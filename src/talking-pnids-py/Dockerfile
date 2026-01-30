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

# Use entrypoint script - it has all the debugging
CMD ["python3", "-u", "entrypoint.py"]
