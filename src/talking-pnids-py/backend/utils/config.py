import json
import os
from pathlib import Path
from typing import Dict, Any
from utils.paths import get_project_root, get_config_file

def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables (priority) or config.json.
    
    Environment variables take precedence over config.json.
    This allows for easy deployment across different environments.
    """
    config_path = get_config_file("config.json")
    
    # Start with defaults
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
            "reasoningEffort": os.getenv("REASONING_EFFORT", "medium"),
        },
    }
    
    # Load from config.json if it exists (env vars already override above)
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                # Only use file config if env var is not set
                config["openai"] = {
                    "apiKey": os.getenv("OPENAI_API_KEY") or file_config.get("openai", {}).get("apiKey", ""),
                    "model": os.getenv("OPENAI_MODEL") or file_config.get("openai", {}).get("model", config["openai"]["model"]),
                }
                config["directories"] = {
                    "pdfs": os.getenv("PDFS_DIR") or file_config.get("directories", {}).get("pdfs", config["directories"]["pdfs"]),
                    "jsons": os.getenv("JSONS_DIR") or file_config.get("directories", {}).get("jsons", config["directories"]["jsons"]),
                    "mds": os.getenv("MDS_DIR") or file_config.get("directories", {}).get("mds", config["directories"]["mds"]),
                }
                config["settings"] = {
                    "maxTokens": int(os.getenv("MAX_TOKENS") or str(file_config.get("settings", {}).get("maxTokens", config["settings"]["maxTokens"]))),
                    "temperature": float(os.getenv("TEMPERATURE") or str(file_config.get("settings", {}).get("temperature", config["settings"]["temperature"]))),
                    "reasoningEffort": os.getenv("REASONING_EFFORT") or file_config.get("settings", {}).get("reasoningEffort", config["settings"]["reasoningEffort"]),
                }
        except Exception as e:
            print(f"Warning: Error reading config file: {e}")
    
    return config

def load_prompts() -> Dict[str, Any] | None:
    """Load prompts from prompts.json"""
    prompts_path = get_config_file("prompts.json")
    try:
        with open(prompts_path, 'r') as f:
            return json.load(f)
    except Exception:
        return None
