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
            # Session started but no specific mapping: send summaries
            summaries = await cache.get_markdown_summaries()
            if len(summaries) > 0:
                context = (
                    f"P&ID Documentation Summaries ({len(summaries)} systems available):\n\n"
                    + "\n".join([
                        f"File {idx + 1}: {summary.filename}\nPreview: {summary.preview}...\nSize: {summary.size} characters\n"
                        for idx, summary in enumerate(summaries)
                    ])
                    + "\n\nNote: Summaries are provided to reduce token usage. If you need details about a specific equipment, instrument, or process from a particular file, indicate which one and the full markdown documentation can be retrieved.\n\n"
                )
            else:
                context = "No P&ID markdown documentation available yet.\n\n"
        else:
            # Fallback: send summaries
            summaries = await cache.get_markdown_summaries()
            if len(summaries) > 0:
                context = (
                    "P&ID Documentation Summaries:\n\n"
                    + "\n".join([
                        f"File {idx + 1}: {summary.filename}\nPreview: {summary.preview}...\n"
                        for idx, summary in enumerate(summaries)
                    ])
                    + "\n\nNote: Summaries are provided. Select a specific file to get full markdown documentation.\n\n"
                )
            else:
                context = "No P&ID markdown documentation available yet.\n\n"
        
        # Get or create session ID
        session_id = request.sessionId or "default"
        
        # Build the full query with context
        full_query = f"{context}Question: {request.query}" if context else request.query
        
        model_name = config.get("openai", {}).get("model", "gpt-4")
        reasoning_effort = config.get("settings", {}).get("reasoningEffort", "medium")
        
        # Check if using reasoning model (o1/o3 or gpt-5.2)
        if model_name.startswith("o1") or model_name.startswith("o3") or model_name == "gpt-5.2":
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
