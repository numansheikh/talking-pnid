from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from api import files, session, query, pdf

load_dotenv()

app = FastAPI(title="Talking P&IDs API")

# CORS middleware - allow localhost and production domains
# In production (Koyeb, Vercel, etc.), allow all origins
# For local dev, allow localhost
# Always allow all origins in production - Koyeb doesn't set KOYEB env var by default
is_production = os.getenv("VERCEL") or os.getenv("KOYEB") or os.getenv("RAILWAY") or os.getenv("RENDER") or os.getenv("PORT")
allowed_origins = ["*"] if is_production else ["http://localhost:3000"]

# Add environment variable for custom domain if set (overrides above)
if os.getenv("FRONTEND_URL"):
    allowed_origins = [os.getenv("FRONTEND_URL")]

# Log CORS configuration for debugging
print(f"CORS Configuration: is_production={is_production}, allowed_origins={allowed_origins}")

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
    from pathlib import Path
    import os
    
    # main.py is in backend/, so parent.parent is the project root
    base_path = Path(__file__).parent.parent
    config_path = base_path / "config" / "config.json"
    data_pdfs = base_path / "data" / "pdfs"
    data_mds = base_path / "data" / "mds"
    data_jsons = base_path / "data" / "jsons"
    
    # Convert Path objects to strings for JSON serialization
    pdf_files = [str(f.name) for f in data_pdfs.glob("*.pdf")] if data_pdfs.exists() else []
    md_files = [str(f.name) for f in data_mds.glob("*.md")] if data_mds.exists() else []
    json_files = [str(f.name) for f in data_jsons.glob("*.json")] if data_jsons.exists() else []
    
    return {
        "base_path": str(base_path),
        "config_exists": config_path.exists(),
        "config_path": str(config_path),
        "data_pdfs_exists": data_pdfs.exists(),
        "data_pdfs_path": str(data_pdfs),
        "data_pdfs_files": pdf_files,
        "data_mds_exists": data_mds.exists(),
        "data_mds_path": str(data_mds),
        "data_mds_files": md_files,
        "data_jsons_exists": data_jsons.exists(),
        "data_jsons_path": str(data_jsons),
        "data_jsons_files": json_files,
        "cwd": os.getcwd(),
        "__file__": __file__,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
