#!/bin/bash
set -e  # Exit on error
set -x  # Print commands

# Force output to stdout/stderr (not buffered)
exec 1>&2

echo "=== STARTUP SCRIPT RUNNING ===" >&2
echo "PWD: $(pwd)" >&2
echo "PROJECT_ROOT: ${PROJECT_ROOT:-not set}" >&2
echo "PYTHONPATH: ${PYTHONPATH:-not set}" >&2

echo "=== Directory Structure ===" >&2
ls -la >&2

echo "=== Checking if main.py exists ===" >&2
if [ -f "main.py" ]; then
    echo "✓ main.py exists" >&2
else
    echo "✗ main.py NOT FOUND!" >&2
    exit 1
fi

echo "=== Python Path ===" >&2
python3 -c "import sys; print('\n'.join(sys.path))" >&2

echo "=== Testing Import ===" >&2
python3 -c "
import sys
import traceback
sys.path.insert(0, '.')
try:
    print('Attempting to import main...', file=sys.stderr)
    import main
    print('✓ main imported successfully', file=sys.stderr)
    print(f'✓ main.app type: {type(main.app)}', file=sys.stderr)
except Exception as e:
    print('✗ Import failed!', file=sys.stderr)
    print(f'Error type: {type(e).__name__}', file=sys.stderr)
    print(f'Error message: {str(e)}', file=sys.stderr)
    print('Full traceback:', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
" 2>&1

echo "=== Starting Uvicorn ===" >&2
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
