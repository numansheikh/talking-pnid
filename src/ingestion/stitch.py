"""
stitch.py — Step 3 of the ingestion pipeline.

Merge 6 per-tile extraction JSONs into a single unified_extraction.json.
Responsibilities:
  - Apply pass3 corrections to pass1/pass2 data
  - Deduplicate components in the 15% overlap zones (fuzzy tag match)
  - Resolve EDGE_* references across adjacent tiles
  - Merge connections that span tile boundaries

Resume: skips if unified_extraction.json already exists.
"""

import json
import re
from pathlib import Path

from config import pid_work_dir, save_json, load_json

# ─────────────────────────────────────────────────────────────────────────────

TILE_ADJACENCY = {
    # (row, col) → which edges connect to which neighbour tile
    # key: (r, c), value: { "EDGE_RIGHT": (r, c+1), "EDGE_BOTTOM": (r+1, c), ... }
}

def _build_adjacency(rows: int = 2, cols: int = 3) -> dict:
    adj = {}
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            tile = (r, c)
            adj[tile] = {}
            if c < cols:
                adj[tile]["EDGE_RIGHT"]  = (r, c + 1)
            if c > 1:
                adj[tile]["EDGE_LEFT"]   = (r, c - 1)
            if r < rows:
                adj[tile]["EDGE_BOTTOM"] = (r + 1, c)
            if r > 1:
                adj[tile]["EDGE_TOP"]    = (r - 1, c)
    return adj


def _tile_key(tile_name: str) -> tuple[int, int]:
    """'tile_r1c2' → (1, 2)"""
    m = re.search(r"r(\d+)c(\d+)", tile_name)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def _apply_corrections(tile_result: dict) -> dict:
    """Apply pass3 corrections to pass1 components in-place, return merged view."""
    p1 = tile_result.get("pass1", {})
    p3 = tile_result.get("pass3", {})

    components = {c["id"]: c for c in p1.get("components", [])}
    connections = {c["id"]: c for c in p1.get("connections", [])}

    # Apply corrections from pass3
    for corr in p3.get("corrections", []):
        cid = corr.get("component_id")
        field = corr.get("field")
        new_val = corr.get("now")
        if cid in components and field:
            if "." in field:
                # nested field like props.normal_position
                parts = field.split(".", 1)
                if parts[0] in components[cid]:
                    components[cid][parts[0]][parts[1]] = new_val
            else:
                components[cid][field] = new_val

    # Add pass3 additions
    p3_adds = p3.get("additions", {})
    for c in p3_adds.get("components", []):
        cid = c.get("id", f"p3_{len(components)}")
        if cid not in components:
            components[cid] = c

    # Merge pass2 additions
    p2 = tile_result.get("pass2", {})
    p2_adds = p2.get("additions", {})
    for c in p2_adds.get("components", []):
        cid = c.get("id", f"p2_{len(components)}")
        if cid not in components:
            components[cid] = c

    # Flatten setpoints into instrument props
    for sp in p2_adds.get("setpoints", []):
        tag = sp.get("tag")
        for cid, comp in components.items():
            if comp.get("tag") == tag:
                props = comp.setdefault("props", {})
                setpoints = props.setdefault("setpoints", [])
                setpoints.append({sp["level"]: sp.get("value")})

    # Flatten locked positions into valve props
    for lp in p2_adds.get("locked_positions", []):
        tag = lp.get("tag")
        for cid, comp in components.items():
            if comp.get("tag") == tag:
                props = comp.setdefault("props", {})
                props["normal_position"] = lp.get("position")
                if lp.get("interlock_ref"):
                    props["interlock_ref"] = lp["interlock_ref"]

    # Flatten design conditions into equipment props
    for dc in p2_adds.get("design_conditions", []):
        tag = dc.get("equipment_tag")
        for cid, comp in components.items():
            if comp.get("tag") == tag:
                props = comp.setdefault("props", {})
                for k in ("design_pressure", "design_temp", "op_pressure", "op_temp"):
                    if dc.get(k):
                        props[k] = dc[k]

    # Merge all connections
    for c in p2_adds.get("connections", []):
        cid = c.get("id", f"p2c_{len(connections)}")
        if cid not in connections:
            connections[cid] = c
    for c in p3_adds.get("connections", []):
        cid = c.get("id", f"p3c_{len(connections)}")
        if cid not in connections:
            connections[cid] = c

    tile_name = tile_result.get("tile", "unknown")
    return {
        "tile": tile_name,
        "components": list(components.values()),
        "connections": list(connections.values()),
        "off_page_refs": p1.get("off_page_refs", []),
        "spec_breaks": p1.get("spec_breaks", []) + p2_adds.get("spec_breaks", []),
        "notes": p2_adds.get("notes", []),
        "quality_flags": p3.get("quality_flags", []),
    }


def _normalize_tag(tag: str) -> str:
    """Normalize tag for duplicate detection: uppercase, strip spaces/dashes."""
    return re.sub(r"[\s\-]", "", tag.upper()) if tag else ""


def _dedup_components(all_comps: list[dict]) -> list[dict]:
    """
    Deduplicate components from overlapping tiles.
    Strategy: if two components share the same normalized tag, keep the one with more data.
    Components without tags are kept as-is.
    """
    seen_tags: dict[str, dict] = {}
    untagged = []

    for comp in all_comps:
        tag = _normalize_tag(comp.get("tag", ""))
        if not tag:
            untagged.append(comp)
            continue
        if tag not in seen_tags:
            seen_tags[tag] = comp
        else:
            # Keep whichever has more props
            existing = seen_tags[tag]
            existing_props = len(json.dumps(existing.get("props", {})))
            new_props = len(json.dumps(comp.get("props", {})))
            if new_props > existing_props:
                seen_tags[tag] = comp

    return list(seen_tags.values()) + untagged


def _resolve_edge_connections(
    tile_data: dict[tuple, dict],
    adjacency: dict,
) -> list[dict]:
    """
    Find EDGE_* endpoints and create cross-tile connections.
    For each EDGE_RIGHT in tile (r,c), look for EDGE_LEFT in tile (r, c+1)
    and connect the components at those edges.
    """
    cross_connections = []

    for tile_key, data in tile_data.items():
        adj = adjacency.get(tile_key, {})
        for conn in data.get("connections", []):
            from_id = conn.get("from", "")
            to_id   = conn.get("to", "")

            for edge_dir, neighbour_key in adj.items():
                opposite = {
                    "EDGE_RIGHT": "EDGE_LEFT",
                    "EDGE_LEFT":  "EDGE_RIGHT",
                    "EDGE_BOTTOM": "EDGE_TOP",
                    "EDGE_TOP":    "EDGE_BOTTOM",
                }[edge_dir]

                if from_id == edge_dir or to_id == edge_dir:
                    # This connection exits this tile at edge_dir
                    # The component on the other side is at the neighbour tile's opposite edge
                    neighbour_data = tile_data.get(neighbour_key)
                    if not neighbour_data:
                        continue
                    # Find entering connections at the opposite edge in neighbour
                    for nconn in neighbour_data.get("connections", []):
                        nfrom = nconn.get("from", "")
                        nto   = nconn.get("to", "")
                        if nfrom == opposite or nto == opposite:
                            # Create a bridge connection
                            bridge_id = f"bridge_{tile_key[0]}{tile_key[1]}_{neighbour_key[0]}{neighbour_key[1]}_{edge_dir}"
                            actual_from = to_id if from_id == edge_dir else from_id
                            actual_to   = nfrom if nfrom != opposite else nto
                            if actual_from not in ("EDGE_LEFT", "EDGE_RIGHT", "EDGE_TOP", "EDGE_BOTTOM") and \
                               actual_to   not in ("EDGE_LEFT", "EDGE_RIGHT", "EDGE_TOP", "EDGE_BOTTOM"):
                                cross_connections.append({
                                    "id": bridge_id,
                                    "from": f"{data['tile']}::{actual_from}",
                                    "to":   f"{neighbour_data['tile']}::{actual_to}",
                                    "kind": conn.get("kind", "process"),
                                    "line_tag":   conn.get("line_tag") or nconn.get("line_tag"),
                                    "pipe_class": conn.get("pipe_class") or nconn.get("pipe_class"),
                                    "diameter":   conn.get("diameter") or nconn.get("diameter"),
                                    "cross_tile": True,
                                })

    return cross_connections


def stitch(pid_id: str, tile_extractions: list[dict], force: bool = False) -> dict:
    """
    Stitch tile extractions into a unified extraction document.
    Returns the unified extraction dict and saves it to disk.
    """
    work_dir = pid_work_dir(pid_id)
    out_path = work_dir / "unified_extraction.json"

    if out_path.exists() and not force:
        print(f"[stitch] Resume: unified_extraction.json already exists for {pid_id}")
        return load_json(out_path)

    print(f"[stitch] Stitching {len(tile_extractions)} tiles for {pid_id}")

    adjacency = _build_adjacency()

    # Apply corrections and flatten each tile
    tile_data: dict[tuple, dict] = {}
    for tile_result in tile_extractions:
        merged = _apply_corrections(tile_result)
        key = _tile_key(merged["tile"])
        tile_data[key] = merged
        print(f"[stitch]   Tile {merged['tile']}: "
              f"{len(merged['components'])} components, "
              f"{len(merged['connections'])} connections")

    # Collect all components and deduplicate
    all_components = []
    for data in tile_data.values():
        # Prefix tile name to IDs to avoid collisions
        tile_prefix = data["tile"]
        for comp in data["components"]:
            comp = dict(comp)
            if not comp.get("id", "").startswith(tile_prefix):
                comp["id"] = f"{tile_prefix}__{comp['id']}"
            comp["_source_tile"] = tile_prefix
            all_components.append(comp)

    deduped = _dedup_components(all_components)
    print(f"[stitch] Components: {len(all_components)} raw → {len(deduped)} after dedup")

    # Collect all intra-tile connections
    all_connections = []
    for data in tile_data.values():
        tile_prefix = data["tile"]
        for conn in data["connections"]:
            conn = dict(conn)
            if not conn.get("id", "").startswith(tile_prefix):
                conn["id"] = f"{tile_prefix}__{conn['id']}"
            conn["_source_tile"] = tile_prefix
            all_connections.append(conn)

    # Resolve cross-tile connections
    cross = _resolve_edge_connections(tile_data, adjacency)
    all_connections.extend(cross)
    print(f"[stitch] Connections: {len(all_connections) - len(cross)} intra + {len(cross)} cross-tile")

    # Collect off-page refs, spec breaks, notes, quality flags
    all_off_page_refs = []
    all_spec_breaks   = []
    all_notes         = []
    all_quality_flags = []
    for data in tile_data.values():
        all_off_page_refs.extend(data.get("off_page_refs", []))
        all_spec_breaks.extend(data.get("spec_breaks", []))
        all_notes.extend(data.get("notes", []))
        all_quality_flags.extend(data.get("quality_flags", []))

    unified = {
        "pid_id": pid_id,
        "tile_count": len(tile_data),
        "components": deduped,
        "connections": all_connections,
        "off_page_refs": all_off_page_refs,
        "spec_breaks": all_spec_breaks,
        "notes": all_notes,
        "quality_flags": all_quality_flags,
        "stats": {
            "components_raw": len(all_components),
            "components_deduped": len(deduped),
            "connections_intra": len(all_connections) - len(cross),
            "connections_cross": len(cross),
        },
    }

    save_json(out_path, unified)
    print(f"[stitch] Done: unified_extraction.json → {out_path}")
    return unified


if __name__ == "__main__":
    import sys
    from config import pid_id_from_pdf

    if len(sys.argv) < 2:
        print("Usage: python stitch.py <pid_id_or_pdf> [--force]")
        sys.exit(1)

    arg = sys.argv[1]
    if arg.endswith(".pdf"):
        pid = pid_id_from_pdf(Path(arg))
    else:
        pid = arg

    force = "--force" in sys.argv
    work_dir = pid_work_dir(pid)
    extractions = load_json(work_dir / "all_tile_extractions.json")
    stitch(pid, extractions, force=force)
