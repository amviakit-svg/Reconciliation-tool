from backend.database import get_db_connection
from backend.auto_sync import run_incremental_sync

conn = get_db_connection()
conn.execute("UPDATE files SET sync_status = 'pending', sync_error = NULL WHERE folder_id = 77")
conn.commit()
conn.close()

run_incremental_sync(77)

conn = get_db_connection()
files = conn.execute("SELECT original_name, sync_status, sync_error FROM files WHERE folder_id = 77").fetchall()
for f in files:
    print(dict(f))
conn.close()
