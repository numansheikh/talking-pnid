"""
Vercel serverless function entry point for FastAPI
Uses a simple HTTP handler that Vercel can understand
"""
import sys
import os
from pathlib import Path
import json

# Set working directory to project root
project_root = Path(__file__).parent.parent
os.chdir(project_root)

# Add backend directory to Python path
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

# Set environment variable for path resolution
os.environ["PROJECT_ROOT"] = str(project_root)

# Import FastAPI app and create a simple handler
from main import app
from fastapi import Request
from fastapi.responses import Response
import asyncio

async def handle_request(request_data):
    """Handle a request using FastAPI"""
    # Parse the request
    method = request_data.get("method", "GET")
    path = request_data.get("path", "/")
    headers = request_data.get("headers", {})
    body = request_data.get("body", "")
    
    # Create a FastAPI Request object
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [[k.encode(), v.encode()] for k, v in headers.items()],
        "query_string": b"",
    }
    
    # Create a mock request
    request = Request(scope)
    if body:
        request._body = body.encode() if isinstance(body, str) else body
    
    # Call the FastAPI app
    response = await app(request.scope, request.receive, lambda x: None)
    
    # Extract response
    status_code = response.status_code
    response_headers = dict(response.headers)
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk
    
    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": response_body.decode() if isinstance(response_body, bytes) else str(response_body)
    }

def handler(request):
    """Vercel serverless function handler"""
    try:
        # Handle CORS
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        
        # Handle OPTIONS preflight
        if request.get("method") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": ""
            }
        
        # Process the request
        result = asyncio.run(handle_request(request))
        result["headers"].update(cors_headers)
        return result
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Handler error: {error_trace}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                **cors_headers
            },
            "body": json.dumps({"error": str(e), "traceback": error_trace})
        }
