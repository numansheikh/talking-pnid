from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from pathlib import Path
from utils.paths import get_config_file
from datetime import datetime

router = APIRouter()

# Knowledge base storage file
KNOWLEDGE_FILE = get_config_file("knowledge_base.json")

class KnowledgeEntry(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    page_count: Optional[int] = None

class KnowledgeList(BaseModel):
    entries: List[KnowledgeEntry]
    total_count: int

def load_knowledge_base() -> dict:
    """Load the knowledge base from file"""
    if KNOWLEDGE_FILE.exists():
        try:
            with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            return {"entries": []}
    return {"entries": []}

def save_knowledge_base(data: dict):
    """Save the knowledge base to file"""
    try:
        KNOWLEDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(KNOWLEDGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving knowledge: {e}")

@router.get("/knowledge")
async def list_knowledge():
    """Get all knowledge entries"""
    kb = load_knowledge_base()
    entries = [KnowledgeEntry(**entry) for entry in kb.get("entries", [])]
    return KnowledgeList(entries=entries, total_count=len(entries))

@router.get("/knowledge/{knowledge_id}")
async def get_knowledge(knowledge_id: str):
    """Get a specific knowledge entry"""
    kb = load_knowledge_base()
    for entry in kb.get("entries", []):
        if entry["id"] == knowledge_id:
            return KnowledgeEntry(**entry)
    raise HTTPException(status_code=404, detail=f"Knowledge entry '{knowledge_id}' not found")

@router.post("/knowledge")
async def create_knowledge(entry: KnowledgeEntry):
    """Create a new knowledge entry"""
    kb = load_knowledge_base()
    
    # Check if ID already exists
    for existing in kb.get("entries", []):
        if existing["id"] == entry.id:
            raise HTTPException(status_code=400, detail=f"Knowledge entry with ID '{entry.id}' already exists")
    
    # Calculate page count (roughly 400 words per page)
    word_count = len(entry.content.split())
    page_count = max(1, word_count // 400)
    
    now = datetime.now().isoformat()
    new_entry = {
        "id": entry.id,
        "title": entry.title,
        "content": entry.content,
        "created_at": now,
        "updated_at": now,
        "page_count": page_count
    }
    
    kb["entries"].append(new_entry)
    save_knowledge_base(kb)
    
    return KnowledgeEntry(**new_entry)

@router.put("/knowledge/{knowledge_id}")
async def update_knowledge(knowledge_id: str, entry: KnowledgeEntry):
    """Update an existing knowledge entry"""
    kb = load_knowledge_base()
    
    found = False
    for i, existing in enumerate(kb.get("entries", [])):
        if existing["id"] == knowledge_id:
            # Calculate page count
            word_count = len(entry.content.split())
            page_count = max(1, word_count // 400)
            
            updated_entry = {
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "created_at": existing["created_at"],
                "updated_at": datetime.now().isoformat(),
                "page_count": page_count
            }
            kb["entries"][i] = updated_entry
            found = True
            break
    
    if not found:
        raise HTTPException(status_code=404, detail=f"Knowledge entry '{knowledge_id}' not found")
    
    save_knowledge_base(kb)
    return KnowledgeEntry(**kb["entries"][i])

@router.delete("/knowledge/{knowledge_id}")
async def delete_knowledge(knowledge_id: str):
    """Delete a knowledge entry"""
    kb = load_knowledge_base()
    
    original_count = len(kb.get("entries", []))
    kb["entries"] = [e for e in kb.get("entries", []) if e["id"] != knowledge_id]
    
    if len(kb["entries"]) == original_count:
        raise HTTPException(status_code=404, detail=f"Knowledge entry '{knowledge_id}' not found")
    
    save_knowledge_base(kb)
    return {"message": f"Knowledge entry '{knowledge_id}' deleted successfully"}

@router.get("/knowledge-context")
async def get_full_context():
    """Get all knowledge as a single context string for GPT"""
    kb = load_knowledge_base()
    entries = kb.get("entries", [])
    
    if not entries:
        return {"context": "", "entry_count": 0}
    
    context_parts = []
    for entry in entries:
        context_parts.append(f"=== {entry['title']} ===\n{entry['content']}\n")
    
    full_context = "\n".join(context_parts)
    return {
        "context": full_context,
        "entry_count": len(entries),
        "total_pages": sum(e.get("page_count", 1) for e in entries)
    }

@router.post("/knowledge/batch-import")
async def batch_import_knowledge(data: dict):
    """Batch import multiple knowledge entries"""
    if "entries" not in data:
        raise HTTPException(status_code=400, detail="Missing 'entries' field")
    
    kb = load_knowledge_base()
    imported_count = 0
    
    for entry_data in data["entries"]:
        try:
            entry = KnowledgeEntry(
                id=entry_data.get("id", ""),
                title=entry_data.get("title", ""),
                content=entry_data.get("content", "")
            )
            
            if not entry.id or not entry.title:
                continue
            
            # Check if exists
            existing = any(e["id"] == entry.id for e in kb.get("entries", []))
            if existing:
                continue
            
            # Calculate page count
            word_count = len(entry.content.split())
            page_count = max(1, word_count // 400)
            now = datetime.now().isoformat()
            
            new_entry = {
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "created_at": now,
                "updated_at": now,
                "page_count": page_count
            }
            kb["entries"].append(new_entry)
            imported_count += 1
        except Exception as e:
            print(f"Error importing entry: {e}")
            continue
    
    save_knowledge_base(kb)
    return {
        "imported_count": imported_count,
        "total_entries": len(kb["entries"])
    }
