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
        
        # Initialize session with context
        print("Sending initialization message...")
        init_message = f"{markdowns_context}\n\n{session_init_prompt}"
        
        model_name = config.get("openai", {}).get("model", "gpt-4")
        reasoning_effort = config.get("settings", {}).get("reasoningEffort", "medium")
        
        # Check if using reasoning model (o1/o3 or gpt-5.1/gpt-5.2)
        if model_name.startswith("o1") or model_name.startswith("o3") or model_name.startswith("gpt-5"):
            print(f"Using {model_name} with reasoning API...")
            client = get_openai_client(config)
            # Create messages in the format expected by the API
            input_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": init_message}
            ]
            assistant_response_text = invoke_with_reasoning(client, model_name, input_messages, reasoning_effort)
        else:
            # Use LangChain for other models
            print("Initializing LangChain model...")
            llm = get_chat_model(config)
            # Create messages with system prompt
            messages = create_messages_with_history(system_prompt, init_message, session_id)
            # Invoke the model
            response = llm.invoke(messages)
            # Extract content from response
            assistant_response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Add to history
        add_to_history(session_id, init_message, assistant_response_text)
        
        assistant_response = assistant_response_text or "Session initialized. Ready to assist."
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
