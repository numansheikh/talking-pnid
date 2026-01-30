#!/bin/bash
# Startup script to debug and start the application

echo "=== Environment Debug ==="
echo "PWD: $(pwd)"
echo "PROJECT_ROOT: ${PROJECT_ROOT:-not set}"
echo "PYTHONPATH: ${PYTHONPATH:-not set}"
echo ""

echo "=== Directory Structure ==="
ls -la
echo ""

echo "=== Checking if main.py exists ==="
if [ -f "main.py" ]; then
    echo "✓ main.py exists"
else
    echo "✗ main.py NOT FOUND!"
    exit 1
fi

echo "=== Python Path ==="
python3 -c "import sys; print('\n'.join(sys.path))"
echo ""

echo "=== Testing Import with full error output ==="
python3 << 'PYTHON_SCRIPT'
import sys
import traceback
sys.path.insert(0, '.')

try:
    print("Attempting to import main...")
    import main
    print("✓ main imported successfully")
    print(f"✓ main.app type: {type(main.app)}")
except Exception as e:
    print("✗ Import failed!")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -ne 0 ]; then
    echo "Import test failed, but continuing anyway..."
fi

echo ""
echo "=== Starting Uvicorn ==="
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
