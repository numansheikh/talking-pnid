FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the entire project structure
COPY backend/ ./backend/
COPY config/ ./config/
COPY data/ ./data/

# Expose port
EXPOSE 8000

# Set environment variables
ENV PROJECT_ROOT=/app
ENV PYTHONPATH=/app/backend

# Change to backend directory
WORKDIR /app/backend

# Verify files exist during build
RUN ls -la && \
    echo "=== File check ===" && \
    test -f main.py && echo "✓ main.py" || echo "✗ main.py MISSING" && \
    test -f entrypoint.py && echo "✓ entrypoint.py" || echo "✗ entrypoint.py MISSING" && \
    test -d api && echo "✓ api/" || echo "✗ api/ MISSING" && \
    test -d utils && echo "✓ utils/" || echo "✗ utils/ MISSING"

# Make entrypoint executable
RUN chmod +x entrypoint.py || echo "entrypoint.py not found"

# Direct CMD that tests import and shows error, then starts uvicorn
CMD python3 -u -c "
import sys, os, traceback
print('=== STARTING ===', file=sys.stderr)
print(f'PWD: {os.getcwd()}', file=sys.stderr)
print(f'PYTHONPATH: {os.environ.get(\"PYTHONPATH\", \"not set\")}', file=sys.stderr)
print(f'Files: {os.listdir(\".\")}', file=sys.stderr)
sys.path.insert(0, '.')
print('Testing imports...', file=sys.stderr)
try:
    print('1. utils.paths...', file=sys.stderr)
    from utils.paths import get_project_root
    print('   OK', file=sys.stderr)
    print('2. api.files...', file=sys.stderr)
    from api import files
    print('   OK', file=sys.stderr)
    print('3. main...', file=sys.stderr)
    import main
    print('   OK - starting uvicorn', file=sys.stderr)
    import uvicorn
    uvicorn.run(main.app, host='0.0.0.0', port=8000)
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"
