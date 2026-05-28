"""
Formula Expression Engine for Reconciliation Tool
Converts Excel-like formulas to DuckDB SQL expressions.

Supported syntax:
  =SUM(A, B, C)          -> TRY_CAST("A" AS DOUBLE) + TRY_CAST("B" AS DOUBLE) + ...
  =-SUM(A, B)            -> -(TRY_CAST("A" AS DOUBLE) + TRY_CAST("B" AS DOUBLE))
  =A + B * C             -> TRY_CAST("A" AS DOUBLE) + (TRY_CAST("B" AS DOUBLE) * TRY_CAST("C" AS DOUBLE))
  =ABS(Amount)           -> ABS(TRY_CAST("Amount" AS DOUBLE))
  =ROUND(SUM(A, B), 2)   -> ROUND(TRY_CAST("A" AS DOUBLE) + TRY_CAST("B" AS DOUBLE), 2)
  =CONCAT(Name, " - ", ID) -> "Name" || ' - ' || "ID"
  =COALESCE(A, B, 0)     -> COALESCE(TRY_CAST("A" AS DOUBLE), TRY_CAST("B" AS DOUBLE), 0)
  =IFNULL(A, 0)          -> IFNULL(TRY_CAST("A" AS DOUBLE), 0)

Operators: +, -, *, /, ^, unary -, unary +
Parentheses for grouping.
"""

import ast
import re
import traceback
from typing import List, Tuple, Optional


# =============================================================================
# ALLOWED FUNCTIONS AND OPERATORS
# =============================================================================

ALLOWED_FUNCTIONS = {
    'SUM', 'ABS', 'AVG', 'COUNT', 'MAX', 'MIN', 'ROUND',
    'CONCAT', 'COALESCE', 'IFNULL',
}

NUMERIC_FUNCTIONS = {'SUM', 'ABS', 'AVG', 'COUNT', 'MAX', 'MIN', 'ROUND', 'COALESCE', 'IFNULL'}
STRING_FUNCTIONS = {'CONCAT'}

# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class FormulaError(Exception):
    """Base exception for formula parsing errors."""
    def __init__(self, message: str, suggestion: str = ""):
        self.suggestion = suggestion
        super().__init__(message)


class FormulaSyntaxError(FormulaError):
    """Raised when formula syntax is invalid."""
    pass


class FormulaValidationError(FormulaError):
    """Raised when formula references invalid columns or functions."""
    pass


# =============================================================================
# PARSER
# =============================================================================

class FormulaParser:
    """
    Parse Excel-like formula string into an AST, then convert to DuckDB SQL.
    """

    def __init__(self, available_columns: List[str]):
        self.available_columns = [str(c).strip() for c in available_columns]
        self.column_lower_map = {c.lower(): c for c in self.available_columns}
        self.referenced_columns = set()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def parse(self, expression: str) -> Tuple[str, List[str]]:
        """
        Parse a formula expression and return (sql_string, referenced_columns).

        Args:
            expression: Raw formula string, e.g. "=-SUM(A, B)" or "A + B * C"

        Returns:
            Tuple of (DuckDB SQL expression, list of referenced column names)

        Raises:
            FormulaSyntaxError: If the expression is malformed.
            FormulaValidationError: If unknown columns/functions are used.
        """
        # Strip leading '=' if present
        expr = expression.strip()
        if expr.startswith('='):
            expr = expr[1:].strip()

        if not expr:
            raise FormulaSyntaxError(
                "Formula expression is empty.",
                suggestion="Enter a formula like =SUM(Amount, Tax) or =Amount * 1.18"
            )

        # 1. Validate characters first
        self._validate_characters(expr)

        # Normalize commas: Excel often uses semicolons as arg separators in some locales
        expr = expr.replace(';', ',')

        # 2. Pre-tokenize to handle column names that contain spaces or special chars
        #    We wrap bare column identifiers in quotes so Python's ast can parse them
        wrapped_expr, token_map = self._wrap_identifiers(expr)

        # 3. Parse with Python's ast module
        try:
            tree = ast.parse(wrapped_expr, mode='eval')
        except SyntaxError as e:
            raise FormulaSyntaxError(
                f"Invalid formula syntax: {str(e).replace('<string>', 'expression')}",
                suggestion="Check parentheses, commas, and operators. Example: =SUM(Amount, Tax) or =Amount + Tax"
            )

        # 4. Convert AST to SQL
        sql = self._convert_node(tree.body)

        return sql, list(self.referenced_columns)

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def _validate_characters(self, expr: str):
        """
        Reject dangerous characters / patterns before parsing.
        """
        # Reject SQL injection attempts
        dangerous = ['--', '/*', '*/', ';', 'DROP ', 'DELETE ', 'INSERT ', 'UPDATE ', 'ALTER ']
        lower = expr.lower()
        for d in dangerous:
            if d in lower:
                raise FormulaValidationError(
                    f"Formula contains invalid characters or keywords.",
                    suggestion="Use only column names, numbers, operators (+, -, *, /, ^), and allowed functions (SUM, ABS, ROUND, etc.)."
                )

        # Allow letters, digits, underscores, spaces, dots, commas, quotes,
        # operators, parentheses
        allowed = re.compile(r"^[A-Za-z0-9_ \.\,\+\-\*\/\^\(\)\'\"\%]+$")
        if not allowed.match(expr):
            # Find the offending characters for a better message
            bad = set()
            for ch in expr:
                if not allowed.match(ch):
                    bad.add(ch)
            if bad:
                raise FormulaSyntaxError(
                    f"Formula contains invalid character(s): {', '.join(sorted(bad))}",
                    suggestion="Allowed: letters, numbers, spaces, underscores, dots, commas, quotes, operators (+ - * / ^), and parentheses."
                )

    # -------------------------------------------------------------------------
    # Identifier Wrapping
    # -------------------------------------------------------------------------

    def _wrap_identifiers(self, expr: str) -> Tuple[str, dict]:
        """
        Wrap bare column identifiers in the expression with a placeholder token
        that Python's ast can parse as a Name node.

        We need to be careful to distinguish:
          - Function names: SUM, ABS, etc.  -> keep as-is
          - Numeric literals: 123, 12.5      -> keep as-is
          - Quoted strings: "Hello", 'Hello' -> keep as-is (pass through for ast)
          - Column names: Amount, "Amount"    -> wrap

        Returns:
            (wrapped_expression, token_map) where token_map maps placeholder -> original
        """
        token_map = {}
        token_counter = [0]

        def _make_token():
            token_counter[0] += 1
            return f"__COL{token_counter[0]}__"

        # Scan character by character
        result_parts = []
        i = 0
        n = len(expr)

        while i < n:
            ch = expr[i]

            # Skip whitespace
            if ch.isspace():
                result_parts.append(ch)
                i += 1
                continue

            # String literal: scan until matching quote and pass through as-is
            if ch in '"\'':
                quote = ch
                j = i + 1
                while j < n and expr[j] != quote:
                    j += 1
                if j < n:
                    j += 1  # include closing quote
                result_parts.append(expr[i:j])
                i = j
                continue

            # Operators and delimiters
            if ch in '+-*/^(),':
                result_parts.append(ch)
                i += 1
                continue

            # Number literal
            if ch.isdigit() or (ch == '.' and i + 1 < n and expr[i + 1].isdigit()):
                j = i
                while j < n and (expr[j].isdigit() or expr[j] == '.'):
                    j += 1
                result_parts.append(expr[i:j])
                i = j
                continue

            # Identifier (function name or column reference)
            if ch.isalpha() or ch == '_':
                j = i
                while j < n and (expr[j].isalnum() or expr[j] == '_' or expr[j] == '.'):
                    j += 1
                word = expr[i:j]

                # Is it a known function?
                if word.upper() in ALLOWED_FUNCTIONS:
                    result_parts.append(word)  # keep as-is (ast.Name)
                else:
                    # It's a column reference (or potentially an unknown function call)
                    # Defer validation to AST conversion; just wrap it
                    token = _make_token()
                    token_map[token] = word
                    result_parts.append(token)
                i = j
                continue

            # Should not reach here if _validate_characters passed
            result_parts.append(ch)
            i += 1

        wrapped = ''.join(result_parts)

        # Store token map on instance for AST conversion
        self._token_map = token_map
        return wrapped, token_map

    def _resolve_column(self, word: str) -> str:
        """
        Resolve a bare word to an actual column name.
        Case-insensitive match against available_columns.
        """
        lower = word.lower()
        if lower in self.column_lower_map:
            col = self.column_lower_map[lower]
            self.referenced_columns.add(col)
            return col

        # Also try exact match
        if word in self.available_columns:
            self.referenced_columns.add(word)
            return word

        # Suggest similar column names
        suggestions = [c for c in self.available_columns if lower in c.lower() or c.lower() in lower]
        suggestion_text = ""
        if suggestions:
            suggestion_text = f" Did you mean: {', '.join(suggestions[:3])}?"
        else:
            suggestion_text = f" Available columns: {', '.join(self.available_columns[:10])}"

        raise FormulaValidationError(
            f"Unknown column '{word}'.{suggestion_text}",
            suggestion="Use exact column names from the master file. Column names are case-insensitive."
        )

    # -------------------------------------------------------------------------
    # AST -> SQL Converter
    # -------------------------------------------------------------------------

    def _convert_node(self, node: ast.AST) -> str:
        """
        Recursively convert an AST node to DuckDB SQL.
        """
        if isinstance(node, ast.Expression):
            return self._convert_node(node.body)

        # Unary operations: -X, +X
        if isinstance(node, ast.UnaryOp):
            operand = self._convert_node(node.operand)
            if isinstance(node.op, ast.USub):
                return f"(-({operand}))"
            elif isinstance(node.op, ast.UAdd):
                return f"(+({operand}))"
            else:
                raise FormulaSyntaxError(
                    f"Unsupported unary operator.",
                    suggestion="Use + or - before a value, e.g. =-SUM(A, B) or =+Amount"
                )

        # Binary operations: +, -, *, /, ^
        if isinstance(node, ast.BinOp):
            left = self._convert_node(node.left)
            right = self._convert_node(node.right)

            if isinstance(node.op, ast.Add):
                op = '+'
            elif isinstance(node.op, ast.Sub):
                op = '-'
            elif isinstance(node.op, ast.Mult):
                op = '*'
            elif isinstance(node.op, ast.Div):
                op = '/'
            elif isinstance(node.op, ast.Pow):
                op = '^'  # DuckDB supports ^
            else:
                raise FormulaSyntaxError(
                    f"Unsupported operator in formula.",
                    suggestion="Allowed operators: +, -, *, /, ^"
                )

            # For string concatenation with ||, detect if either side is a string literal
            if op == '+' and (self._is_string_literal(node.left) or self._is_string_literal(node.right)):
                return f"({left} || {right})"

            return f"({left} {op} {right})"

        # Call: SUM(A, B), ABS(Amount), etc.
        if isinstance(node, ast.Call):
            return self._convert_call(node)

        # Name: column reference (wrapped token)
        if isinstance(node, ast.Name):
            return self._convert_name(node.id)

        # Constant: numbers, strings
        if isinstance(node, ast.Constant):
            return self._convert_constant(node.value)

        # For Python < 3.8 compatibility: ast.Num, ast.Str
        if hasattr(ast, 'Num') and isinstance(node, ast.Num):
            return self._convert_constant(node.n)
        if hasattr(ast, 'Str') and isinstance(node, ast.Str):
            return self._convert_constant(node.s)

        raise FormulaSyntaxError(
            f"Unsupported formula element: {ast.dump(node)}",
            suggestion="Use simple arithmetic, allowed functions, and column references."
        )

    def _is_string_literal(self, node: ast.AST) -> bool:
        """Check if a node evaluates to a string literal."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return True
        if hasattr(ast, 'Str') and isinstance(node, ast.Str):
            return True
        return False

    def _convert_name(self, name: str) -> str:
        """
        Convert a Name node to SQL.
        If it's a wrapped column token, resolve and validate it.
        If it's a function name, return uppercased.
        """
        # Check token map first for wrapped column tokens
        if hasattr(self, '_token_map') and name in self._token_map:
            original = self._token_map[name]
            # Validate that the column exists
            col = self._resolve_column(original)
            return self._sql_column(col)

        # Function names
        if name.upper() in ALLOWED_FUNCTIONS:
            return name.upper()

        # Try to resolve as column (for bare names that weren't wrapped)
        try:
            col = self._resolve_column(name)
            return self._sql_column(col)
        except FormulaValidationError:
            pass

        # Unknown identifier
        if name.startswith('__COL') and name.endswith('__'):
            # This is a wrapped token that we lost track of — shouldn't happen
            raise FormulaValidationError(
                f"Unknown column reference in formula.",
                suggestion="Check column names. Use exact names from the master file."
            )

        raise FormulaValidationError(
            f"Unknown identifier '{name}' in formula.",
            suggestion="Use column names or allowed functions (SUM, ABS, ROUND, etc.)."
        )

    def _convert_constant(self, value) -> str:
        """Convert a Python constant to SQL literal."""
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            # Escape single quotes for SQL
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        if value is None:
            return "NULL"
        raise FormulaSyntaxError(
            f"Unsupported constant type: {type(value).__name__}",
            suggestion="Use numbers or text strings in formulas."
        )

    def _convert_call(self, node: ast.Call) -> str:
        """Convert a function call to DuckDB SQL."""
        func_name = self._get_call_name(node.func)
        if not func_name:
            raise FormulaSyntaxError(
                "Invalid function call in formula.",
                suggestion="Use allowed functions: SUM, ABS, ROUND, CONCAT, COALESCE, IFNULL, etc."
            )

        # If func_name is a wrapped token, it was an unknown function (not in ALLOWED_FUNCTIONS)
        if func_name.startswith('__COL') and func_name.endswith('__'):
            if hasattr(self, '_token_map') and func_name in self._token_map:
                original = self._token_map[func_name]
                allowed_list = ', '.join(sorted(ALLOWED_FUNCTIONS))
                raise FormulaValidationError(
                    f"Unknown function '{original}'. Allowed: {allowed_list}",
                    suggestion="Use only the listed functions. For other operations, use operators (+, -, *, /, ^)."
                )

        func_upper = func_name.upper()

        if func_upper not in ALLOWED_FUNCTIONS:
            allowed_list = ', '.join(sorted(ALLOWED_FUNCTIONS))
            raise FormulaValidationError(
                f"Unknown function '{func_name}'. Allowed: {allowed_list}",
                suggestion="Use only the listed functions. For other operations, use operators (+, -, *, /, ^)."
            )

        args = [self._convert_node(arg) for arg in node.args]

        if func_upper == 'SUM':
            if len(args) < 1:
                raise FormulaSyntaxError(
                    "SUM() requires at least 1 argument.",
                    suggestion="Example: =SUM(Amount, Tax, Discount) or =SUM(Total)"
                )
            # Convert to addition chain with TRY_CAST
            casted = [self._try_cast_numeric(a) for a in args]
            return ' + '.join(casted)

        if func_upper == 'ABS':
            if len(args) != 1:
                raise FormulaSyntaxError(
                    "ABS() requires exactly 1 argument.",
                    suggestion="Example: =ABS(Amount)"
                )
            return f"ABS({self._try_cast_numeric(args[0])})"

        if func_upper == 'AVG':
            if len(args) < 1:
                raise FormulaSyntaxError(
                    "AVG() requires at least 1 argument.",
                    suggestion="Example: =AVG(Amount, Tax)"
                )
            if len(args) == 1:
                return f"AVG({self._try_cast_numeric(args[0])})"
            else:
                # Average of multiple expressions: (a + b + c) / count
                casted = [self._try_cast_numeric(a) for a in args]
                total = ' + '.join(casted)
                return f"(({total}) / {len(args)})"

        if func_upper == 'COUNT':
            if len(args) < 1:
                raise FormulaSyntaxError(
                    "COUNT() requires at least 1 argument.",
                    suggestion="Example: =COUNT(Amount, Tax)"
                )
            if len(args) == 1:
                return f"COUNT({args[0]})"
            else:
                # Count non-null across multiple columns? Not standard.
                # Fallback: count of rows where any is not null
                conditions = [f"{a} IS NOT NULL" for a in args]
                return f"CASE WHEN ({' OR '.join(conditions)}) THEN 1 ELSE 0 END"

        if func_upper == 'MAX':
            if len(args) < 1:
                raise FormulaSyntaxError(
                    "MAX() requires at least 1 argument.",
                    suggestion="Example: =MAX(Amount, Tax, Discount)"
                )
            if len(args) == 1:
                return f"MAX({self._try_cast_numeric(args[0])})"
            else:
                nested = args[0]
                for a in args[1:]:
                    nested = f"GREATEST({self._try_cast_numeric(nested)}, {self._try_cast_numeric(a)})"
                return nested

        if func_upper == 'MIN':
            if len(args) < 1:
                raise FormulaSyntaxError(
                    "MIN() requires at least 1 argument.",
                    suggestion="Example: =MIN(Amount, Tax, Discount)"
                )
            if len(args) == 1:
                return f"MIN({self._try_cast_numeric(args[0])})"
            else:
                nested = args[0]
                for a in args[1:]:
                    nested = f"LEAST({self._try_cast_numeric(nested)}, {self._try_cast_numeric(a)})"
                return nested

        if func_upper == 'ROUND':
            if len(args) not in (1, 2):
                raise FormulaSyntaxError(
                    "ROUND() requires 1 or 2 arguments.",
                    suggestion="Example: =ROUND(Amount, 2) or =ROUND(SUM(A, B), 0)"
                )
            val = self._try_cast_numeric(args[0])
            if len(args) == 2:
                return f"ROUND({val}, {args[1]})"
            return f"ROUND({val})"

        if func_upper == 'CONCAT':
            if len(args) < 1:
                raise FormulaSyntaxError(
                    "CONCAT() requires at least 1 argument.",
                    suggestion="Example: =CONCAT(FirstName, ' ', LastName)"
                )
            # DuckDB: || operator for concatenation
            # We need to determine if each arg is string or needs casting
            parts = []
            for a in args:
                # If it's a plain column ref, wrap with CAST(... AS VARCHAR)
                # If it's a string literal, keep as-is
                # If it's numeric, cast to string
                parts.append(self._try_cast_string(a))
            return ' || '.join(parts)

        if func_upper == 'COALESCE':
            if len(args) < 1:
                raise FormulaSyntaxError(
                    "COALESCE() requires at least 1 argument.",
                    suggestion="Example: =COALESCE(Amount, 0)"
                )
            joined = ', '.join(args)
            return f"COALESCE({joined})"

        if func_upper == 'IFNULL':
            if len(args) != 2:
                raise FormulaSyntaxError(
                    "IFNULL() requires exactly 2 arguments.",
                    suggestion="Example: =IFNULL(Amount, 0)"
                )
            return f"IFNULL({args[0]}, {args[1]})"

        # Fallback (shouldn't reach here)
        joined = ', '.join(args)
        return f"{func_upper}({joined})"

    def _get_call_name(self, func_node: ast.AST) -> Optional[str]:
        """Extract function name from ast.Call.func."""
        if isinstance(func_node, ast.Name):
            return func_node.id
        return None

    def _try_cast_numeric(self, sql_expr: str) -> str:
        """
        Wrap a SQL expression with TRY_CAST(... AS DOUBLE) for safe numeric operations.
        Skip wrapping if it's already a simple numeric literal or already wrapped.
        """
        s = sql_expr.strip()
        # Already wrapped?
        if s.startswith("TRY_CAST(") and s.endswith("AS DOUBLE)"):
            return s
        # Numeric literal?
        if re.match(r'^-?\d+(\.\d+)?$', s):
            return s
        # Single-quoted string literal? Don't cast strings to double
        if s.startswith("'") and s.endswith("'"):
            return s
        # Quoted column identifier (double quotes) -> wrap with TRY_CAST
        if s.startswith('"') and s.endswith('"'):
            return f'TRY_CAST({s} AS DOUBLE)'
        return f'TRY_CAST({s} AS DOUBLE)'

    def _try_cast_string(self, sql_expr: str) -> str:
        """
        Ensure expression is treated as string for concatenation.
        """
        s = sql_expr.strip()
        # String literal?
        if (s.startswith("'") and s.endswith("'")):
            return s
        # Already cast to varchar?
        if 'AS VARCHAR' in s:
            return s
        return f'CAST({s} AS VARCHAR)'

    def _sql_column(self, col_name: str) -> str:
        """Quote a column name for DuckDB SQL."""
        # DuckDB allows double-quoted identifiers
        escaped = col_name.replace('"', '""')
        return f'"{escaped}"'


# =============================================================================
# PUBLIC HELPER
# =============================================================================

def parse_formula(expression: str, available_columns: List[str]) -> Tuple[str, List[str]]:
    """
    Convenience wrapper: parse a formula expression.

    Returns:
        (sql_expression, referenced_columns)

    Raises:
        FormulaError: On any parsing or validation error.
    """
    parser = FormulaParser(available_columns)
    return parser.parse(expression)


def validate_formula(expression: str, available_columns: List[str]) -> dict:
    """
    Validate a formula without executing it. Returns a result dict.

    Returns:
        {
            "valid": True,
            "sql": "...",
            "columns": [...]
        }
    or
        {
            "valid": False,
            "error": "...",
            "suggestion": "..."
        }
    """
    try:
        sql, cols = parse_formula(expression, available_columns)
        return {
            "valid": True,
            "sql": sql,
            "columns": cols
        }
    except FormulaError as e:
        return {
            "valid": False,
            "error": str(e),
            "suggestion": e.suggestion
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Unexpected error: {str(e)}",
            "suggestion": "Please check your formula syntax and try again."
        }


# =============================================================================
# TESTS (run when module executed directly)
# =============================================================================

if __name__ == '__main__':
    cols = ["Amount", "Tax", "Discount", "Grand Total", "Net_Amount"]

    test_cases = [
        ("=SUM(Amount, Tax)", 'TRY_CAST("Amount" AS DOUBLE) + TRY_CAST("Tax" AS DOUBLE)'),
        ("=-SUM(Amount, Tax)", '(-(TRY_CAST("Amount" AS DOUBLE) + TRY_CAST("Tax" AS DOUBLE)))'),
        ("=Amount + Tax * 0.18", '("Amount" + ("Tax" * 0.18))'),
        ("=ABS(Amount)", 'ABS(TRY_CAST("Amount" AS DOUBLE))'),
        ("=ROUND(SUM(Amount, Tax), 2)", 'ROUND(TRY_CAST("Amount" AS DOUBLE) + TRY_CAST("Tax" AS DOUBLE), 2)'),
        ("=CONCAT(Amount, ' - ', Tax)", 'CAST("Amount" AS VARCHAR) || \' - \' || CAST("Tax" AS VARCHAR)'),
        ("=COALESCE(Amount, 0)", 'COALESCE("Amount", 0)'),
        ("=IFNULL(Amount, 0)", 'IFNULL("Amount", 0)'),
        ("=MAX(Amount, Tax, Discount)", None),  # multi-arg MAX
        ("=MIN(Amount, Tax)", None),  # multi-arg MIN
    ]

    print("Running formula engine tests...\n")
    all_pass = True

    for expr, expected_sql in test_cases:
        try:
            result = validate_formula(expr, cols)
            if result["valid"]:
                sql = result["sql"]
                if expected_sql is not None and sql != expected_sql:
                    print(f"FAIL: {expr}")
                    print(f"  Expected: {expected_sql}")
                    print(f"  Got:      {sql}")
                    all_pass = False
                else:
                    print(f"PASS: {expr}")
                    print(f"  SQL: {sql}")
                    print(f"  Columns: {result['columns']}")
            else:
                print(f"FAIL: {expr}")
                print(f"  Error: {result['error']}")
                all_pass = False
        except Exception as e:
            print(f"EXCEPTION: {expr}")
            print(f"  {e}")
            all_pass = False
        print()

    # Error cases
    error_cases = [
        ("=SUM()", "requires at least 1"),
        ("=UNKNOWN_FUNC(Amount)", "Unknown function"),
        ("=NonExistent + Amount", "Unknown column"),
        ("=Amount + ;", "invalid characters"),
    ]

    for expr, expected_err in error_cases:
        result = validate_formula(expr, cols)
        if not result["valid"] and expected_err.lower() in result["error"].lower():
            print(f"PASS (error expected): {expr}")
            print(f"  Error: {result['error']}")
        else:
            print(f"FAIL (expected error): {expr}")
            print(f"  Got: {result}")
            all_pass = False
        print()

    if all_pass:
        print("All tests passed!")
    else:
        print("Some tests failed.")