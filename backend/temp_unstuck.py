from backend.database import get_db_connection
conn = get_db_connection()
conn.execute("UPDATE files SET sync_status = 'pending' WHERE sync_status = 'in_processing'")
conn.commit()
conn.close()
print('Unstuck files!')
