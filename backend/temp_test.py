import duckdb
conn = duckdb.connect(':memory:')
with open('test.csv.deleted.123', 'w') as f:
    f.write('a,b\n1,2')
df = conn.execute("SELECT * FROM read_csv_auto('test.csv.deleted.123')").fetchdf()
print(df)
