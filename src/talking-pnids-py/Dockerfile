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

# Run the application from backend directory
WORKDIR /app/backend

# Set environment variables for path resolution
ENV PROJECT_ROOT=/app
ENV PYTHONPATH=/app/backend:/app

# Run the application using python -m for better import resolution
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
