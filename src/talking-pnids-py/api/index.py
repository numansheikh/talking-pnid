"""
Vercel serverless function entry point for FastAPI
Uses asgiref to convert ASGI to WSGI for Vercel compatibility
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

# Convert ASGI to WSGI for Vercel compatibility
try:
    from asgiref.wsgi import WsgiToAsgi
    
    # Wrap FastAPI (ASGI) app with WSGI adapter
    wsgi_app = WsgiToAsgi(app)
    
    # Vercel expects a WSGI application
    handler = wsgi_app
except ImportError:
    # Fallback: try Mangum if asgiref not available
    try:
        from mangum import Mangum
        mangum_adapter = Mangum(app, lifespan="off")
        def handler(event, context):
            return mangum_adapter(event, context)
    except ImportError:
        # Last resort: export app directly (may not work)
        handler = app
