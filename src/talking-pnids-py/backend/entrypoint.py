#!/usr/bin/env python3
"""Entrypoint script to test imports and start uvicorn"""
import sys
import traceback
import os

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)

print("=== ENTRYPOINT STARTING ===")
print(f"PWD: {os.getcwd()}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'not set')}")
print(f"Files in current dir: {os.listdir('.')}")

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))
print(f"Python sys.path: {sys.path[:3]}")

print("\n=== Testing step-by-step imports ===")
try:
    print("1. Testing utils.paths...")
    from utils.paths import get_project_root
    print("   ✓ utils.paths OK")
except Exception as e:
    print(f"   ✗ utils.paths FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("2. Testing api.files...")
    from api import files
    print("   ✓ api.files OK")
except Exception as e:
    print(f"   ✗ api.files FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("3. Testing main module...")
    import main
    print("   ✓ main imported successfully")
    print(f"   ✓ app type: {type(main.app)}")
except Exception as e:
    print(f"   ✗ main FAILED: {type(e).__name__}: {e}")
    print("   Full traceback:")
    traceback.print_exc()
    sys.exit(1)

print("\n=== Starting uvicorn ===")
import uvicorn
uvicorn.run(main.app, host="0.0.0.0", port=8000)
