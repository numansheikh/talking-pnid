from fastapi import APIRouter, HTTPException
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from utils.paths import get_project_root, get_config_file, get_data_dir

router = APIRouter()

def load_config():
    """Load configuration from config.json or environment variables"""
    config_path = get_config_file("config.json")
    config = {
        "directories": {
            "pdfs": os.getenv("PDFS_DIR", "./data/pdfs"),
            "jsons": os.getenv("JSONS_DIR", "./data/jsons"),
            "mds": os.getenv("MDS_DIR", "./data/mds"),
        }
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config["directories"] = {
                    "pdfs": os.getenv("PDFS_DIR") or file_config.get("directories", {}).get("pdfs") or config["directories"]["pdfs"],
                    "jsons": os.getenv("JSONS_DIR") or file_config.get("directories", {}).get("jsons") or config["directories"]["jsons"],
                    "mds": os.getenv("MDS_DIR") or file_config.get("directories", {}).get("mds") or config["directories"]["mds"],
                }
        except Exception as e:
            print(f"Warning: Error reading config file: {e}")
    
    return config

def load_file_mappings():
    """Load file mappings from file-mappings.json"""
    mappings_path = get_config_file("file-mappings.json")
    try:
        with open(mappings_path, 'r') as f:
            return json.load(f)
    except Exception:
        return {"mappings": []}

def verify_files():
    """Verify which files exist in the directories"""
    config = load_config()
    
    # Use centralized path resolution
    pdfs_full_path = get_data_dir("pdfs")
    jsons_full_path = get_data_dir("jsons")
    mds_full_path = get_data_dir("mds")
    
    pdfs = []
    jsons = []
    mds = []
    
    try:
        if pdfs_full_path.exists():
            pdfs = [f for f in os.listdir(pdfs_full_path) if f.endswith('.pdf')]
    except Exception as e:
        print(f"Error reading PDFs directory: {e}")
    
    try:
        if jsons_full_path.exists():
            jsons = [f for f in os.listdir(jsons_full_path) if f.endswith('.json')]
    except Exception as e:
        print(f"Error reading JSONs directory: {e}")
    
    try:
        if mds_full_path.exists():
            mds = [f for f in os.listdir(mds_full_path) if f.endswith('.md')]
    except Exception as e:
        print(f"Error reading MDs directory: {e}")
    
    return {"pdfs": pdfs, "jsons": jsons, "mds": mds}

@router.get("/files")
async def get_files():
    """Get file mappings with existence verification"""
    try:
        mappings_data = load_file_mappings()
        files_data = verify_files()
        
        # Enrich mappings with file existence info
        enriched_mappings = []
        for mapping in mappings_data.get("mappings", []):
            enriched_mapping = {
                **mapping,
                "pdfExists": mapping.get("pdf", "") in files_data["pdfs"],
                "jsonExists": mapping.get("json", "") in files_data["jsons"] if mapping.get("json") else False,
                "mdExists": mapping.get("md", "") in files_data["mds"] if mapping.get("md") else False,
            }
            enriched_mappings.append(enriched_mapping)
        
        return {
            "mappings": enriched_mappings,
            "availablePdfs": files_data["pdfs"],
            "availableJsons": files_data["jsons"],
            "availableMds": files_data["mds"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load file mappings: {str(e)}")
