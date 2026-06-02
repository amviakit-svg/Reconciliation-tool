

# --- AUTO-SYNC ENDPOINTS ---

from fastapi import BackgroundTasks
from backend.auto_sync import trigger_folder_sync
from backend.database import get_files_with_sync_status

@app.post("/api/folders/{folder_id}/sync")
async def trigger_manual_sync(folder_id: int, background_tasks: BackgroundTasks):
    # This endpoint is called when the user clicks 'Sync Now' in the UI
    background_tasks.add_task(trigger_folder_sync, folder_id)
    return {"success": True, "message": "Sync started in the background."}

@app.get("/api/folders/{folder_id}/sync-status")
async def get_folder_sync_status(folder_id: int):
    # Returns a list of files with their sync status
    files = get_files_with_sync_status(folder_id)
    return {"success": True, "files": files}
