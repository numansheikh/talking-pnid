from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from utils.config import load_config, load_prompts
from utils.markdown_cache import cache
from utils.langchain_setup import (
    get_chat_model,
    get_system_prompt_template,
    create_messages_with_history,
    add_to_history,
    get_openai_client,
    invoke_with_reasoning
)

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    sessionStarted: bool
    selectedMapping: dict | None = None
    sessionId: str | None = None

@router.post("/query")
async def process_query(request: QueryRequest):
    """Process a query with LangChain"""
    try:
        config = load_config()
        prompts = load_prompts()
        
        # Get system prompt
        system_prompt = get_system_prompt_template(prompts)
        
        # Build context based on selected mapping or session state
        context = ""
        
        # If a specific mapping is selected, send that full markdown
        if request.selectedMapping and request.selectedMapping.get("md"):
            markdown = await cache.get_markdown_by_filename(request.selectedMapping["md"])
            if markdown:
                context = f"P&ID Markdown Documentation for {request.selectedMapping.get('id', 'unknown')} ({request.selectedMapping.get('pdf', 'unknown')}):\n\n{markdown}\n\n"
            else:
                context = f"No markdown found for {request.selectedMapping['md']}.\n\n"
        elif request.sessionStarted:
            # Session started but no specific mapping: send all full markdowns
            await cache.get_all_markdowns()  # This populates the cache
            if len(cache.markdowns) > 0:
                markdown_parts = []
                for idx, (filename, markdown_file) in enumerate(cache.markdowns.items(), 1):
                    markdown_parts.append(
                        f"=== P&ID Documentation File {idx}: {filename} ===\n\n{markdown_file.content}\n\n"
                    )
                context = (
                    f"P&ID Documentation ({len(cache.markdowns)} systems available):\n\n"
                    + "".join(markdown_parts)
                )
            else:
                context = "No P&ID markdown documentation available yet.\n\n"
        else:
            # Fallback: send all full markdowns
            await cache.get_all_markdowns()  # This populates the cache
            if len(cache.markdowns) > 0:
                markdown_parts = []
                for idx, (filename, markdown_file) in enumerate(cache.markdowns.items(), 1):
                    markdown_parts.append(
                        f"=== P&ID Documentation File {idx}: {filename} ===\n\n{markdown_file.content}\n\n"
                    )
                context = (
                    f"P&ID Documentation ({len(cache.markdowns)} systems available):\n\n"
                    + "".join(markdown_parts)
                )
            else:
                context = "No P&ID markdown documentation available yet.\n\n"
        
        # Get or create session ID
        session_id = request.sessionId or "default"
        
        # Build the full query with context
        full_query = f"{context}Question: {request.query}" if context else request.query
        
        model_name = config.get("openai", {}).get("model", "gpt-4")
        reasoning_effort = config.get("settings", {}).get("reasoningEffort", "medium")
        
        # Check if using reasoning model (o1/o3 or gpt-5.1/gpt-5.2)
        if model_name.startswith("o1") or model_name.startswith("o3") or model_name.startswith("gpt-5"):
            client = get_openai_client(config)
            # Build messages with history
            history = []
            # Get message history for the session (simplified - just use current query)
            input_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_query}
            ]
            answer = invoke_with_reasoning(client, model_name, input_messages, reasoning_effort)
        else:
            # Use LangChain for other models
            llm = get_chat_model(config)
            # Create messages with system prompt and history
            messages = create_messages_with_history(system_prompt, full_query, session_id)
            # Invoke the model
            response = llm.invoke(messages)
            # Extract content from response
            answer = response.content if hasattr(response, 'content') else str(response)
        
        # Add to history
        add_to_history(session_id, full_query, answer)
        
        if not answer:
            raise HTTPException(
                status_code=500,
                detail="LangChain returned an empty response. Please try again."
            )
        
        return {"answer": answer}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Query processing error: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )
