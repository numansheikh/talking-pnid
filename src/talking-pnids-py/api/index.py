"""
Vercel serverless function entry point for FastAPI
"""
import sys
import os
from pathlib import Path

# Add backend directory to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Import FastAPI app
from main import app

# Wrap FastAPI app with Mangum for Vercel/Lambda compatibility
from mangum import Mangum

handler = Mangum(app, lifespan="off")
