from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from pathlib import Path
import json

router = APIRouter()

def get_project_root() -> Path:
    """Get the project root directory"""
    import os
    if os.getenv("PROJECT_ROOT"):
        return Path(os.getenv("PROJECT_ROOT"))
    
    # Walk up from current working directory to find data/
    cwd = Path(os.getcwd())
    current = cwd
    for _ in range(5):  # Go up max 5 levels
        if (current / "data").exists():
            return current
        if current.parent == current:  # Reached root
            break
        current = current.parent
    
    return Path(__file__).parent.parent.parent

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
        
        # Try to get project root from environment variable (set by api/index.py)
        # Otherwise fall back to relative path resolution
        if os.getenv("PROJECT_ROOT"):
            base_path = Path(os.getenv("PROJECT_ROOT"))
        else:
            # Fallback: try multiple path resolution strategies
            base_path = Path(__file__).parent.parent.parent
            
            # If we're in a serverless environment, try alternative paths
            if not (base_path / "data").exists():
                # Try relative to current working directory
                cwd = Path.cwd()
                if (cwd / "data").exists():
                    base_path = cwd
                elif (cwd.parent / "data").exists():
                    base_path = cwd.parent
                elif (cwd.parent.parent / "data").exists():
                    base_path = cwd.parent.parent
        
        pdfs_path = config["directories"]["pdfs"]
        if pdfs_path.startswith("./"):
            pdfs_path = pdfs_path[2:]
        pdfs_full_path = base_path / pdfs_path
        
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
