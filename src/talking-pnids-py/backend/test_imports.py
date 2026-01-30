#!/usr/bin/env python3
"""Test script to verify all imports work correctly"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("Testing imports...")

try:
    print("1. Testing utils.paths...")
    from utils.paths import get_project_root, get_data_dir, get_config_file
    print("   ✓ utils.paths imported successfully")
    
    print("2. Testing utils.config...")
    from utils.config import load_config, load_prompts
    print("   ✓ utils.config imported successfully")
    
    print("3. Testing utils.markdown_cache...")
    from utils.markdown_cache import cache
    print("   ✓ utils.markdown_cache imported successfully")
    
    print("4. Testing utils.langchain_setup...")
    from utils.langchain_setup import get_chat_model
    print("   ✓ utils.langchain_setup imported successfully")
    
    print("5. Testing api.files...")
    from api import files
    print("   ✓ api.files imported successfully")
    
    print("6. Testing api.session...")
    from api import session
    print("   ✓ api.session imported successfully")
    
    print("7. Testing api.query...")
    from api import query
    print("   ✓ api.query imported successfully")
    
    print("8. Testing api.pdf...")
    from api import pdf
    print("   ✓ api.pdf imported successfully")
    
    print("9. Testing main...")
    import main
    print("   ✓ main imported successfully")
    
    print("\n✅ All imports successful!")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
