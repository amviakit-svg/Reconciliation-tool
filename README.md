# Reconciliation Tool

A powerful data reconciliation platform built with Python (FastAPI) and DuckDB for handling large-scale Excel file processing, rule-based matching, and automated reporting.

## Quick Start

### Option 1: Start Server (Easiest - Background Mode)
Double-click the **`start_server.bat`** file. This will:
- Start the server in the **background** (no terminal window to keep open!)
- You can close the startup window immediately after it starts
- The server will keep running until you restart your computer

Then open your browser to: **http://localhost:8000**

### Option 2: Start with Browser Auto-Open
Double-click the **`start_background.vbs`** file. This will:
- Start the server silently in the background (no window at all!)
- Automatically open your browser to the tool

### Option 3: Stop the Server
To stop the background server, run:
```cmd
taskkill /f /im python.exe
```

### Option 4: Command Line (For Developers)
Open Command Prompt in the project folder and run:

```cmd
venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Then open your browser to: **http://localhost:8000**

---

## Project Structure

```
Reconciliation tool/
├── backend/
│   ├── main.py           # FastAPI application
│   ├── database.py       # SQLite database operations
│   └── requirements.txt  # Python dependencies
├── frontend/
│   └── index.html        # Single-page application UI
├── data/
│   ├── uploads/          # Uploaded Excel files
│   └── master_files/     # DuckDB master files
├── venv/                 # Python virtual environment
└── start_server.bat      # One-click server startup
```

---

## Features

### 1. Dashboard
- Overview statistics (Files, Folders, Master Files, Rules)
- Recent activity tracking
- Reconciliation status indicators

### 2. Upload & File Management
- **Drag-and-drop upload** for Excel files (.xlsx, .xls, .csv)
- **Folder management** with subfolder support
- **File details** view showing sheets, rows, and columns
- **Bulk operations**: Move, Delete, Multi-select
- **Master File Creation**: Merge folder files into DuckDB for fast processing

### 3. Rule Mapping (3 Phases)
- **Phase 1**: Select primary data (File/Sheet/Column)
- **Phase 2**: Configure matching rules (VLOOKUP, SUMIF, Addition, Subtraction)
- **Phase 3**: Remarks and conditions (placeholder for future expansion)

### 4. Final Processing
- One-click execution of all configured rules
- Phase-wise status tracking
- Results download

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python) |
| Analytical DB | DuckDB (handles millions of rows) |
| Metadata DB | SQLite |
| Frontend | Vanilla JavaScript + Tailwind CSS |
| File Processing | Pandas + openpyxl |

---

## How to Use

1. **Start the server** using `start_server.bat`
2. **Open browser** to `http://localhost:8000`
3. **Go to Upload & Files tab**
   - Create folders as needed
   - Upload Excel files via drag-and-drop
   - Click on files to view detailed information
4. **Create Master Files**
   - Select a folder with files
   - Click "Create Master File"
   - Choose sheet, header row, and columns
   - Files are merged into a fast DuckDB database
5. **Configure Rules**
   - Phase 1: Select your primary data column
   - Phase 2: Add matching rules row by row
   - Phase 3: Set up remarks (coming soon)
6. **Run Processing**
   - Go to Final Processing tab
   - Click "Process All Rules"
   - Download your reconciliation report

---

## Requirements

- Python 3.10+
- Windows, macOS, or Linux
- Modern web browser (Chrome, Firefox, Edge)

---

## Dependencies

All dependencies are installed in the virtual environment (`venv`):
- fastapi
- uvicorn
- duckdb
- pandas
- openpyxl
- python-multipart

To reinstall dependencies manually:
```cmd
venv\Scripts\pip install -r backend\requirements.txt