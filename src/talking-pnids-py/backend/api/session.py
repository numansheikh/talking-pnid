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
        
        # Load markdown summaries (cached)
        print("Loading markdown summaries...")
        markdown_summaries = await cache.get_markdown_summaries()
        print(f"Markdown summaries loaded: {len(markdown_summaries)}")
        
        if len(markdown_summaries) == 0:
            raise HTTPException(
                status_code=404,
                detail="No markdown files found. Please add markdown files to the data/mds folder."
            )
        
        # Get system prompt
        system_prompt = get_system_prompt_template(prompts)
        
        # Get session init prompt
        session_init_prompt = get_session_init_prompt(prompts, len(markdown_summaries))
        
        # Prepare context with markdown summaries
        markdowns_context = (
            f"P&ID Documentation Summaries ({len(markdown_summaries)} systems available):\n\n"
            + "\n".join([
                f"File {idx + 1}: {summary.filename}\nPreview: {summary.preview}...\nSize: {summary.size} characters\n"
                for idx, summary in enumerate(markdown_summaries)
            ])
            + "\n\nNote: Full markdown documentation will be provided when answering specific questions about the plant."
        )
        
        # Create session ID
        session_id = str(int(time.time() * 1000))
        
        # Initialize session with context
        print("Sending initialization message...")
        init_message = f"{markdowns_context}\n\n{session_init_prompt}"
        
        model_name = config.get("openai", {}).get("model", "gpt-4")
        reasoning_effort = config.get("settings", {}).get("reasoningEffort", "medium")
        
        # Check if using reasoning model (o1/o3 or gpt-5.2)
        if model_name.startswith("o1") or model_name.startswith("o3") or model_name == "gpt-5.2":
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
            "markdownsLoaded": len(markdown_summaries),
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
