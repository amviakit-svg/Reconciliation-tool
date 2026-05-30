import sys
import os

def patch_file():
    filepath = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\main.py"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    old_logic = '''        # Override parsing if the user provided a custom filename with a month/type
        if custom_filename:
            custom_parsed = parse_filename(custom_filename)
            if custom_parsed.get('parsed'):
                parsed = custom_parsed
        
        # Determine final filename
        final_output_filename = None
        if custom_filename:
            import re
            from datetime import datetime, timezone, timedelta
            safe_name = re.sub(r'[^\\w\\s-]', '', custom_filename).strip()
            ist_tz = timezone(timedelta(hours=5, minutes=30))
            timestamp_ist = datetime.now(ist_tz).strftime("%d-%m-%Y_%I-%M-%p")
            final_output_filename = f"{safe_name}_{timestamp_ist}.xlsx"
        
        if parsed['parsed']:
            report_type = parsed['report_type']
            month_name = parsed['month_name']
            year = parsed['year']
            financial_year = parsed['financial_year']
            
            output_filename = final_output_filename or generate_processed_filename(
                source_primary_filename, report_type, month_name, year
            )
            
            base_dir = get_physical_storage_path(PROCESSED_DIR, cid, mid)
            if not financial_year or not month_name:
                storage_path = os.path.join(base_dir, 'Unclassified')
            else:
                storage_path = os.path.join(base_dir, financial_year, report_type, month_name)'''
                
    new_logic = '''        # Override parsing if the user provided a custom filename with a month/type
        if custom_filename:
            custom_parsed = parse_filename(custom_filename)
            if custom_parsed.get('parsed'):
                parsed['month_name'] = custom_parsed.get('month_name', parsed.get('month_name'))
                parsed['month_number'] = custom_parsed.get('month_number', parsed.get('month_number'))
                parsed['year'] = custom_parsed.get('year', parsed.get('year'))
                parsed['financial_year'] = custom_parsed.get('financial_year', parsed.get('financial_year'))
                parsed['parsed'] = True
        
        # Determine final filename
        final_output_filename = None
        if custom_filename:
            import re
            from datetime import datetime, timezone, timedelta
            safe_name = re.sub(r'[^\\w\\s-]', '', custom_filename).strip()
            ist_tz = timezone(timedelta(hours=5, minutes=30))
            timestamp_ist = datetime.now(ist_tz).strftime("%d-%m-%Y_%I-%M-%p")
            final_output_filename = f"{safe_name}_{timestamp_ist}.xlsx"
        
        if parsed['parsed']:
            report_type = None
            month_name = parsed['month_name']
            year = parsed['year']
            financial_year = parsed['financial_year']
            
            output_filename = final_output_filename or generate_processed_filename(
                source_primary_filename, "Unknown", month_name, year
            )
            
            base_dir = get_physical_storage_path(PROCESSED_DIR, cid, mid)
            if not financial_year or not month_name:
                storage_path = os.path.join(base_dir, 'Unclassified')
            else:
                storage_path = os.path.join(base_dir, financial_year, month_name)'''

    if old_logic in content:
        content = content.replace(old_logic, new_logic)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched main.py")
    else:
        print("Failed to replace chunk for main.py")

patch_file()
