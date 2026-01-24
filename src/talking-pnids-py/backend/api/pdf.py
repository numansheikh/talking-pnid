from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from pathlib import Path
import json

router = APIRouter()

def load_config():
    """Load configuration from config.json or environment variables"""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.json"
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
        base_path = Path(__file__).parent.parent.parent
        
        pdfs_path = config["directories"]["pdfs"]
        if pdfs_path.startswith("./"):
            pdfs_path = pdfs_path[2:]
        pdfs_full_path = base_path / pdfs_path
        
        file_path = pdfs_full_path / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
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
        raise HTTPException(status_code=500, detail=f"Failed to load PDF: {str(e)}")
