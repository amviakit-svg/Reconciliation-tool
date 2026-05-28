#!/usr/bin/env python3
"""
Reconciliation Tool Launcher
============================
This is the entry point for the PyInstaller-bundled executable.
It ensures correct paths are set and starts the uvicorn server.
"""

import os
import sys

# Detect if running as frozen (PyInstaller bundle)
if getattr(sys, 'frozen', False):
    # sys.executable is the .exe location
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure backend is in Python path
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

# Set working directory to ensure data/ folder creation works
os.chdir(BASE_DIR)

# Import and run the FastAPI app
from backend.main import app
import uvicorn

if __name__ == "__main__":
    # Use 127.0.0.1 for deployment (more secure than 0.0.0.0)
    # Port 8000 with auto-retry if busy
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")