"""
Centralized path resolution utility for the backend.
This ensures consistent path resolution across all modules.
"""
import os
from pathlib import Path
from typing import Optional

def get_project_root() -> Path:
    """
    Get the project root directory using multiple strategies.
    
    Strategy priority:
    1. PROJECT_ROOT environment variable (set by Dockerfile)
    2. Walk up from current working directory to find data/ directory
    3. If main.py is in backend/, go up one level
    4. Fallback to calculated path from this file's location
    
    Returns:
        Path: The project root directory
    """
    # Strategy 1: Use PROJECT_ROOT env var if set (for containerized/serverless deployments)
    project_root_env = os.getenv("PROJECT_ROOT")
    if project_root_env:
        root = Path(project_root_env)
        if root.exists():
            return root
    
    # Strategy 2: Walk up from current working directory to find data/
    cwd = Path(os.getcwd())
    current = cwd
    for _ in range(10):  # Go up max 10 levels
        if (current / "data").exists() and (current / "config").exists():
            return current
        if current.parent == current:  # Reached filesystem root
            break
        current = current.parent
    
    # Strategy 3: If we're in backend/, go up one level
    # Check if main.py exists in a backend/ subdirectory
    cwd = Path(os.getcwd())
    if (cwd / "backend" / "main.py").exists():
        return cwd
    if cwd.name == "backend" and (cwd.parent / "data").exists():
        return cwd.parent
    
    # Strategy 4: Calculate from this file's location
    # This file is in backend/utils/, so go up 2 levels
    utils_path = Path(__file__).parent
    if utils_path.name == "utils":
        potential_root = utils_path.parent.parent
        if (potential_root / "data").exists() and (potential_root / "config").exists():
            return potential_root
    
    # Fallback: return calculated path anyway
    return utils_path.parent.parent if utils_path.name == "utils" else Path("/app")

def get_data_dir(subdir: Optional[str] = None) -> Path:
    """
    Get the data directory path.
    Supports environment variables for absolute paths (useful for cloud deployment).
    
    Args:
        subdir: Optional subdirectory (e.g., 'pdfs', 'jsons', 'mds')
    
    Returns:
        Path: The data directory or subdirectory path
    """
    # Check for environment variable first (allows absolute paths for cloud deployment)
    if subdir == "pdfs":
        env_path = os.getenv("PDFS_DIR")
    elif subdir == "jsons":
        env_path = os.getenv("JSONS_DIR")
    elif subdir == "mds":
        env_path = os.getenv("MDS_DIR")
    else:
        env_path = None
    
    # If environment variable is set and is an absolute path, use it directly
    if env_path:
        env_path_obj = Path(env_path)
        if env_path_obj.is_absolute():
            return env_path_obj
    
    # Otherwise, use project root relative path
    project_root = get_project_root()
    data_dir = project_root / "data"
    if subdir:
        # If env var is set but relative, resolve it relative to project root
        if env_path:
            return (project_root / env_path).resolve()
        return data_dir / subdir
    return data_dir

def get_config_dir() -> Path:
    """
    Get the config directory path.
    
    Returns:
        Path: The config directory path
    """
    project_root = get_project_root()
    return project_root / "config"

def get_config_file(filename: str = "config.json") -> Path:
    """
    Get a config file path.
    
    Args:
        filename: Name of the config file
    
    Returns:
        Path: The config file path
    """
    return get_config_dir() / filename
