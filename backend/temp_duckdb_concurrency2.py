import duckdb
import os
import threading

db_path = 'test_concurrency.duckdb'
if os.path.exists(db_path):
    os.remove(db_path)

conn1 = duckdb.connect(db_path)
conn1.execute("CREATE TABLE t1 (i INTEGER)")
conn1.execute("INSERT INTO t1 VALUES (1)")

def read_thread():
    try:
        conn2 = duckdb.connect(db_path)
        print("Thread read:", conn2.execute("SELECT * FROM t1").fetchall())
        conn2.close()
    except Exception as e:
        print("Thread exception:", e)

t = threading.Thread(target=read_thread)
t.start()
t.join()

conn1.close()
print("Done")
