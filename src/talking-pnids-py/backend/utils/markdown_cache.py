import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class MarkdownFile:
    def __init__(self, filename: str, content: str, mtime: datetime):
        self.filename = filename
        self.content = content
        self.mtime = mtime

class MarkdownSummary:
    def __init__(self, filename: str, preview: str, size: int):
        self.filename = filename
        self.preview = preview
        self.size = size

class MarkdownCache:
    def __init__(self):
        self.markdowns: Dict[str, MarkdownFile] = {}
        self.summaries: Optional[List[MarkdownSummary]] = None
        self.last_loaded: Optional[float] = None
        self.mds_path: Optional[Path] = None
    
    def get_project_root(self) -> Path:
        """Get the project root directory"""
        if os.getenv("PROJECT_ROOT"):
            return Path(os.getenv("PROJECT_ROOT"))
        cwd = Path(os.getcwd())
        if cwd.name == "backend":
            return cwd.parent
        elif (cwd / "data").exists():
            return cwd
        elif (cwd.parent / "data").exists():
            return cwd.parent
        return Path(__file__).parent.parent.parent
    
    def load_config(self) -> Dict:
        """Load config to get mds directory"""
        project_root = self.get_project_root()
        config_path = project_root / "config" / "config.json"
        config = {
            "directories": {
                "mds": os.getenv("MDS_DIR", "./data/mds"),
            }
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    config["directories"]["mds"] = (
                        os.getenv("MDS_DIR") or 
                        file_config.get("directories", {}).get("mds") or 
                        config["directories"]["mds"]
                    )
            except Exception as e:
                print(f"Warning: Error reading config file: {e}")
        
        return config
    
    def get_mds_path(self) -> Path:
        """Get the markdown directory path"""
        config = self.load_config()
        base_path = self.get_project_root()
        mds_path = config["directories"]["mds"]
        if mds_path.startswith("./"):
            mds_path = mds_path[2:]
        return base_path / mds_path
    
    def create_summary(self, content: str, filename: str) -> MarkdownSummary:
        """Create a markdown summary"""
        preview = content[:500].replace('\n', ' ').strip()
        return MarkdownSummary(filename, preview, len(content))
    
    async def get_all_markdowns(self) -> List[str]:
        """Get all markdown contents (with caching)"""
        mds_path = self.get_mds_path()
        
        # Check if path changed
        if self.mds_path != mds_path:
            self.mds_path = mds_path
            self.markdowns.clear()
            self.summaries = None
        
        if not mds_path.exists():
            print(f"Warning: Markdown directory does not exist: {mds_path}")
            return []
        
        markdowns: List[str] = []
        now = datetime.now().timestamp()
        
        try:
            if not mds_path.exists():
                print(f"Error: Markdown path does not exist: {mds_path}")
                return []
            files = [f for f in os.listdir(mds_path) if f.endswith('.md')]
            if len(files) == 0:
                print(f"Warning: No markdown files found in {mds_path}")
            
            for file in files:
                file_path = mds_path / file
                
                # Check if we need to reload this file
                needs_reload = True
                if file in self.markdowns:
                    cached = self.markdowns[file]
                    try:
                        stats = file_path.stat()
                        file_mtime = datetime.fromtimestamp(stats.st_mtime)
                        if file_mtime == cached.mtime:
                            needs_reload = False
                            markdowns.append(cached.content)
                    except Exception:
                        # File might have been deleted
                        if file in self.markdowns:
                            del self.markdowns[file]
                
                if needs_reload:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        stats = file_path.stat()
                        mtime = datetime.fromtimestamp(stats.st_mtime)
                        
                        # Cache the markdown
                        self.markdowns[file] = MarkdownFile(file, content, mtime)
                        markdowns.append(content)
                    except Exception as e:
                        print(f"Error loading markdown file {file}: {e}")
            
            # Invalidate summaries cache if markdowns changed
            self.summaries = None
            self.last_loaded = now
            
        except Exception as e:
            print(f"Error loading markdown files: {e}")
        
        return markdowns
    
    def load_file_mappings(self) -> Dict:
        """Load file mappings"""
        mappings_path = Path(__file__).parent.parent.parent / "config" / "file-mappings.json"
        try:
            with open(mappings_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {"mappings": []}
    
    def save_file_mappings(self, mappings: Dict) -> bool:
        """Save file mappings"""
        mappings_path = Path(__file__).parent.parent.parent / "config" / "file-mappings.json"
        try:
            with open(mappings_path, 'w') as f:
                json.dump(mappings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving file mappings: {e}")
            return False
    
    async def get_markdown_summaries(self) -> List[MarkdownSummary]:
        """Get markdown summaries (with caching)"""
        # If summaries are cached, return them
        if self.summaries:
            return self.summaries
        
        # Load file mappings
        file_mappings = self.load_file_mappings()
        mappings = file_mappings.get("mappings", [])
        
        # Load all markdowns (which will update cache)
        await self.get_all_markdowns()
        
        summaries: List[MarkdownSummary] = []
        needs_update = False
        
        # For each markdown file, check if summary exists in mappings
        for cached in self.markdowns.values():
            # Find mapping by md filename
            mapping = next((m for m in mappings if m.get("md") == cached.filename), None)
            
            # Check if summary exists and if file size matches
            has_valid_summary = (
                mapping and 
                mapping.get("summary") and 
                mapping["summary"].get("preview") and 
                mapping["summary"].get("size") and
                mapping["summary"]["size"] == len(cached.content)
            )
            
            if has_valid_summary:
                # Use existing summary from file-mappings.json
                summaries.append(MarkdownSummary(
                    cached.filename,
                    mapping["summary"]["preview"],
                    mapping["summary"]["size"]
                ))
            else:
                # Generate new summary
                summary = self.create_summary(cached.content, cached.filename)
                summaries.append(summary)
                
                # Update the mapping with the new summary
                if mapping:
                    if "summary" not in mapping:
                        mapping["summary"] = {}
                    mapping["summary"]["preview"] = summary.preview
                    mapping["summary"]["size"] = summary.size
                    needs_update = True
                else:
                    # No mapping found, create minimal one
                    print(f"Warning: No mapping found for {cached.filename}, creating minimal entry")
                    mappings.append({
                        "id": f"pid-{cached.filename.replace('.md', '')}",
                        "md": cached.filename,
                        "name": f"P&ID {cached.filename.replace('.md', '')}",
                        "description": f"Piping & Instrumentation Diagram {cached.filename.replace('.md', '')}",
                        "summary": {
                            "preview": summary.preview,
                            "size": summary.size,
                        },
                    })
                    needs_update = True
        
        # Save updated mappings if any summaries were generated
        if needs_update:
            file_mappings["mappings"] = mappings
            self.save_file_mappings(file_mappings)
            print("Updated file-mappings.json with markdown summaries")
        
        # Cache summaries in memory
        self.summaries = summaries
        
        return summaries
    
    async def get_markdown_by_filename(self, filename: str) -> Optional[str]:
        """Get markdown content by filename (with caching)"""
        mds_path = self.get_mds_path()
        
        # Check cache first
        if filename in self.markdowns:
            cached = self.markdowns[filename]
            file_path = mds_path / filename
            try:
                stats = file_path.stat()
                file_mtime = datetime.fromtimestamp(stats.st_mtime)
                if file_mtime == cached.mtime:
                    return cached.content
            except Exception:
                # File might have been deleted
                if filename in self.markdowns:
                    del self.markdowns[filename]
        
        # Load from disk
        file_path = mds_path / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            stats = file_path.stat()
            mtime = datetime.fromtimestamp(stats.st_mtime)
            
            # Cache it
            self.markdowns[filename] = MarkdownFile(filename, content, mtime)
            
            return content
        except Exception as e:
            print(f"Error loading markdown file {filename}: {e}")
            return None

# Global cache instance
cache = MarkdownCache()
