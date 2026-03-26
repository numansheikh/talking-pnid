"""
supergraph.py — Step 6 of the ingestion pipeline.

Wire 3 per-P&ID graphs into a super graph by resolving off_page_ref connections.
Two terminator nodes with the same off_page_ref (normalised) on different P&IDs
are connected by an inter-P&ID edge.

Resume: skips if supergraph.json already exists.
"""

import json
import os
import re
from pathlib import Path

import anthropic

from config import (
    MODEL_SCHEMA, MAX_TOKENS_SCHEMA,
    POC_PIDS, graphs_dir, save_json, load_json,
)

# ─────────────────────────────────────────────────────────────────────────────

def _norm_ref(ref: str) -> str:
    """Normalise off_page_ref for matching: uppercase, strip spaces/special."""
    return re.sub(r"[\s\-_./]", "", ref.upper()) if ref else ""


def build_supergraph(force: bool = False) -> dict:
    """
    Load all available P&ID graphs and wire them into a super graph.
    Returns the supergraph dict and saves it to graphs_dir/supergraph.json.
    """
    out_path = graphs_dir() / "supergraph.json"

    if out_path.exists() and not force:
        print("[supergraph] Resume: supergraph.json already exists")
        return load_json(out_path)

    # Load all available graphs
    gdir = graphs_dir()
    graphs: dict[str, dict] = {}
    for pid_id in POC_PIDS:
        gpath = gdir / f"{pid_id}.graph.json"
        if gpath.exists():
            graphs[pid_id] = load_json(gpath)
            n = len(graphs[pid_id].get("nodes", []))
            e = len(graphs[pid_id].get("edges", []))
            print(f"[supergraph] Loaded {pid_id}: {n} nodes, {e} edges")
        else:
            print(f"[supergraph] WARNING: {pid_id}.graph.json not found, skipping")

    if len(graphs) < 2:
        print("[supergraph] Need at least 2 P&ID graphs to build supergraph")
        return {}

    # Build index of terminator nodes by normalised off_page_ref
    # { norm_ref: [(pid_id, node)] }
    ref_index: dict[str, list[tuple[str, dict]]] = {}
    for pid_id, graph in graphs.items():
        for node in graph.get("nodes", []):
            if node.get("type") == "terminator" and node.get("off_page_ref"):
                norm = _norm_ref(node["off_page_ref"])
                ref_index.setdefault(norm, []).append((pid_id, node))

    # Find matches across different P&IDs
    inter_pid_edges = []
    matched_refs = set()
    edge_count = 0

    for norm_ref, occurrences in ref_index.items():
        # Unique P&IDs that have this ref
        pids_with_ref = list({pid for pid, _ in occurrences})
        if len(pids_with_ref) < 2:
            continue  # same ref on only one P&ID — can't wire

        matched_refs.add(norm_ref)
        # Create an edge between each pair of P&IDs sharing this ref
        for i in range(len(occurrences)):
            for j in range(i + 1, len(occurrences)):
                pid_a, node_a = occurrences[i]
                pid_b, node_b = occurrences[j]
                if pid_a == pid_b:
                    continue
                edge_id = f"inter_{pid_a}_{pid_b}_{norm_ref}_{edge_count}"
                inter_pid_edges.append({
                    "id": edge_id,
                    "from": f"{pid_a}::{node_a['id']}",
                    "to":   f"{pid_b}::{node_b['id']}",
                    "kind": "process",
                    "props": {
                        "off_page_ref": node_a.get("off_page_ref"),
                        "cross_pid": True,
                    },
                })
                edge_count += 1

    print(f"[supergraph] Matched {len(matched_refs)} off-page refs → {edge_count} inter-P&ID edges")

    # Use Claude Sonnet to enrich the supergraph with a connectivity summary
    enriched_connections = _enrich_with_llm(graphs, inter_pid_edges)

    # Build supergraph document
    supergraph = {
        "schema_version": "pid.supergraph.v0.1.0",
        "metadata": {
            "pid_ids": list(graphs.keys()),
            "description": "Cross-P&ID super graph for POC P&IDs 006, 007, 008",
        },
        "pid_graphs": {
            pid_id: {
                "node_count": len(g.get("nodes", [])),
                "edge_count": len(g.get("edges", [])),
                "metadata": g.get("metadata", {}),
            }
            for pid_id, g in graphs.items()
        },
        "inter_pid_edges": inter_pid_edges,
        "connectivity_summary": enriched_connections,
    }

    save_json(out_path, supergraph)
    print(f"[supergraph] Saved supergraph.json → {out_path}")
    print(f"[supergraph] {len(graphs)} P&IDs, {edge_count} inter-P&ID connections")
    return supergraph


def _enrich_with_llm(graphs: dict, inter_edges: list) -> dict:
    """
    Use Claude Sonnet to summarise the connectivity between P&IDs.
    Returns a connectivity summary dict.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[supergraph] WARNING: ANTHROPIC_API_KEY not set, skipping LLM enrichment")
        return {}

    client = anthropic.Anthropic(api_key=api_key)

    # Build a concise overview of what each P&ID contains
    pid_summaries = {}
    for pid_id, graph in graphs.items():
        nodes = graph.get("nodes", [])
        equipment = [n.get("tag") for n in nodes if n.get("type") == "equipment" and n.get("tag")]
        terminators = [
            {"tag": n.get("tag"), "ref": n.get("off_page_ref")}
            for n in nodes if n.get("type") == "terminator"
        ]
        pid_summaries[pid_id] = {
            "equipment": equipment[:20],
            "terminator_count": len(terminators),
            "terminators": terminators[:20],
        }

    edge_summary = [
        {"from_pid": e["from"].split("::")[0], "to_pid": e["to"].split("::")[0],
         "ref": e.get("props", {}).get("off_page_ref")}
        for e in inter_edges[:30]
    ]

    prompt = f"""You are a process engineer reviewing P&ID connectivity.

Given these P&ID summaries and their inter-P&ID connections, write a brief JSON connectivity summary:

P&ID SUMMARIES:
{json.dumps(pid_summaries, indent=2)}

INTER-P&ID CONNECTIONS:
{json.dumps(edge_summary, indent=2)}

Return JSON:
{{
  "process_flow_description": "<2-3 sentence description of how these P&IDs connect>",
  "key_connections": [
    {{"from_pid": "...", "to_pid": "...", "description": "..."}}
  ],
  "isolated_terminators": ["<any off-page refs with no match across P&IDs>"]
}}"""

    try:
        msg = client.messages.create(
            model=MODEL_SCHEMA,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[supergraph] LLM enrichment failed: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    build_supergraph(force=force)
