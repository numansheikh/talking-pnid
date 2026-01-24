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
    from starlette.requests import Request as StarletteRequest
    from starlette.responses import Response
    
    # Parse the request
    method = request_data.get("method", "GET")
    path = request_data.get("path", "/")
    headers = request_data.get("headers", {})
    body = request_data.get("body", "")
    query_string = request_data.get("queryStringParameters", {})
    
    # Build query string
    if query_string:
        qs = "&".join([f"{k}={v}" for k, v in query_string.items()])
    else:
        qs = ""
    
    # Normalize headers - Vercel might send them in different formats
    normalized_headers = []
    for k, v in headers.items():
        if isinstance(v, list):
            for item in v:
                normalized_headers.append([k.lower().encode(), str(item).encode()])
        else:
            normalized_headers.append([k.lower().encode(), str(v).encode()])
    
    # Create ASGI scope
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": qs.encode(),
        "headers": normalized_headers,
        "client": None,
        "server": None,
        "scheme": "https",
        "root_path": "",
        "path_params": {},
    }
    
    # Create request and response
    async def receive():
        return {
            "type": "http.request",
            "body": body.encode() if isinstance(body, str) else body,
            "more_body": False
        }
    
    response_parts = {"status": None, "headers": [], "body": b""}
    
    async def send(message):
        if message["type"] == "http.response.start":
            response_parts["status"] = message["status"]
            response_parts["headers"] = message["headers"]
        elif message["type"] == "http.response.body":
            response_parts["body"] += message.get("body", b"")
    
    # Call FastAPI app
    await app(scope, receive, send)
    
    # Format response
    headers_dict = {k.decode(): v.decode() for k, v in response_parts["headers"]}
    
    return {
        "statusCode": response_parts["status"] or 200,
        "headers": headers_dict,
        "body": response_parts["body"].decode("utf-8") if response_parts["body"] else ""
    }

def handler(request):
    """Vercel serverless function handler"""
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    
    try:
        # Parse Vercel's request format
        # Vercel sends: {"method": "GET", "path": "/api/files", "headers": {...}, "body": ""}
        method = request.get("method") or request.get("httpMethod", "GET")
        path = request.get("path") or request.get("url", "/")
        headers = request.get("headers") or {}
        body = request.get("body") or ""
        query_params = request.get("queryStringParameters") or {}
        
        # Simple health check endpoint
        if path == "/api/health" or path == "/health":
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    **cors_headers
                },
                "body": json.dumps({"status": "ok", "message": "Backend is working", "path": path, "method": method})
            }
        
        # Handle OPTIONS preflight
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": ""
            }
        
        # Prepare request data
        request_data = {
            "method": method,
            "path": path,
            "headers": headers,
            "body": body,
            "queryStringParameters": query_params
        }
        
        # Process the request
        result = asyncio.run(handle_request(request_data))
        result["headers"].update(cors_headers)
        return result
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Handler error: {error_trace}")
        print(f"Request received: {json.dumps(request, default=str)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                **cors_headers
            },
            "body": json.dumps({
                "error": str(e),
                "message": "Backend error - check Vercel function logs",
                "request_path": request.get("path", "unknown"),
                "request_method": request.get("method", "unknown")
            })
        }
