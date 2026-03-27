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
    invoke_with_reasoning,
)
from utils.graph_tools import load_graph, run_graph_agent
from utils import rag_retriever

router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    sessionStarted: bool
    selectedMapping: dict | None = None
    sessionId: str | None = None
    sources: list[str] | None = None  # ["graph", "rag"] — defaults to both if graph available


@router.post("/query")
async def process_query(request: QueryRequest):
    try:
        config  = load_config()
        prompts = load_prompts()

        pid_id     = (request.selectedMapping or {}).get("id")
        session_id = request.sessionId or "default"
        model_name = config.get("openai", {}).get("model", "gpt-4o")
        api_key    = config.get("openai", {}).get("apiKey", "")

        # Determine which sources to use
        sources   = request.sources or ["graph", "rag"]
        use_graph = "graph" in sources
        use_rag   = "rag" in sources

        graph = load_graph(pid_id) if (pid_id and use_graph) else None

        # ── Graph agent path (standard models only) ───────────────────────────
        is_reasoning = model_name.startswith(("o1", "o3", "gpt-5"))

        if graph and not is_reasoning:
            # RAG retrieval (silently skipped if index not built yet)
            rag_context = ""
            rag_sources = []
            if use_rag and rag_retriever.is_available() and api_key:
                chunks = rag_retriever.retrieve(request.query, pid_id, api_key, k=4)
                rag_context = rag_retriever.format_for_prompt(chunks)
                rag_sources = [c["source"] for c in chunks]

            client = get_openai_client(config)

            # Convert LangChain session history to plain dicts
            from utils.langchain_setup import get_message_history
            from langchain_core.messages import HumanMessage, AIMessage
            history = get_message_history(session_id)
            session_msgs = []
            for m in history:
                if isinstance(m, HumanMessage):
                    session_msgs.append({"role": "user",      "content": m.content})
                elif isinstance(m, AIMessage):
                    session_msgs.append({"role": "assistant", "content": m.content})

            answer, tool_sources = run_graph_agent(
                client=client,
                model=model_name,
                pid_id=pid_id,
                query=request.query,
                session_messages=session_msgs,
                rag_context=rag_context,
            )

            add_to_history(session_id, request.query, answer)

            return {
                "answer": answer,
                "sources": {
                    "graph_nodes":  tool_sources.get("graph_nodes", []),
                    "tools_called": tool_sources.get("tools_called", []),
                    "rag_chunks":   rag_sources,
                    "mode":         "graph",
                },
            }

        # ── Reasoning model path (o1, o3, gpt-5.x) ───────────────────────────
        # Inject compact graph JSON + RAG as context — no tool_use
        if graph and is_reasoning:
            import json as _json

            compact_nodes = [
                {k: v for k, v in n.items() if k != "_source_tile" and v not in (None, "", [], {})}
                for n in graph.get("nodes", [])
                if n.get("tag")
            ]
            compact_edges = [
                {k: v for k, v in e.items() if v not in (None, "", [])}
                for e in graph.get("edges", [])
            ]
            graph_context = (
                f"P&ID KNOWLEDGE GRAPH ({pid_id}):\n"
                f"```json\n{_json.dumps({'nodes': compact_nodes[:100], 'edges': compact_edges[:150]}, indent=1)}\n```\n\n"
            )

            rag_context = ""
            if use_rag and rag_retriever.is_available() and api_key:
                chunks = rag_retriever.retrieve(request.query, pid_id, api_key, k=4)
                if chunks:
                    rag_context = "ENGINEERING NOTES:\n" + rag_retriever.format_for_prompt(chunks) + "\n\n"

            system_prompt = get_system_prompt_template(prompts)
            full_query = graph_context + rag_context + f"Question: {request.query}"

            reasoning_effort = config.get("settings", {}).get("reasoningEffort", "medium")
            client = get_openai_client(config)
            input_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": full_query},
            ]
            answer = invoke_with_reasoning(client, model_name, input_messages, reasoning_effort)
            add_to_history(session_id, request.query, answer)
            return {"answer": answer, "sources": {"mode": "reasoning+graph"}}

        # ── Fallback: markdown context (no graph for this P&ID) ───────────────
        system_prompt = get_system_prompt_template(prompts)
        context = ""

        if request.selectedMapping and request.selectedMapping.get("md"):
            markdown = await cache.get_markdown_by_filename(request.selectedMapping["md"])
            context = (
                f"P&ID Markdown Documentation for {request.selectedMapping.get('id', 'unknown')} "
                f"({request.selectedMapping.get('pdf', 'unknown')}):\n\n{markdown}\n\n"
            ) if markdown else f"No markdown found for {request.selectedMapping['md']}.\n\n"
        elif request.sessionStarted:
            await cache.get_all_markdowns()
            if cache.markdowns:
                parts = [
                    f"=== P&ID Documentation File {i}: {fn} ===\n\n{mf.content}\n\n"
                    for i, (fn, mf) in enumerate(cache.markdowns.items(), 1)
                ]
                context = f"P&ID Documentation ({len(cache.markdowns)} systems):\n\n" + "".join(parts)

        # Augment with RAG even in fallback mode if available
        if use_rag and rag_retriever.is_available() and pid_id and api_key:
            chunks = rag_retriever.retrieve(request.query, pid_id, api_key, k=3)
            if chunks:
                context += "\nEngineering Notes:\n" + rag_retriever.format_for_prompt(chunks) + "\n\n"

        full_query = f"{context}Question: {request.query}" if context else request.query

        llm = get_chat_model(config)
        messages = create_messages_with_history(system_prompt, full_query, session_id)
        response = llm.invoke(messages)
        answer = response.content if hasattr(response, "content") else str(response)

        add_to_history(session_id, request.query, answer)

        if not answer:
            raise HTTPException(status_code=500, detail="Model returned empty response.")

        return {"answer": answer, "sources": {"mode": "markdown"}}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Query error:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")
