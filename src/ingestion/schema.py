"""
schema.py — Step 4 of the ingestion pipeline.

Convert unified_extraction.json → pid.graph.v0.1.1 JSON using Claude Sonnet.
The model receives the unified extraction and produces a schema-conformant graph.

Resume: skips if pid_graph.json already exists.
"""

import json
import os
import time
from pathlib import Path

import anthropic

from config import (
    MODEL_SCHEMA, MAX_TOKENS_SCHEMA, STRATEGY_VERSION, calc_cost,
    pid_work_dir, graphs_dir, save_json, load_json,
)

# ─────────────────────────────────────────────────────────────────────────────

SCHEMA_DEF = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "pid.graph.v0.1.1",
  "type": "object",
  "required": ["schema_version", "nodes", "edges"],
  "properties": {
    "schema_version": {"type": "string", "const": "pid.graph.v0.1.1"},
    "metadata": {
      "type": "object",
      "properties": {
        "doc_id": {"type": "string"},
        "rev": {"type": "string"},
        "plant": {"type": "string"},
        "unit": {"type": "string"},
        "area": {"type": "string"},
        "units": {"type": "object"}
      }
    },
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type"],
        "properties": {
          "id": {"type": "string"},
          "type": {"type": "string", "enum": ["equipment","valve","instrument","junction","terminator","nozzle","annotation"]},
          "subtype": {"type": "string"},
          "tag": {"type": "string"},
          "layer": {"type": "string", "enum": ["process","instrument","electrical","mechanical","utility","annotation","other"]},
          "status": {"type": "string", "enum": ["existing","new","removed","future","temporary"]},
          "service": {"type": "string"},
          "loop_id": {"type": "string"},
          "signal_type": {"type": "string"},
          "off_page_ref": {"type": "string"},
          "off_page_doc_id": {"type": "string"},
          "ports": {"type": "array"},
          "props": {"type": "object"}
        },
        "additionalProperties": false
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "from", "to", "kind"],
        "properties": {
          "id": {"type": "string"},
          "from": {"type": "string"},
          "to": {"type": "string"},
          "kind": {"type": "string", "enum": ["process","signal","impulse","association","containment"]},
          "line_tag": {"type": "string"},
          "pipe_class": {"type": "string"},
          "diameter": {"type": "string"},
          "fluid_code": {"type": "string"},
          "flow_dir": {"type": "string", "enum": ["uni","bi"]},
          "layer": {"type": "string"},
          "status": {"type": "string"},
          "props": {"type": "object"}
        },
        "additionalProperties": false
      }
    }
  },
  "additionalProperties": false
}"""

SYSTEM_PROMPT = """You are a process engineering expert and P&ID data modeller.
Convert P&ID extraction data into a structured graph JSON conforming to pid.graph.v0.1.1 schema.
Return ONLY valid JSON — no markdown, no commentary."""

CONVERT_PROMPT_TEMPLATE = """Convert this P&ID extraction data for {pid_id} into a pid.graph.v0.1.1 graph JSON.

SCHEMA:
{schema}

EXTRACTION DATA:
{extraction}

INSTRUCTIONS:
1. Each extracted component → a node. Preserve all tag numbers exactly.
2. Each extracted connection → an edge. Use node IDs (not tag names) as from/to.
3. For components with a tag, use the tag as the node id (cleaned: no spaces).
   For untagged components, use a descriptive id like "junction_r1c1_001".
4. Map component types:
   - valve.* → type: "valve", subtype: "valve.<kind>"
   - instrument.* → type: "instrument", subtype: "instrument.<kind>"
   - equipment.vessel, equipment.pump, etc. → type: "equipment"
   - off-page connectors / terminators → type: "terminator"
   - pipe junctions / tees → type: "junction"
5. Put all extra data (normal_position, fail_position, design_pressure, setpoints, etc.)
   into the node's "props" object.
6. For off_page_refs: create terminator nodes with off_page_ref = the reference label.
7. For spec_breaks: create a junction node at the boundary with props.spec_change = true,
   props.from_spec and props.to_spec set.
8. Set metadata.doc_id = "{pid_id}", metadata.units.pressure = "barg", metadata.units.temperature = "degC", metadata.strategy_version = "{strategy_version}".
9. Keep all tag numbers exactly as extracted — do not normalise or invent tags.
10. Remove duplicate nodes (same tag). Remove cross_tile bridge connections that have no real from/to.

Return valid JSON conforming exactly to pid.graph.v0.1.1. No extra keys at root level."""


def convert_to_graph(pid_id: str, unified: dict, force: bool = False) -> dict:
    """
    Convert unified extraction to pid.graph.v0.1.1 using Claude Sonnet.
    Saves to both work dir and graphs dir.
    """
    work_dir  = pid_work_dir(pid_id)
    out_work  = work_dir / "pid_graph.json"
    out_graph = graphs_dir() / f"{pid_id}.graph.json"

    if out_graph.exists() and not force:
        print(f"[schema] Resume: {pid_id}.graph.json already exists")
        return load_json(out_graph)

    print(f"[schema] Converting {pid_id} extraction → pid.graph.v0.1.1")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    # Trim extraction to fit in context (keep components + connections + spec_breaks)
    extraction_slim = {
        "pid_id": unified.get("pid_id"),
        "components": unified.get("components", []),
        "connections": [
            c for c in unified.get("connections", [])
            if not c.get("cross_tile")  # skip raw edge-bridges, Sonnet will reconstruct
               or (c.get("from", "").count("::") == 0)
        ],
        "off_page_refs": unified.get("off_page_refs", []),
        "spec_breaks": unified.get("spec_breaks", []),
        "notes": unified.get("notes", []),
    }

    extraction_json = json.dumps(extraction_slim, indent=2)

    # If too large, truncate connections to top 500
    if len(extraction_json) > 80_000:
        extraction_slim["connections"] = extraction_slim["connections"][:500]
        extraction_slim["_truncated"] = True
        extraction_json = json.dumps(extraction_slim, indent=2)
        print(f"[schema] WARNING: extraction truncated to fit context window")

    prompt = CONVERT_PROMPT_TEMPLATE.format(
        pid_id=pid_id,
        schema=SCHEMA_DEF,
        extraction=extraction_json,
        strategy_version=STRATEGY_VERSION,
    )

    print(f"[schema] Calling {MODEL_SCHEMA} for schema conversion...")
    t0 = time.time()
    msg = client.messages.create(
        model=MODEL_SCHEMA,
        max_tokens=MAX_TOKENS_SCHEMA,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed = time.time() - t0

    schema_in  = msg.usage.input_tokens
    schema_out = msg.usage.output_tokens
    schema_cost = calc_cost(MODEL_SCHEMA, schema_in, schema_out)
    print(f"[schema] Tokens: {schema_in:,} in / {schema_out:,} out  |  "
          f"${schema_cost:.3f}  |  {elapsed:.0f}s")

    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    graph = json.loads(raw)

    # Validate required fields
    assert graph.get("schema_version") == "pid.graph.v0.1.1", "Wrong schema_version"
    assert "nodes" in graph and "edges" in graph, "Missing nodes or edges"

    node_count = len(graph["nodes"])
    edge_count = len(graph["edges"])
    print(f"[schema] Graph: {node_count} nodes, {edge_count} edges")

    # Save token report
    token_report = {
        "step": "schema",
        "model": MODEL_SCHEMA,
        "api_calls": 1,
        "input_tokens":  schema_in,
        "output_tokens": schema_out,
        "cost_usd": round(schema_cost, 4),
        "elapsed_s": round(elapsed, 1),
    }
    save_json(work_dir / "schema_token_report.json", token_report)

    save_json(out_work,  graph)
    save_json(out_graph, graph)
    print(f"[schema] Saved → {out_graph}")
    return graph


if __name__ == "__main__":
    import sys
    from config import pid_id_from_pdf

    if len(sys.argv) < 2:
        print("Usage: python schema.py <pid_id_or_pdf> [--force]")
        sys.exit(1)

    arg = sys.argv[1]
    pid = pid_id_from_pdf(Path(arg)) if arg.endswith(".pdf") else arg
    force = "--force" in sys.argv

    work_dir = pid_work_dir(pid)
    unified = load_json(work_dir / "unified_extraction.json")
    convert_to_graph(pid, unified, force=force)
