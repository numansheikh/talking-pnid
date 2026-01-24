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

# For Vercel, we need to use Mangum to convert ASGI to AWS Lambda format
# But Vercel's Python runtime might need a specific handler format
try:
    from mangum import Mangum
    # Create Mangum adapter
    mangum_handler = Mangum(app, lifespan="off")
    
    # Vercel expects handler to be callable
    # Export as handler function that Vercel can invoke
    def handler(request):
        return mangum_handler(request)
except ImportError:
    # Fallback: export app directly if Mangum not available
    handler = app
