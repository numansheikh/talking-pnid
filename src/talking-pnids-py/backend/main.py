from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from api import files, session, query, pdf

load_dotenv()

app = FastAPI(title="Talking P&IDs API")

# CORS middleware - allow localhost for local development
# For production, set FRONTEND_URL environment variable (comma-separated for multiple origins)
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    # Support comma-separated origins
    allowed_origins = [origin.strip() for origin in frontend_url.split(",")]
else:
    # Local development - allow common localhost ports
    allowed_origins = ["http://localhost:3000", "http://localhost:5173"]

# Always include Vercel frontend URL if not already present
vercel_frontend = "https://talking-pnid.vercel.app"
if vercel_frontend not in allowed_origins:
    allowed_origins.append(vercel_frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(session.router, prefix="/api", tags=["session"])
app.include_router(query.router, prefix="/api", tags=["query"])
app.include_router(pdf.router, prefix="/api", tags=["pdf"])

@app.get("/")
async def root():
    return {"message": "Talking P&IDs API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/debug/paths")
async def debug_paths():
    """Debug endpoint to check paths"""
    from utils.paths import get_project_root, get_config_file, get_data_dir
    from pathlib import Path
    import os
    
    # Initialize variables to avoid UnboundLocalError
    base_path = None
    config_path = None
    data_pdfs = None
    data_mds = None
    data_jsons = None
    
    try:
        base_path = get_project_root()
        config_path = get_config_file("config.json")
        data_pdfs = get_data_dir("pdfs")
        data_mds = get_data_dir("mds")
        data_jsons = get_data_dir("jsons")
        
        # Convert Path objects to strings for JSON serialization
        pdf_files = [str(f.name) for f in data_pdfs.glob("*.pdf")] if data_pdfs and data_pdfs.exists() else []
        md_files = [str(f.name) for f in data_mds.glob("*.md")] if data_mds and data_mds.exists() else []
        json_files = [str(f.name) for f in data_jsons.glob("*.json")] if data_jsons and data_jsons.exists() else []
        
        return {
            "base_path": str(base_path) if base_path else "not set",
            "config_exists": config_path.exists() if config_path else False,
            "config_path": str(config_path) if config_path else "not set",
            "data_pdfs_exists": data_pdfs.exists() if data_pdfs else False,
            "data_pdfs_path": str(data_pdfs) if data_pdfs else "not set",
            "data_pdfs_files": pdf_files,
            "data_mds_exists": data_mds.exists() if data_mds else False,
            "data_mds_path": str(data_mds) if data_mds else "not set",
            "data_mds_files": md_files,
            "data_jsons_exists": data_jsons.exists() if data_jsons else False,
            "data_jsons_path": str(data_jsons) if data_jsons else "not set",
            "data_jsons_files": json_files,
            "cwd": os.getcwd(),
            "__file__": __file__,
            "PROJECT_ROOT": os.getenv("PROJECT_ROOT", "not set"),
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "base_path": str(base_path) if base_path else "not set",
            "config_path": str(config_path) if config_path else "not set",
            "cwd": os.getcwd(),
            "__file__": __file__,
            "PROJECT_ROOT": os.getenv("PROJECT_ROOT", "not set"),
        }

if __name__ == "__main__":
    import uvicorn
    # Read port from environment variable (Koyeb sets PORT)
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
