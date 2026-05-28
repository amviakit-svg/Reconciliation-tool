import csv
import os
import time

fpath = r'data\uploads\43ce76cc147241b280ed95ddde4224e9.csv'
print('Analyzing file:', fpath)
print('Size:', os.path.getsize(fpath), 'bytes')

# Method 1: Count raw lines (fast)
start = time.time()
with open(fpath, 'rb') as f:
    raw_lines = sum(1 for _ in f)
print(f'Raw lines: {raw_lines} (took {time.time()-start:.2f}s)')

# Method 2: Count with csv.reader ALL rows
start = time.time()
total_all = 0
with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
    reader = csv.reader(f)
    for row in reader:
        total_all += 1
print(f'CSV reader (all): {total_all} (took {time.time()-start:.2f}s)')

# Method 3: Count with csv.reader skipping empty rows
start = time.time()
total_skip = 0
empty_rows = 0
with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
    reader = csv.reader(f)
    for row in reader:
        if not row or all(field.strip() == '' for field in row):
            empty_rows += 1
            continue
        total_skip += 1
print(f'CSV reader (skip empty): {total_skip} (took {time.time()-start:.2f}s)')
print(f'  Empty rows skipped: {empty_rows}')

# Method 4: Use pandas
import pandas as pd
start = time.time()
df = pd.read_csv(fpath, low_memory=False)
print(f'Pandas rows: {len(df)} (took {time.time()-start:.2f}s)')
print(f'Pandas cols: {len(df.columns)}')

# Sample first row
print('\nFirst data row (sample):')
print(df.iloc[0].to_dict())