import json
import os
from pathlib import Path
from typing import Dict, Any

def get_project_root() -> Path:
    """Get the project root directory, handling different deployment scenarios"""
    # Strategy 1: Use PROJECT_ROOT env var if set
    if os.getenv("PROJECT_ROOT"):
        return Path(os.getenv("PROJECT_ROOT"))
    
    # Strategy 2: Walk up from current working directory to find data/
    cwd = Path(os.getcwd())
    current = cwd
    for _ in range(5):  # Go up max 5 levels
        if (current / "data").exists():
            return current
        if current.parent == current:  # Reached root
            break
        current = current.parent
    
    # Strategy 3: If this file is in backend/utils/, try going up
    utils_path = Path(__file__).parent
    if utils_path.name == "utils":
        potential_root = utils_path.parent.parent
        if (potential_root / "data").exists():
            return potential_root
    
    # Strategy 4: Default - assume we're in backend/utils/ so go up two levels
    return Path(__file__).parent.parent.parent

def load_config() -> Dict[str, Any]:
    """Load configuration from config.json or environment variables"""
    project_root = get_project_root()
    config_path = project_root / "config" / "config.json"
    config: Dict[str, Any] = {
        "openai": {
            "apiKey": os.getenv("OPENAI_API_KEY", ""),
            "model": os.getenv("OPENAI_MODEL", "gpt-4"),
        },
        "directories": {
            "pdfs": os.getenv("PDFS_DIR", "./data/pdfs"),
            "jsons": os.getenv("JSONS_DIR", "./data/jsons"),
            "mds": os.getenv("MDS_DIR", "./data/mds"),
        },
        "settings": {
            "maxTokens": int(os.getenv("MAX_TOKENS", "2000")),
            "temperature": float(os.getenv("TEMPERATURE", "0.7")),
        },
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                # Merge config (env vars override file config)
                config["openai"] = {
                    "apiKey": os.getenv("OPENAI_API_KEY") or file_config.get("openai", {}).get("apiKey") or config["openai"]["apiKey"],
                    "model": os.getenv("OPENAI_MODEL") or file_config.get("openai", {}).get("model") or config["openai"]["model"],
                }
                config["directories"] = {
                    "pdfs": os.getenv("PDFS_DIR") or file_config.get("directories", {}).get("pdfs") or config["directories"]["pdfs"],
                    "jsons": os.getenv("JSONS_DIR") or file_config.get("directories", {}).get("jsons") or config["directories"]["jsons"],
                    "mds": os.getenv("MDS_DIR") or file_config.get("directories", {}).get("mds") or config["directories"]["mds"],
                }
                config["settings"] = {
                    "maxTokens": int(os.getenv("MAX_TOKENS") or str(file_config.get("settings", {}).get("maxTokens", config["settings"]["maxTokens"]))),
                    "temperature": float(os.getenv("TEMPERATURE") or str(file_config.get("settings", {}).get("temperature", config["settings"]["temperature"]))),
                }
        except Exception as e:
            print(f"Warning: Error reading config file: {e}")
    
    return config

def load_prompts() -> Dict[str, Any] | None:
    """Load prompts from prompts.json"""
    project_root = get_project_root()
    prompts_path = project_root / "config" / "prompts.json"
    try:
        with open(prompts_path, 'r') as f:
            return json.load(f)
    except Exception:
        return None
