from fastapi import APIRouter, HTTPException
from utils.config import load_config, load_prompts
from utils.markdown_cache import cache
from utils.langchain_setup import (
    get_chat_model,
    get_system_prompt_template,
    get_session_init_prompt,
    create_messages_with_history,
    add_to_history,
    get_openai_client,
    invoke_with_reasoning
)
import time

router = APIRouter()

@router.post("/session")
async def start_session():
    """Initialize a session with LangChain"""
    try:
        import traceback
        print("Session initialization started...")
        
        config = load_config()
        print(f"Config loaded, model: {config.get('openai', {}).get('model', 'N/A')}")
        
        prompts = load_prompts()
        print(f"Prompts loaded: {'yes' if prompts else 'no'}")
        
        # Load all markdown files (cached)
        print("Loading all markdown files...")
        await cache.get_all_markdowns()  # This populates the cache
        print(f"Markdown files loaded: {len(cache.markdowns)}")
        
        if len(cache.markdowns) == 0:
            raise HTTPException(
                status_code=404,
                detail="No markdown files found. Please add markdown files to the data/mds folder."
            )
        
        # Get system prompt
        system_prompt = get_system_prompt_template(prompts)
        
        # Get session init prompt
        session_init_prompt = get_session_init_prompt(prompts, len(cache.markdowns))
        
        # Prepare context with full markdown content
        markdown_parts = []
        for idx, (filename, markdown_file) in enumerate(cache.markdowns.items(), 1):
            markdown_parts.append(
                f"=== P&ID Documentation File {idx}: {filename} ===\n\n{markdown_file.content}\n\n"
            )
        
        markdowns_context = (
            f"P&ID Documentation ({len(cache.markdowns)} systems available):\n\n"
            + "".join(markdown_parts)
        )
        
        # Create session ID
        session_id = str(int(time.time() * 1000))
        
        # Fixed welcome message — do not generate from markdown (avoids over-promising
        # capabilities or listing system names the graph agent can't back up).
        assistant_response = (
            "Ready. I have **3 P&IDs loaded** for the Rumaila early power plant:\n\n"
            "| Diagram | System |\n"
            "|---------|--------|\n"
            "| [PID-0006] | DS-1 Scraper Receiver (PP01-361) |\n"
            "| [PID-0007] | DS-3 Scraper Receiver (PP01-361) |\n"
            "| [PID-0008] | Fuel Gas KO Drum (PP01-362-V001) |\n\n"
            "Select a diagram from the sidebar or ask across all three. "
            "I can answer questions about equipment, valves, instruments, line numbers, "
            "operating conditions, isolation procedures, and process flows."
        )

        # Store the welcome as the first assistant turn so follow-up queries have context
        add_to_history(session_id, session_init_prompt, assistant_response)
        print("Session initialized successfully")
        
        return {
            "success": True,
            "message": assistant_response,
            "markdownsLoaded": len(cache.markdowns),
            "sessionId": session_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Session initialization error: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize session: {str(e)}"
        )
