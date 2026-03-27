"""
graph_tools.py — P&ID graph query tools for the LLM agent.

Loads pid.graph.v0.1.1 JSON files and implements five tools:
  get_node       — full node details by tag
  list_nodes     — all nodes of a given type
  find_path      — shortest process path between two tags
  impact_region  — all components reachable from a tag
  search_nodes   — fuzzy tag / service search

Also provides:
  build_tool_definitions() — OpenAI tool_use schema
  execute_tool()           — dispatch tool calls to implementations
  run_graph_agent()        — full tool_use loop (max 5 iterations)
  load_graph()             — load + cache graph JSON by pid_id
"""

import json
import re
from pathlib import Path
from typing import Any
from functools import lru_cache

# ── Path resolution ───────────────────────────────────────────────────────────

def _graphs_dir() -> Path:
    """Locate the graphs directory relative to this file."""
    # backend/utils/ → backend/ → talking-pnids-py/ → data/graphs/
    return Path(__file__).resolve().parents[2] / "data" / "graphs"


@lru_cache(maxsize=10)
def load_graph(pid_id: str) -> dict | None:
    """Load and cache a pid.graph.v0.1.1 JSON by pid_id.
    When pid_id == 'supergraph', merges all three P&ID graphs into one flat
    nodes+edges structure so all existing tools work transparently.
    Returns None if not found.
    """
    if pid_id == "supergraph":
        return _load_merged_supergraph()
    path = _graphs_dir() / f"{pid_id}.graph.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _load_merged_supergraph() -> dict | None:
    """Flatten all individual P&ID graphs into one nodes+edges structure.
    The supergraph.json is a summary file — actual nodes/edges live in the
    individual pid-XXX.graph.json files. We load each of those and merge them.
    Node/edge IDs are prefixed with pid_id: to avoid collisions.
    inter_pid_edges use 'pid-007::node_id' format for cross-P&ID connections.
    """
    sg_path = _graphs_dir() / "supergraph.json"
    if not sg_path.exists():
        return None
    sg = json.loads(sg_path.read_text())
    pids_list = list(sg.get("pid_graphs", {}).keys())

    merged_nodes: list[dict] = []
    merged_edges: list[dict] = []
    # Maps original node id → prefixed id, per pid
    id_maps: dict[str, dict[str, str]] = {}

    for pid in pids_list:
        graph_path = _graphs_dir() / f"{pid}.graph.json"
        if not graph_path.exists():
            continue
        subgraph = json.loads(graph_path.read_text())
        prefix = pid + ":"
        id_map: dict[str, str] = {}
        for n in subgraph.get("nodes", []):
            new_id = prefix + n["id"]
            id_map[n["id"]] = new_id
            merged_nodes.append({**n, "id": new_id, "_pid": pid})
        id_maps[pid] = id_map
        for e in subgraph.get("edges", []):
            merged_edges.append({
                **e,
                "from": id_map.get(e.get("from", ""), prefix + e.get("from", "")),
                "to":   id_map.get(e.get("to",   ""), prefix + e.get("to",   "")),
                "_pid": pid,
            })

    # Add cross-P&ID edges — format: "pid-007::node_id"
    for ie in sg.get("inter_pid_edges", []):
        def _resolve(ref: str) -> str | None:
            if "::" in ref:
                pid, orig_id = ref.split("::", 1)
                return id_maps.get(pid, {}).get(orig_id)
            return None
        src_id = _resolve(ie.get("from", ""))
        dst_id = _resolve(ie.get("to",   ""))
        if src_id and dst_id:
            merged_edges.append({
                "from":     src_id,
                "to":       dst_id,
                "kind":     ie.get("kind", "process"),
                "line_tag": ie.get("props", {}).get("line_tag"),
                "_inter_pid": True,
            })

    return {
        "schema_version": "pid.graph.v0.1.1",
        "metadata": {
            "pid_id":      "supergraph",
            "description": f"Merged supergraph: {', '.join(pids_list)}",
        },
        "nodes": merged_nodes,
        "edges": merged_edges,
        "_supergraph": True,
        "_pids": pids_list,
        "_stats": {"nodes": len(merged_nodes), "edges": len(merged_edges)},
    }


@lru_cache(maxsize=2)
def load_supergraph() -> dict | None:
    path = _graphs_dir() / "supergraph.json"
    return json.loads(path.read_text()) if path.exists() else None


def graph_summary(pid_id: str) -> str:
    """One-line summary for system prompt context."""
    g = load_graph(pid_id)
    if not g:
        return f"No graph available for {pid_id}."
    n = len(g.get("nodes", []))
    e = len(g.get("edges", []))
    if pid_id == "supergraph":
        pids = g.get("_pids", [])
        return f"supergraph ({', '.join(pids)}): {n} nodes, {e} edges across all P&IDs"
    meta = g.get("metadata", {})
    area = meta.get("area") or meta.get("unit") or ""
    return f"{pid_id}: {n} nodes, {e} edges{f', {area}' if area else ''}"


# ── Node helpers ──────────────────────────────────────────────────────────────

def _normalize_tag(tag: str) -> str:
    return re.sub(r"[\s\-]", "", tag.upper()) if tag else ""


def _node_by_tag(nodes: list[dict], tag: str) -> dict | None:
    norm = _normalize_tag(tag)
    for n in nodes:
        if _normalize_tag(n.get("tag", "")) == norm:
            return n
    return None


def _node_by_id(nodes: list[dict], nid: str) -> dict | None:
    for n in nodes:
        if n.get("id") == nid:
            return n
    return None


# ── Tool implementations ──────────────────────────────────────────────────────

def get_node(pid_id: str, tag: str) -> dict:
    g = load_graph(pid_id)
    if not g:
        return {"error": f"Graph not found for {pid_id}"}
    node = _node_by_tag(g["nodes"], tag)
    if not node:
        # Try searching by id
        node = _node_by_id(g["nodes"], tag)
    if not node:
        return {"error": f"No node with tag '{tag}' in {pid_id}"}
    return node


def list_nodes(pid_id: str, node_type: str, subtype_filter: str | None = None) -> list[dict]:
    g = load_graph(pid_id)
    if not g:
        return [{"error": f"Graph not found for {pid_id}"}]
    results = []
    for n in g["nodes"]:
        if n.get("type") != node_type:
            continue
        if subtype_filter and not (n.get("subtype", "") or "").startswith(subtype_filter):
            continue
        # Return a compact summary (not full props) to save tokens
        results.append({
            "id":      n.get("id"),
            "tag":     n.get("tag"),
            "subtype": n.get("subtype"),
            "service": n.get("service"),
            "status":  n.get("status"),
            "props_summary": _props_summary(n.get("props", {})),
        })
    return results


def _props_summary(props: dict) -> dict:
    """Return only the interesting props (non-null, non-empty)."""
    return {k: v for k, v in props.items() if v not in (None, "", [], {})}


def find_path(pid_id: str, from_tag: str, to_tag: str) -> dict:
    """Find shortest path between two tags using BFS on process/signal edges."""
    g = load_graph(pid_id)
    if not g:
        return {"error": f"Graph not found for {pid_id}"}

    nodes = g["nodes"]
    edges = g["edges"]

    from_node = _node_by_tag(nodes, from_tag)
    to_node   = _node_by_tag(nodes, to_tag)

    if not from_node:
        return {"error": f"Tag '{from_tag}' not found"}
    if not to_node:
        return {"error": f"Tag '{to_tag}' not found"}

    # Build adjacency (bidirectional for process edges)
    adj: dict[str, list[str]] = {}
    for e in edges:
        src, dst = e.get("from", ""), e.get("to", "")
        adj.setdefault(src, []).append(dst)
        if e.get("kind") in ("process", "signal"):
            adj.setdefault(dst, []).append(src)  # bidirectional

    # BFS
    start = from_node["id"]
    end   = to_node["id"]
    visited = {start}
    queue = [[start]]

    while queue:
        path = queue.pop(0)
        last = path[-1]
        if last == end:
            # Resolve node ids to tags
            tag_path = []
            for nid in path:
                n = _node_by_id(nodes, nid)
                tag_path.append(n.get("tag") or nid if n else nid)
            # Find edges along path
            edge_details = []
            for i in range(len(path) - 1):
                for e in edges:
                    if (e.get("from") == path[i] and e.get("to") == path[i+1]) or \
                       (e.get("to") == path[i] and e.get("from") == path[i+1]):
                        edge_details.append({
                            "line_tag":   e.get("line_tag"),
                            "pipe_class": e.get("pipe_class"),
                            "diameter":   e.get("diameter"),
                            "kind":       e.get("kind"),
                        })
                        break
            return {"path": tag_path, "hops": len(tag_path) - 1, "edges": edge_details}

        for neighbour in adj.get(last, []):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(path + [neighbour])

    return {"error": f"No path found between '{from_tag}' and '{to_tag}'"}


def impact_region(pid_id: str, tag: str, direction: str = "both", depth: int = 3) -> dict:
    """Return all nodes within `depth` hops from `tag` via process/signal edges."""
    g = load_graph(pid_id)
    if not g:
        return {"error": f"Graph not found for {pid_id}"}

    nodes = g["nodes"]
    edges = g["edges"]

    origin = _node_by_tag(nodes, tag)
    if not origin:
        return {"error": f"Tag '{tag}' not found"}

    # Build directed adjacency
    downstream: dict[str, list[str]] = {}
    upstream:   dict[str, list[str]] = {}
    for e in edges:
        if e.get("kind") not in ("process", "signal", "impulse"):
            continue
        src, dst = e.get("from", ""), e.get("to", "")
        downstream.setdefault(src, []).append(dst)
        upstream.setdefault(dst, []).append(src)

    def bfs(start_id: str, adj: dict, max_depth: int) -> list[dict]:
        visited = {start_id}
        queue = [(start_id, 0)]
        found = []
        while queue:
            nid, d = queue.pop(0)
            if d >= max_depth:
                continue
            for nb in adj.get(nid, []):
                if nb not in visited:
                    visited.add(nb)
                    n = _node_by_id(nodes, nb)
                    if n:
                        found.append({
                            "tag":    n.get("tag") or nb,
                            "type":   n.get("type"),
                            "subtype":n.get("subtype"),
                            "service":n.get("service"),
                            "hops":   d + 1,
                        })
                    queue.append((nb, d + 1))
        return found

    start_id = origin["id"]
    result = {"origin": tag, "depth": depth}

    if direction in ("downstream", "both"):
        result["downstream"] = bfs(start_id, downstream, depth)
    if direction in ("upstream", "both"):
        result["upstream"] = bfs(start_id, upstream, depth)

    return result


def search_nodes(pid_id: str, query: str) -> list[dict]:
    """Fuzzy search nodes by tag prefix or service keyword."""
    g = load_graph(pid_id)
    if not g:
        return [{"error": f"Graph not found for {pid_id}"}]

    q_norm = _normalize_tag(query)
    q_lower = query.lower()
    results = []

    for n in g["nodes"]:
        tag_norm    = _normalize_tag(n.get("tag", ""))
        service     = (n.get("service") or "").lower()
        subtype     = (n.get("subtype") or "").lower()

        if (q_norm and q_norm in tag_norm) or \
           (q_lower and q_lower in service) or \
           (q_lower and q_lower in subtype):
            results.append({
                "id":      n.get("id"),
                "tag":     n.get("tag"),
                "type":    n.get("type"),
                "subtype": n.get("subtype"),
                "service": n.get("service"),
            })

    return results[:20]  # cap at 20 results


# ── OpenAI tool_use definitions ───────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_node",
            "description": (
                "Get full details for a component by tag number. "
                "Returns type, subtype, service, normal/fail position, design pressure/temp, "
                "alarm setpoints, loop_id, and all other properties. "
                "Use this first when a question mentions a specific tag."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "Tag number, e.g. 'HV-0059', '362-V001', 'PSV-001'"
                    }
                },
                "required": ["tag"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_nodes",
            "description": (
                "List all components of a given type in this P&ID. "
                "Returns tag, subtype, service, and key props for each. "
                "Use for questions like 'all isolation valves', 'all instruments with HH alarm', "
                "'all locked-open valves', 'all spectacle blinds'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "node_type": {
                        "type": "string",
                        "enum": ["equipment", "valve", "instrument", "junction", "terminator", "annotation"],
                        "description": "Type of node to list"
                    },
                    "subtype_filter": {
                        "type": "string",
                        "description": "Optional: filter by subtype prefix, e.g. 'valve.gate', 'instrument.pressure', 'valve.spectacle'"
                    }
                },
                "required": ["node_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_path",
            "description": (
                "Find the process/piping path between two components. "
                "Returns the sequence of tags and connection details (line tag, pipe class, diameter). "
                "Use for tracing flow routes between equipment."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "from_tag": {"type": "string", "description": "Starting tag"},
                    "to_tag":   {"type": "string", "description": "Destination tag"}
                },
                "required": ["from_tag", "to_tag"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "impact_region",
            "description": (
                "Find all components connected to a component within N hops. "
                "Use for 'what is affected if X fails/closes', 'upstream effects', "
                "'downstream consequences' questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "Tag of the component of interest"},
                    "direction": {
                        "type": "string",
                        "enum": ["upstream", "downstream", "both"],
                        "description": "Which direction to traverse. Default: both"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "How many hops to traverse. Default: 3",
                        "default": 3
                    }
                },
                "required": ["tag"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_nodes",
            "description": (
                "Search for components by partial tag, service description, or subtype keyword. "
                "Use when you don't know the exact tag. Returns up to 20 matches."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Partial tag, service keyword, or subtype. E.g. 'HV', 'fuel gas', 'spectacle'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def execute_tool(pid_id: str, tool_name: str, tool_input: dict) -> Any:
    """Dispatch a tool call and return the result."""
    if tool_name == "get_node":
        return get_node(pid_id, tool_input["tag"])
    elif tool_name == "list_nodes":
        return list_nodes(pid_id, tool_input["node_type"], tool_input.get("subtype_filter"))
    elif tool_name == "find_path":
        return find_path(pid_id, tool_input["from_tag"], tool_input["to_tag"])
    elif tool_name == "impact_region":
        return impact_region(
            pid_id,
            tool_input["tag"],
            tool_input.get("direction", "both"),
            tool_input.get("depth", 3),
        )
    elif tool_name == "search_nodes":
        return search_nodes(pid_id, tool_input["query"])
    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ── Graph agent loop ──────────────────────────────────────────────────────────

GRAPH_SYSTEM_PROMPT = """You are a senior process engineer answering questions about P&ID diagrams.
You have access to a structured knowledge graph of the P&ID via tools.

Graph available: {graph_summary}

## STRICT SCOPE — GUARDRAIL
You ONLY answer questions about P&IDs, plant equipment, valves, instruments, pipelines, process flows, operations, maintenance, and safety.
If a question is not related to P&IDs or plant operations, respond with EXACTLY:
"This assistant only answers questions about P&ID diagrams and plant operations. Please ask about the equipment, instruments, or processes shown in the loaded diagrams."
Do NOT answer the off-topic question or provide suggestions.

## ACCURACY RULES
- Use tools to look up exact data — do not guess or invent tag numbers.
- If asked about a tag that cannot be found, say so — do not substitute a similar-looking tag.
- Only state facts present in the graph. If data is missing, say "Enough information is not available" then give your engineering reasoning clearly labelled as such.
- Provide only the information asked for. Do not add unrequested detail.

## TOOL USAGE
- For a specific tag: call get_node() first.
- For listing questions (all valves, locked-open valves, all instruments): call list_nodes().
- For "what happens if X fails/closes": call impact_region() upstream or downstream.
- For tracing flow routes: call find_path().
- If you don't know a tag: call search_nodes() first.
- Always cite the exact tag numbers found in the graph.
- Present list/tabular answers as markdown tables.

## READING VALVE POSITIONS
Normal position is stored in props_summary.normal_position for each valve node returned by list_nodes():
- LO = Locked Open (physically locked, cannot be closed during operation)
- LC = Locked Closed (physically locked, cannot be opened during operation)
- ILO = Interlocked Open (held open by interlock/ESD system)
- ILC = Interlocked Closed (held closed by interlock/ESD system)
- NO = Normally Open (open under normal operation, not locked)
- NC = Normally Closed (closed under normal operation, not locked)
- FO = Fail Open (spring-return to open on air/signal failure)
- FC = Fail Closed (spring-return to closed on air/signal failure)
When asked about "locked open" or "locked closed" valves: call list_nodes(node_type='valve'), then filter results where props_summary.normal_position is 'LO' or 'LC' respectively.

## READING SPECTACLE BLINDS
Spectacle blinds appear as valve.spectacle subtype, OR as fitting.spectacle_blind junctions, OR noted in props_summary of adjacent valves (e.g. notes containing 'spectacle blind'). Call list_nodes(node_type='valve', subtype_filter='valve.spectacle') AND list_nodes(node_type='junction') and check for spectacle references.
{rag_section}"""


def run_graph_agent(
    client,          # openai.OpenAI instance
    model: str,
    pid_id: str,
    query: str,
    session_messages: list,  # prior conversation history
    rag_context: str = "",
    max_iterations: int = 5,
) -> tuple[str, dict]:
    """
    Run the tool_use agent loop. Returns (answer_text, sources_dict).
    max_iterations prevents runaway loops — if the model keeps calling tools
    after 5 rounds, we force a final answer.
    """
    rag_section = f"\nEngineering notes available as additional context:\n{rag_context}" if rag_context else ""

    system_content = GRAPH_SYSTEM_PROMPT.format(
        graph_summary=graph_summary(pid_id),
        rag_section=rag_section,
    )

    messages = [{"role": "system", "content": system_content}]
    messages.extend(session_messages)
    messages.append({"role": "user", "content": query})

    tools_called = []

    for iteration in range(max_iterations):
        # On the last iteration, disable tools to force a text answer
        tools = TOOL_DEFINITIONS if iteration < max_iterations - 1 else []
        tool_choice = "auto" if tools else "none"

        # gpt-5.x uses max_completion_tokens; older models use max_tokens
        token_kwarg = (
            {"max_completion_tokens": 2000}
            if model.startswith(("gpt-5", "o1", "o3"))
            else {"max_tokens": 2000}
        )
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools if tools else None,
            tool_choice=tool_choice if tools else None,
            **token_kwarg,
        )

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        if finish_reason != "tool_calls" or not msg.tool_calls:
            # Final text answer
            return msg.content or "", {
                "graph_nodes": list({t["tag"] for t in tools_called if "tag" in t}),
                "tools_called": [t["name"] for t in tools_called],
                "iterations": iteration + 1,
            }

        # Execute all tool calls in this round
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]})

        for tc in msg.tool_calls:
            tool_input = json.loads(tc.function.arguments)
            result = execute_tool(pid_id, tc.function.name, tool_input)
            tools_called.append({"name": tc.function.name, **tool_input})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    # Should not reach here due to last-iteration tool disable
    return "Unable to generate answer.", {"tools_called": []}
