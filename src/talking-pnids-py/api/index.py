"""
Vercel serverless function entry point for FastAPI
"""
import sys
import os
from pathlib import Path

# Set working directory to project root (where api/ directory is located)
# In Vercel, __file__ will be something like /var/task/api/index.py
# So parent.parent gets us to the project root
project_root = Path(__file__).parent.parent
os.chdir(project_root)

# Add backend directory to Python path
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

# Set environment variable for path resolution
os.environ["PROJECT_ROOT"] = str(project_root)

# Import FastAPI app
from main import app

# Vercel's @vercel/python builder expects the app to be exported directly
# FastAPI is ASGI, and Vercel should handle it natively
# If this doesn't work, we may need to use individual serverless functions
handler = app
