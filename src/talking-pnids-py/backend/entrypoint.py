#!/usr/bin/env python3
"""Entrypoint script to test imports and start uvicorn"""
import sys
import traceback
import os

# Write directly to stderr (always visible)
def log(msg):
    sys.stderr.write(str(msg) + "\n")
    sys.stderr.flush()

log("=== ENTRYPOINT STARTING ===")
log(f"PWD: {os.getcwd()}")
log(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'not set')}")
try:
    files = os.listdir('.')
    log(f"Files in current dir (first 10): {files[:10]}")
except Exception as e:
    log(f"Error listing files: {e}")

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))
log(f"Python sys.path (first 3): {sys.path[:3]}")

log("\n=== Testing step-by-step imports ===")
try:
    log("1. Testing utils.paths...")
    from utils.paths import get_project_root
    log("   ✓ utils.paths OK")
except Exception as e:
    log(f"   ✗ utils.paths FAILED: {e}")
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

try:
    log("2. Testing api.files...")
    from api import files
    log("   ✓ api.files OK")
except Exception as e:
    log(f"   ✗ api.files FAILED: {e}")
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

try:
    log("3. Testing main module...")
    import main
    log("   ✓ main imported successfully")
    log(f"   ✓ app type: {type(main.app)}")
except Exception as e:
    log(f"   ✗ main FAILED: {type(e).__name__}: {e}")
    log("   Full traceback:")
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

log("\n=== Starting uvicorn ===")
import uvicorn
uvicorn.run(main.app, host="0.0.0.0", port=8000)
