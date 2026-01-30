#!/usr/bin/env python3
"""Entrypoint script to test imports and start uvicorn"""
import sys
import traceback
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("=== Testing imports ===", file=sys.stderr)
try:
    print("Importing main...", file=sys.stderr)
    import main
    print("✓ main imported successfully", file=sys.stderr)
    print(f"✓ app type: {type(main.app)}", file=sys.stderr)
except Exception as e:
    print(f"✗ Import failed: {type(e).__name__}: {e}", file=sys.stderr)
    print("Full traceback:", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

print("=== Starting uvicorn ===", file=sys.stderr)
import uvicorn
uvicorn.run(main.app, host="0.0.0.0", port=8000)
