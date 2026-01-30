from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from pathlib import Path
import json
from utils.paths import get_project_root, get_data_dir

router = APIRouter()

def load_config():
    """Load configuration from config.json or environment variables"""
    project_root = get_project_root()
    config_path = project_root / "config" / "config.json"
    config = {
        "directories": {
            "pdfs": os.getenv("PDFS_DIR", "./data/pdfs"),
        }
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config["directories"]["pdfs"] = (
                    os.getenv("PDFS_DIR") or 
                    file_config.get("directories", {}).get("pdfs") or 
                    config["directories"]["pdfs"]
                )
        except Exception as e:
            print(f"Warning: Error reading config file: {e}")
    
    return config

@router.get("/pdf/{filename:path}")
async def get_pdf(filename: str):
    """Serve PDF file"""
    try:
        # Security: Only allow PDF files
        if not filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        config = load_config()
        
        # Use centralized path resolution
        pdfs_full_path = get_data_dir("pdfs")
        
        file_path = pdfs_full_path / filename
        
        if not file_path.exists():
            # Log for debugging
            import os
            print(f"PDF not found: {file_path}")
            print(f"Base path: {base_path}")
            print(f"PDFs path: {pdfs_full_path}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"__file__ location: {__file__}")
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        return FileResponse(
            str(file_path),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "public, max-age=3600",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"PDF loading error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to load PDF: {str(e)}")
