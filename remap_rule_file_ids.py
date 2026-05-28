import sqlite3
import json
import re

DB_PATH = "data/metadata.db"

# File ID mapping: old_id -> new_id (from migration output)
FILE_ID_MAP = {
    "1": "73",
    "3": "74",
    "4": "75",
    "5": "76",
    "12": "77",
    "13": "78",
    "14": "79",
    "15": "80",
    "16": "81",
    "17": "82",
    "18": "83",
    "20": "84",
    "21": "85",
    "22": "86",
    "23": "87",
    "24": "88",
    "25": "89",
    "26": "90",
    "28": "91",
    "29": "92",
    "30": "93",
    "31": "94",
    "32": "95",
    "33": "96",
    "34": "97",
    # master files
    "master_5": "master_10",  # old folder 5 -> new folder 10 (Sales)
    "master_3": "master_8",   # old folder 3 -> new folder 8 (Clickpost)
}

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rules = conn.execute("SELECT id, name, phase, config FROM rules").fetchall()
print(f"Found {len(rules)} rules to remap\n")

for rule in rules:
    rule_id = rule['id']
    name = rule['name']
    config = rule['config']
    
    # Replace quoted old IDs with quoted new IDs
    # Match "id": "X" or "file_id": "X" or "secondary_file": "X" etc.
    new_config = config
    
    # Replace all occurrences of old file IDs in quotes
    for old_id, new_id in FILE_ID_MAP.items():
        # Match the old ID when it's a JSON string value
        patterns = [
            f'"file_id":"{old_id}"',
            f'"file_id": "{old_id}"',
            f'"secondary_file":"{old_id}"',
            f'"secondary_file": "{old_id}"',
            f'"extract_file":"{old_id}"',
            f'"extract_file": "{old_id}"',
            f'"primary_file":"{old_id}"',
            f'"primary_file": "{old_id}"',
            f'"id":"{old_id}"',
            f'"id": "{old_id}"',
        ]
        for pattern in patterns:
            if pattern in new_config:
                # Replace with same spacing
                replacement = pattern.replace(old_id, new_id, 1)
                new_config = new_config.replace(pattern, replacement)
                print(f"  Rule '{name}': replaced {pattern} -> {replacement}")
    
    if new_config != config:
        conn.execute("UPDATE rules SET config = ? WHERE id = ?", (new_config, rule_id))
        print(f"Updated rule {rule_id} '{name}'\n")
    else:
        print(f"Rule {rule_id} '{name}' - no changes needed\n")

conn.commit()

# Verify
print("\n=== VERIFICATION ===")
rules = conn.execute("SELECT id, name, phase, config FROM rules").fetchall()
for rule in rules:
    print(f"\nRule {rule['id']}: {rule['name']} (phase {rule['phase']})")
    try:
        config = json.loads(rule['config'])
        if isinstance(config, list):
            for item in config:
                if isinstance(item, dict):
                    for key in ['secondary_file', 'extract_file', 'primary_file', 'file_id']:
                        if key in item:
                            print(f"  {key}: {item[key]}")
        elif isinstance(config, dict):
            for key in ['file_id', 'primary_file']:
                if key in config:
                    print(f"  {key}: {config[key]}")
    except:
        print(f"  (Could not parse config)")

conn.close()
print("\nRemapping complete!")
