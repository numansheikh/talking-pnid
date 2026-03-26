"""
validate.py — Step 5 of the ingestion pipeline.

Cross-validate the pid.graph.v0.1.1 JSON against:
  1. OCR tag list (catch hallucinated or missed tags)
  2. Completeness rules (every vessel/PSV/valve/loop has required attributes)

Outputs a confidence report JSON.
Resume: skips if validation_report.json already exists.
"""

import json
import re
from pathlib import Path

from config import pid_work_dir, save_json, load_json, load_ocr_tags

# ─────────────────────────────────────────────────────────────────────────────

def _normalize_tag(tag: str) -> str:
    return re.sub(r"[\s\-_]", "", tag.upper()) if tag else ""


def validate_graph(pid_id: str, graph: dict, force: bool = False) -> dict:
    """
    Validate a pid.graph.v0.1.1 graph document.
    Returns a confidence report dict and saves it to disk.
    """
    work_dir   = pid_work_dir(pid_id)
    report_path = work_dir / "validation_report.json"

    if report_path.exists() and not force:
        print(f"[validate] Resume: validation_report.json already exists for {pid_id}")
        return load_json(report_path)

    print(f"[validate] Validating {pid_id}")

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    ocr_tags = load_ocr_tags(pid_id)

    issues = []
    warnings = []
    confirmed_tags = []

    # ── 1. OCR cross-reference ────────────────────────────────────────────────
    graph_tags = {_normalize_tag(n["tag"]): n for n in nodes if n.get("tag")}
    ocr_norm   = {_normalize_tag(t): t for t in ocr_tags if t.strip()}

    if ocr_tags:
        # Tags in OCR but not in graph → likely missed
        missed_in_graph = [
            ocr_norm[t] for t in ocr_norm if t not in graph_tags
        ]
        # Tags in graph but not in OCR → possibly hallucinated
        extra_in_graph = [
            graph_tags[t]["tag"] for t in graph_tags if t not in ocr_norm
        ]
        confirmed = [graph_tags[t]["tag"] for t in graph_tags if t in ocr_norm]

        confirmed_tags = confirmed
        if missed_in_graph:
            issues.append({
                "rule": "ocr_coverage",
                "severity": "high",
                "message": f"{len(missed_in_graph)} OCR tags not found in graph",
                "items": missed_in_graph[:50],
            })
        if extra_in_graph:
            warnings.append({
                "rule": "ocr_hallucination_check",
                "severity": "medium",
                "message": f"{len(extra_in_graph)} graph tags not in OCR list (may be hallucinated or small-bore)",
                "items": extra_in_graph[:50],
            })
        print(f"[validate] OCR: {len(confirmed)} confirmed, {len(missed_in_graph)} missed, {len(extra_in_graph)} unconfirmed")
    else:
        warnings.append({"rule": "ocr_unavailable", "severity": "low",
                         "message": "No OCR tag file found for this P&ID"})

    # ── 2. Completeness rules ─────────────────────────────────────────────────

    # 2a. Every vessel must have design/op pressure + temp
    vessels = [n for n in nodes if n.get("type") == "equipment" and
               "vessel" in (n.get("subtype") or "").lower()]
    for v in vessels:
        props = v.get("props", {})
        missing = [f for f in ("design_pressure", "design_temp", "op_pressure", "op_temp")
                   if not props.get(f)]
        if missing:
            issues.append({
                "rule": "vessel_conditions",
                "severity": "high",
                "message": f"Vessel {v.get('tag','?')} missing: {', '.join(missing)}",
                "node_id": v["id"],
            })

    # 2b. Every PSV must have set_pressure and size_code
    psvs = [n for n in nodes if "PSV" in (n.get("tag") or "").upper() or
            "psv" in (n.get("subtype") or "").lower() or
            "relief" in (n.get("subtype") or "").lower()]
    for psv in psvs:
        props = psv.get("props", {})
        missing = [f for f in ("set_pressure", "size_code") if not props.get(f)]
        if missing:
            issues.append({
                "rule": "psv_attributes",
                "severity": "high",
                "message": f"PSV {psv.get('tag','?')} missing: {', '.join(missing)}",
                "node_id": psv["id"],
            })

    # 2c. Every valve must have normal_position (LO/LC/NO/NC/FO/FC/FL)
    valves = [n for n in nodes if n.get("type") == "valve"]
    valves_missing_pos = []
    for v in valves:
        props = v.get("props", {})
        if not props.get("normal_position") and not props.get("fail_position"):
            valves_missing_pos.append(v.get("tag") or v["id"])
    if valves_missing_pos:
        warnings.append({
            "rule": "valve_normal_position",
            "severity": "medium",
            "message": f"{len(valves_missing_pos)} valves missing normal/fail position",
            "items": valves_missing_pos[:30],
        })

    # 2d. Every spec break should have from_spec and to_spec
    spec_break_nodes = [n for n in nodes if
                        (n.get("props") or {}).get("spec_change")]
    for sb in spec_break_nodes:
        props = sb.get("props", {})
        if not props.get("from_spec") or not props.get("to_spec"):
            warnings.append({
                "rule": "spec_break_attributes",
                "severity": "medium",
                "message": f"Spec break node {sb['id']} missing from_spec or to_spec",
                "node_id": sb["id"],
            })

    # 2e. Off-page terminators should have off_page_ref set
    terminators = [n for n in nodes if n.get("type") == "terminator"]
    term_missing_ref = [t["id"] for t in terminators if not t.get("off_page_ref")]
    if term_missing_ref:
        warnings.append({
            "rule": "terminator_ref",
            "severity": "medium",
            "message": f"{len(term_missing_ref)} terminators missing off_page_ref",
            "items": term_missing_ref,
        })

    # 2f. Control loops: check for transmitter + controller + output valve triad
    # Infer loop from loop_id on instrument nodes
    loop_map: dict[str, list] = {}
    for n in nodes:
        lid = n.get("loop_id")
        if lid:
            loop_map.setdefault(lid, []).append(n)

    for loop_id, members in loop_map.items():
        types_present = {n.get("subtype", "").split(".")[-1] for n in members}
        # Very rough check
        has_transmitter = any("transmitter" in t or t.startswith("T") for t in types_present)
        has_controller  = any("controller" in t or t.startswith("C") for t in types_present)
        has_valve       = any(n.get("type") == "valve" for n in members)
        if not (has_transmitter and has_controller and has_valve):
            warnings.append({
                "rule": "control_loop_completeness",
                "severity": "low",
                "message": f"Loop {loop_id} may be incomplete (needs transmitter + controller + valve)",
                "members": [n.get("tag") or n["id"] for n in members],
            })

    # ── 3. Summary ────────────────────────────────────────────────────────────
    high_issues   = [i for i in issues if i.get("severity") == "high"]
    medium_issues = [i for i in issues if i.get("severity") == "medium"] + \
                    [w for w in warnings if w.get("severity") == "medium"]

    total_nodes = len(nodes)
    total_edges = len(edges)
    total_tags  = len(graph_tags)
    ocr_coverage = round(len(confirmed_tags) / max(len(ocr_norm), 1) * 100, 1) if ocr_tags else None

    # Confidence score: start at 100, deduct for issues
    confidence = 100.0
    confidence -= len(high_issues) * 5
    confidence -= len(medium_issues) * 2
    confidence = max(0.0, min(100.0, confidence))

    report = {
        "pid_id": pid_id,
        "schema_version": "pid.graph.v0.1.1",
        "stats": {
            "nodes": total_nodes,
            "edges": total_edges,
            "tagged_nodes": total_tags,
            "vessels": len(vessels),
            "valves": len(valves),
            "psvs": len(psvs),
            "terminators": len(terminators),
            "control_loops": len(loop_map),
        },
        "ocr": {
            "tag_count": len(ocr_tags),
            "confirmed": len(confirmed_tags),
            "coverage_pct": ocr_coverage,
        },
        "confidence_score": confidence,
        "issues": issues,
        "warnings": warnings,
        "summary": (
            f"Confidence: {confidence:.0f}%. "
            f"{total_nodes} nodes, {total_edges} edges. "
            f"OCR coverage: {ocr_coverage}%. "
            f"{len(high_issues)} high-severity issues."
        ),
    }

    save_json(report_path, report)
    print(f"[validate] {report['summary']}")
    print(f"[validate] Report → {report_path}")
    return report


if __name__ == "__main__":
    import sys
    from config import pid_id_from_pdf, graphs_dir

    if len(sys.argv) < 2:
        print("Usage: python validate.py <pid_id_or_pdf> [--force]")
        sys.exit(1)

    arg = sys.argv[1]
    pid = pid_id_from_pdf(Path(arg)) if arg.endswith(".pdf") else arg
    force = "--force" in sys.argv

    graph_path = graphs_dir() / f"{pid}.graph.json"
    graph = load_json(graph_path)
    validate_graph(pid, graph, force=force)
