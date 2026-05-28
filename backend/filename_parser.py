import re
from datetime import datetime

MONTH_MAP = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12
}

REPORT_TYPE_PATTERNS = [
    (r'(?<![a-zA-Z0-9])(?:cn|credit[\s\-_]?note|cr[\s\-_]?note)(?![a-zA-Z0-9])', 'CN'),
    (r'(?<![a-zA-Z0-9])(?:sales|order|website[\s\-_]?sales|marketplace)(?![a-zA-Z0-9])', 'Sales'),
    (r'(?<![a-zA-Z0-9])(?:settlement|cod)(?![a-zA-Z0-9])', 'Settlement'),
    (r'(?<![a-zA-Z0-9])(?:returns?|rto)(?![a-zA-Z0-9])', 'Returns'),
]


def parse_financial_year(year, month_number):
    """
    Indian Financial Year: Apr-Mar
    Apr 2023 - Mar 2024 = FY2023-24
    """
    if month_number >= 4:  # Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec
        fy_start = year
        fy_end = year + 1
    else:  # Jan, Feb, Mar
        fy_start = year - 1
        fy_end = year
    return f"FY{fy_start}-{str(fy_end)[-2:]}"


def detect_month_year(filename):
    """
    Detect month and year from filename using multiple patterns.
    Returns (month_name, month_number, year) or (None, None, None)
    """
    filename_lower = filename.lower()
    
    # Pattern 1: Month'YY or Month'YYYY (e.g., Jan'24, Jan'2024)
    pattern1 = re.compile(
        r'(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)[\'\s\-_]*(\d{2,4})\b',
        re.I
    )
    match = pattern1.search(filename_lower)
    if match:
        month_str = match.group(1).lower()
        year_str = match.group(2)
        month_num = MONTH_MAP.get(month_str)
        if month_num:
            year = int(year_str)
            if year < 100:
                year = 2000 + year
            return (month_str.capitalize(), month_num, year)
    
    # Pattern 2: MM-YYYY or MM_YYYY (e.g., 01-2024, 01_2024)
    pattern2 = re.compile(r'(\d{1,2})[\-/](\d{2,4})\b')
    match = pattern2.search(filename_lower)
    if match:
        month_num = int(match.group(1))
        year_str = match.group(2)
        if 1 <= month_num <= 12:
            year = int(year_str)
            if year < 100:
                year = 2000 + year
            month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            return (month_names[month_num], month_num, year)
    
    # Pattern 3: YYYY-MM (e.g., 2024-01)
    pattern3 = re.compile(r'(\d{4})[\-/](\d{1,2})\b')
    match = pattern3.search(filename_lower)
    if match:
        year = int(match.group(1))
        month_num = int(match.group(2))
        if 1 <= month_num <= 12:
            month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            return (month_names[month_num], month_num, year)
    
    # Pattern 4: Full text month with year (e.g., "Sales Report january 2024")
    pattern4 = re.compile(
        r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b',
        re.I
    )
    match = pattern4.search(filename_lower)
    if match:
        month_str = match.group(1).lower()
        year = int(match.group(2))
        month_num = MONTH_MAP.get(month_str)
        if month_num:
            return (month_str.capitalize()[:3], month_num, year)
    
    # Pattern 5: YYYYMM (e.g., 202605) or YYYY_MM (e.g., 2026_05)
    pattern5 = re.compile(r'(?<!\d)(20\d{2})_?(0[1-9]|1[0-2])(?!\d)')
    match = pattern5.search(filename_lower)
    if match:
        year = int(match.group(1))
        month_num = int(match.group(2))
        month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return (month_names[month_num], month_num, year)
        
    # Pattern 6: Just month name, default to current year
    pattern6 = re.compile(
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b',
        re.I
    )
    match = pattern6.search(filename_lower)
    if match:
        month_str = match.group(1).lower()
        month_num = MONTH_MAP.get(month_str)
        if month_num:
            return (month_str.capitalize()[:3], month_num, datetime.now().year)
    
    return (None, None, None)


def detect_report_type(filename):
    """
    Detect report type from filename.
    Returns 'Sales', 'CN', 'Settlement', 'Returns', or 'Others'
    """
    filename_lower = filename.lower()
    
    for pattern, report_type in REPORT_TYPE_PATTERNS:
        if re.search(pattern, filename_lower):
            return report_type
    
    return 'Others'


def parse_filename(filename):
    """
    Full filename parser.
    Returns dict with: report_type, month_name, month_number, year, financial_year
    """
    month_name, month_number, year = detect_month_year(filename)
    report_type = detect_report_type(filename)
    
    if month_name and month_number and year:
        financial_year = parse_financial_year(year, month_number)
    else:
        financial_year = None
    
    return {
        'report_type': report_type,
        'month_name': month_name,
        'month_number': month_number,
        'year': year,
        'financial_year': financial_year,
        'parsed': month_name is not None
    }


def generate_processed_filename(original_filename, report_type, month_name, year):
    """
    Generate auto-naming for processed output file.
    e.g., Jan2024_Sales_Reconciliation_20240511_143000.xlsx
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    
    # Short year
    short_year = str(year)[-2:] if year else '00'
    
    # Build filename
    parts = []
    if month_name:
        parts.append(f"{month_name}{short_year}")
    if report_type and report_type != 'Others':
        parts.append(report_type)
    parts.append("Reconciliation")
    parts.append(timestamp)
    
    return '_'.join(parts) + '.xlsx'


def get_storage_path(base_dir, financial_year, report_type, month_name):
    """
    Get the folder path for storing processed file.
    e.g., data/processed/FY2023-24/Sales/Jan/
    """
    import os
    
    if not financial_year or not month_name:
        # Fallback to unclassified
        path = os.path.join(base_dir, 'processed', 'Unclassified')
    else:
        path = os.path.join(base_dir, 'processed', financial_year, report_type, month_name)
    
    os.makedirs(path, exist_ok=True)
    return path