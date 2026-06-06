import sqlite3

conn = sqlite3.connect('data/metadata.db')

template = """# Welcome to {module_name} Reconciliation

This module is pre-configured to automate the reconciliation process for **{module_name}**.

## 1. What Kind of Files to Upload

Please ensure that you upload data in standard formats (`.csv` or `.xlsx`). The required files generally fall into the following categories:
- **Sales Data:** Primary sales reports from {module_name} containing order details, product sales, and tax information.
- **Settlement/Payment Data:** Bank settlement reports or payment ledger files from {module_name}.
- **Return Data:** Reports containing customer returns and associated fee reversals.

## 2. Mandatory Columns per Folder

Your system is pre-configured with Master Configurations for specific folders. To ensure seamless processing, your uploaded files MUST contain the following key columns:
- **Order ID / Transaction ID:** Unique identifier for each transaction.
- **Principal Amount / Sales Amount:** The core transaction value.
- **Tax Details (CGST, SGST, IGST):** Where applicable.
- **Fees & Commissions:** Platform fees, shipping credits, etc.
- **Status:** Order status (e.g., Shipped, Returned, Cancelled).

*(Note: The exact column headers must match the Master Configuration defined for each respective folder in the "Master Files" section. Please review the Master Configuration to see the exact expected column names.)*

## 3. Steps from Upload to Final Processing

Follow these steps to complete your reconciliation:

1. **Upload Files:** Navigate to the specific folder (e.g., Sales, Settlement) and upload your raw reports.
2. **Review Master Configuration:** Ensure that the uploaded files align with the Master Configuration for that folder. The system will auto-sync compatible files.
3. **Primary Data Review:** Switch to the "Primary Data" tab to review the cleaned and merged data.
4. **Rule Engine:** Proceed to the "Rule Engine" to apply predefined matching and calculation rules (e.g., matching Sales vs Settlements).
5. **Final Processing:** Execute the rules in the "Final Processing" tab and download your final reconciled output.

---
*If you experience any issues with missing columns or failed syncs, please ensure your source file headers perfectly match the Master Configuration.*
"""

modules = conn.execute("SELECT id, name FROM modules").fetchall()
for m in modules:
    content = template.format(module_name=m[1])
    conn.execute("UPDATE modules SET readme_content = ? WHERE id = ?", (content, m[0]))

conn.commit()
conn.close()
print("Updated readme_content for all modules")
