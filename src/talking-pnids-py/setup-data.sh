#!/bin/bash

# Script to copy data files from JS project to Python project

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JS_DATA_DIR="$SCRIPT_DIR/../talking-pnids-js/data"
PY_DATA_DIR="$SCRIPT_DIR/data"

echo "Setting up data directory..."

# Create data directories
mkdir -p "$PY_DATA_DIR/pdfs"
mkdir -p "$PY_DATA_DIR/jsons"
mkdir -p "$PY_DATA_DIR/mds"

# Copy files if source exists
if [ -d "$JS_DATA_DIR" ]; then
    echo "Copying PDFs..."
    cp -r "$JS_DATA_DIR/pdfs"/* "$PY_DATA_DIR/pdfs/" 2>/dev/null || echo "No PDFs to copy"
    
    echo "Copying JSONs..."
    cp -r "$JS_DATA_DIR/jsons"/* "$PY_DATA_DIR/jsons/" 2>/dev/null || echo "No JSONs to copy"
    
    echo "Copying Markdown files..."
    cp -r "$JS_DATA_DIR/mds"/* "$PY_DATA_DIR/mds/" 2>/dev/null || echo "No MDs to copy"
    
    echo "Data files copied successfully!"
    echo ""
    echo "Files in data directory:"
    ls -la "$PY_DATA_DIR/pdfs/" 2>/dev/null | head -5
    ls -la "$PY_DATA_DIR/mds/" 2>/dev/null | head -5
else
    echo "Error: JS project data directory not found at $JS_DATA_DIR"
    echo "Please ensure the talking-pnids-js project exists in the parent directory"
fi
