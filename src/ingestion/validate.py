"""
validate.py — Step 5 of the ingestion pipeline.

Cross-validates the pid.graph.v0.1.1 JSON against three sources:
  1. PID Data.xlsx  — structured ground truth (equipment specs, instrument tags,
                       control loops, valve sizes) for the V001 KO drum system
  2. OCR tag list   — catch hallucinated or missed tags
  3. Completeness rules — every vessel/PSV/valve/loop has required attributes

Outputs a confidence report JSON.
Resume: skips if validation_report.json already exists.
"""

import json
import re
from pathlib import Path

from config import pid_work_dir, save_json, load_json, load_ocr_tags, PID_DATA_XLSX, STRATEGY_VERSION

# ─────────────────────────────────────────────────────────────────────────────

def _normalize_tag(tag: str) -> str:
    """Strip prefix variants: PP01-362-LIT001 → LIT001, also keep full form."""
    return re.sub(r"[\s\-_]", "", (tag or "").upper())


def _tag_matches(graph_tag: str, ref_tag: str) -> bool:
    """
    Fuzzy tag match: handles prefix variants.
    PP01-362-LIT001 matches LIT001, LIT-001, PP01-362-LIT-001, etc.
    """
    if not graph_tag or not ref_tag:
        return False
    g = _normalize_tag(graph_tag)
    r = _normalize_tag(ref_tag)
    # Exact match
    if g == r:
        return True
    # One ends with the other (prefix stripping)
    return g.endswith(r) or r.endswith(g)


def _find_node(nodes: list, ref_tag: str) -> dict | None:
    """Find a node in the graph that matches ref_tag (with prefix flexibility)."""
    for n in nodes:
        if _tag_matches(n.get("tag", ""), ref_tag):
            return n
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Section 1: Excel ground truth validation
# ─────────────────────────────────────────────────────────────────────────────

def _load_excel_ground_truth() -> dict | None:
    """
    Load PID Data.xlsx into a structured dict.
    Returns None if file not found or openpyxl not installed.

    Schema mirrors the Excel sheets:
      equipment, lines, field_gauges, field_tx_dcs, field_tx_esd,
      dcs_controllers, esd_controllers, control_valves, esd_valves, manual_valves
    """
    if not PID_DATA_XLSX.exists():
        return None
    try:
        import openpyxl
    except ImportError:
        print("[validate] WARNING: openpyxl not installed, skipping Excel validation")
        return None

    wb = openpyxl.load_workbook(str(PID_DATA_XLSX))

    def sheet_to_dicts(sheet_name: str) -> list[dict]:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            return []
        headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(rows[0])]
        result = []
        for row in rows[1:]:
            if any(v is not None for v in row):
                result.append({headers[i]: row[i] for i in range(len(headers))})
        return result

    return {
        "equipment":       sheet_to_dicts("Eqpt"),
        "lines":           sheet_to_dicts("Line"),
        "field_gauges":    sheet_to_dicts("Field_Gauges"),
        "field_tx_dcs":    sheet_to_dicts("Field_TX_DCS"),
        "field_tx_esd":    sheet_to_dicts("Field_TX_ESD"),
        "dcs_controllers": sheet_to_dicts("DCS_CNTRLR"),
        "esd_controllers": sheet_to_dicts("ESD_CNTRLR"),
        "control_valves":  sheet_to_dicts("Control_Valve"),
        "esd_valves":      sheet_to_dicts("ESD_Valve"),
        "manual_valves":   sheet_to_dicts("Manual_Valve"),
    }


def _validate_excel(nodes: list, edges: list, gt: dict) -> tuple[list, list, dict]:
    """
    Compare graph against Excel ground truth.
    Returns (issues, warnings, excel_summary).
    """
    issues = []
    warnings = []
    found = {}
    missing = {}

    # ── Equipment specs ───────────────────────────────────────────────────────
    for eqpt in gt.get("equipment", []):
        tag = eqpt.get("Equipment_Tag", "")
        node = _find_node(nodes, tag)
        if not node:
            issues.append({
                "rule": "excel_equipment_missing",
                "severity": "high",
                "message": f"Equipment {tag} ({eqpt.get('Eqpt_Service')}) not found in graph",
                "expected_tag": tag,
            })
            missing[tag] = "equipment"
            continue

        found[tag] = node["id"]
        props = node.get("props", {})

        # Check design pressure
        exp_dp = eqpt.get("Eqpt_Design_Pressure", "")
        if exp_dp and not props.get("design_pressure"):
            issues.append({
                "rule": "excel_design_pressure_missing",
                "severity": "high",
                "message": f"{tag}: design_pressure missing (expected: {exp_dp})",
                "node_id": node["id"],
                "expected": str(exp_dp),
            })
        elif exp_dp and props.get("design_pressure"):
            # Loose numeric check: extract first number from both
            def _first_num(s):
                m = re.search(r"[\d.]+", str(s))
                return float(m.group()) if m else None
            exp_n = _first_num(exp_dp)
            got_n = _first_num(str(props["design_pressure"]))
            if exp_n and got_n and abs(exp_n - got_n) > 1.0:
                warnings.append({
                    "rule": "excel_design_pressure_mismatch",
                    "severity": "medium",
                    "message": f"{tag}: design_pressure {props['design_pressure']} vs expected {exp_dp}",
                    "node_id": node["id"],
                })

        # Check design temperature
        exp_dt = eqpt.get("Eqpt_Design_Temperature", "")
        if exp_dt and not props.get("design_temp"):
            issues.append({
                "rule": "excel_design_temp_missing",
                "severity": "high",
                "message": f"{tag}: design_temp missing (expected: {exp_dt})",
                "node_id": node["id"],
                "expected": str(exp_dt),
            })

    # ── Instruments (field gauges + DCS transmitters + ESD transmitters) ──────
    all_instruments = (
        [(r, "Field_Inst_Tag",    "field_gauge")    for r in gt.get("field_gauges", [])] +
        [(r, "Field_TX_DCS_Tag",  "dcs_transmitter") for r in gt.get("field_tx_dcs", [])] +
        [(r, "Field_TX_ESD_Tag",  "esd_transmitter") for r in gt.get("field_tx_esd", [])]
    )
    for row, tag_col, kind in all_instruments:
        tag = row.get(tag_col, "")
        if not tag:
            continue
        # Handle compound tags like LZT002A/B/C — split and check each
        sub_tags = [t.strip() for t in re.split(r"[/,]", tag)]
        base = sub_tags[0]
        # Check for the base tag or any variant
        node = _find_node(nodes, base)
        if not node and len(sub_tags) > 1:
            for st in sub_tags[1:]:
                # Try appending suffix to base stem
                stem = re.sub(r"[A-Z]$", "", base)
                node = _find_node(nodes, stem + st) or _find_node(nodes, st)
                if node:
                    break
        if not node:
            issues.append({
                "rule": f"excel_{kind}_missing",
                "severity": "high",
                "message": f"{kind} {tag} not found in graph",
                "expected_tag": tag,
            })
            missing[tag] = kind
        else:
            found[tag] = node["id"]

    # ── Controllers ───────────────────────────────────────────────────────────
    for row in gt.get("dcs_controllers", []):
        tag     = row.get("DCS_CNTRLR_Tag", "")
        inp     = row.get("DCS_CNTRLR_Input", "")
        out     = row.get("DCS_CNTRLR_Output", "")
        node    = _find_node(nodes, tag)
        if not node:
            issues.append({
                "rule": "excel_dcs_controller_missing",
                "severity": "high",
                "message": f"DCS controller {tag} not found in graph",
                "expected_tag": tag,
            })
            missing[tag] = "dcs_controller"
        else:
            found[tag] = node["id"]
            # Check loop wiring: input and output should exist and be connected
            in_node  = _find_node(nodes, inp)
            out_node = _find_node(nodes, out)
            if not in_node:
                warnings.append({
                    "rule": "excel_loop_input_missing",
                    "severity": "medium",
                    "message": f"Controller {tag} input {inp} not found in graph",
                })
            if not out_node:
                warnings.append({
                    "rule": "excel_loop_output_missing",
                    "severity": "medium",
                    "message": f"Controller {tag} output {out} not found in graph",
                })

    for row in gt.get("esd_controllers", []):
        tag  = row.get("ESD_CNTRLR_Tag", "")
        node = _find_node(nodes, tag)
        if not node:
            issues.append({
                "rule": "excel_esd_controller_missing",
                "severity": "high",
                "message": f"ESD controller {tag} not found in graph",
                "expected_tag": tag,
            })
            missing[tag] = "esd_controller"
        else:
            found[tag] = node["id"]

    # ── Valves (control, ESD, manual) ─────────────────────────────────────────
    all_valves = (
        [(r, "Control_Valve_Tag", "Control_Valve__Size_Process", "control_valve") for r in gt.get("control_valves", [])] +
        [(r, "ESD_Valve_Tag",     "ESD_Valve__Size_Process",     "esd_valve")     for r in gt.get("esd_valves", [])] +
        [(r, "Manual_Valve_Tag",  "Manual_Valve__Size_Process",  "manual_valve")  for r in gt.get("manual_valves", [])]
    )
    for row, tag_col, size_col, kind in all_valves:
        tag      = row.get(tag_col, "")
        exp_size = row.get(size_col, "")
        if not tag:
            continue
        node = _find_node(nodes, tag)
        if not node:
            issues.append({
                "rule": f"excel_{kind}_missing",
                "severity": "high",
                "message": f"{kind} {tag} not found in graph",
                "expected_tag": tag,
            })
            missing[tag] = kind
        else:
            found[tag] = node["id"]
            # Check size
            if exp_size:
                got_size = (node.get("props") or {}).get("size", "")
                if got_size:
                    def _norm_size(s):
                        return re.sub(r"[\s\"\'in]", "", str(s).lower())
                    if _norm_size(got_size) != _norm_size(exp_size):
                        warnings.append({
                            "rule": f"excel_{kind}_size_mismatch",
                            "severity": "medium",
                            "message": f"{kind} {tag}: size {got_size} vs expected {exp_size}",
                            "node_id": node["id"],
                        })

    excel_summary = {
        "total_reference_tags": len(found) + len(missing),
        "found_in_graph": len(found),
        "missing_from_graph": len(missing),
        "missing_tags": list(missing.keys()),
        "coverage_pct": round(len(found) / max(len(found) + len(missing), 1) * 100, 1),
    }

    return issues, warnings, excel_summary


# ─────────────────────────────────────────────────────────────────────────────
# Section 2: OCR cross-reference
# ─────────────────────────────────────────────────────────────────────────────

def _validate_ocr(nodes: list, pid_id: str) -> tuple[list, list, dict]:
    issues = []
    warnings = []
    ocr_tags = load_ocr_tags(pid_id)
    graph_tags = {_normalize_tag(n["tag"]): n for n in nodes if n.get("tag")}
    ocr_norm   = {_normalize_tag(t): t for t in ocr_tags if t.strip()}

    confirmed_tags = []
    missed_in_graph = []
    extra_in_graph = []

    if ocr_tags:
        missed_in_graph = [ocr_norm[t] for t in ocr_norm if t not in graph_tags]
        extra_in_graph  = [graph_tags[t]["tag"] for t in graph_tags if t not in ocr_norm]
        confirmed_tags  = [graph_tags[t]["tag"] for t in graph_tags if t in ocr_norm]

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
    else:
        warnings.append({"rule": "ocr_unavailable", "severity": "low",
                         "message": "No OCR tag file found for this P&ID"})

    ocr_summary = {
        "ocr_tag_count": len(ocr_tags),
        "confirmed": len(confirmed_tags),
        "missed_in_graph": len(missed_in_graph),
        "extra_in_graph": len(extra_in_graph),
        "coverage_pct": round(len(confirmed_tags) / max(len(ocr_norm), 1) * 100, 1) if ocr_tags else None,
    }
    return issues, warnings, ocr_summary


# ─────────────────────────────────────────────────────────────────────────────
# Section 3: Completeness rules
# ─────────────────────────────────────────────────────────────────────────────

def _validate_completeness(nodes: list, edges: list) -> tuple[list, list]:
    issues = []
    warnings = []

    # Every vessel must have design/op pressure + temp
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

    # Every PSV must have set_pressure and size_code
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

    # Every valve should have normal_position
    valves = [n for n in nodes if n.get("type") == "valve"]
    valves_missing_pos = [
        v.get("tag") or v["id"] for v in valves
        if not (v.get("props") or {}).get("normal_position")
        and not (v.get("props") or {}).get("fail_position")
    ]
    if valves_missing_pos:
        warnings.append({
            "rule": "valve_normal_position",
            "severity": "medium",
            "message": f"{len(valves_missing_pos)} valves missing normal/fail position",
            "items": valves_missing_pos[:30],
        })

    # Spec break nodes should have from_spec and to_spec
    spec_break_nodes = [n for n in nodes if (n.get("props") or {}).get("spec_change")]
    for sb in spec_break_nodes:
        props = sb.get("props", {})
        if not props.get("from_spec") or not props.get("to_spec"):
            warnings.append({
                "rule": "spec_break_attributes",
                "severity": "medium",
                "message": f"Spec break node {sb['id']} missing from_spec or to_spec",
                "node_id": sb["id"],
            })

    # Terminators should have off_page_ref
    terminators = [n for n in nodes if n.get("type") == "terminator"]
    term_missing = [t["id"] for t in terminators if not t.get("off_page_ref")]
    if term_missing:
        warnings.append({
            "rule": "terminator_ref",
            "severity": "medium",
            "message": f"{len(term_missing)} terminators missing off_page_ref",
            "items": term_missing,
        })

    # Control loops: transmitter + controller + output valve
    loop_map: dict[str, list] = {}
    for n in nodes:
        if n.get("loop_id"):
            loop_map.setdefault(n["loop_id"], []).append(n)
    for loop_id, members in loop_map.items():
        has_valve = any(n.get("type") == "valve" for n in members)
        has_instrument = any(n.get("type") == "instrument" for n in members)
        if not (has_valve and has_instrument):
            warnings.append({
                "rule": "control_loop_completeness",
                "severity": "low",
                "message": f"Loop {loop_id} may be incomplete",
                "members": [n.get("tag") or n["id"] for n in members],
            })

    return issues, warnings


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def validate_graph(pid_id: str, graph: dict, force: bool = False) -> dict:
    """
    Validate a pid.graph.v0.1.1 graph against all three sources.
    Returns and saves a confidence report.
    """
    work_dir    = pid_work_dir(pid_id)
    report_path = work_dir / "validation_report.json"

    if report_path.exists() and not force:
        print(f"[validate] Resume: validation_report.json already exists for {pid_id}")
        return load_json(report_path)

    print(f"[validate] Validating {pid_id}")

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    all_issues   = []
    all_warnings = []

    # ── 1. Excel ground truth (DISABLED — data not yet validated as correct) ───
    # Plumbing kept for when a verified ground truth source is provided.
    # Issues and warnings from Excel are NOT included in confidence scoring.
    excel_summary = {"status": "disabled", "reason": "ground truth not yet validated"}
    gt = _load_excel_ground_truth()
    if gt:
        _, _, excel_summary_raw = _validate_excel(nodes, edges, gt)
        excel_summary = {**excel_summary_raw, "status": "disabled", "excluded_from_score": True}
        print(f"[validate] Excel (info only, not scored): "
              f"{excel_summary_raw['found_in_graph']}/{excel_summary_raw['total_reference_tags']} "
              f"reference tags found ({excel_summary_raw['coverage_pct']}%)")

    # ── 2. OCR cross-reference ────────────────────────────────────────────────
    o_issues, o_warnings, ocr_summary = _validate_ocr(nodes, pid_id)
    all_issues   += o_issues
    all_warnings += o_warnings
    if ocr_summary.get("ocr_tag_count"):
        print(f"[validate] OCR: {ocr_summary['confirmed']} confirmed, "
              f"{ocr_summary['missed_in_graph']} missed, "
              f"{ocr_summary['extra_in_graph']} unconfirmed")

    # ── 3. Completeness rules ─────────────────────────────────────────────────
    c_issues, c_warnings = _validate_completeness(nodes, edges)
    all_issues   += c_issues
    all_warnings += c_warnings

    # ── Confidence score ──────────────────────────────────────────────────────
    # Base 100, deduct for issues by severity
    high_issues   = [i for i in all_issues   if i.get("severity") == "high"]
    medium_issues = [i for i in all_issues   if i.get("severity") == "medium"] + \
                    [w for w in all_warnings if w.get("severity") == "medium"]

    confidence = 100.0
    confidence -= len(high_issues)   * 5
    confidence -= len(medium_issues) * 2
    confidence  = max(0.0, min(100.0, confidence))

    # ── Report ────────────────────────────────────────────────────────────────
    vessels = [n for n in nodes if n.get("type") == "equipment"]
    valves  = [n for n in nodes if n.get("type") == "valve"]
    insts   = [n for n in nodes if n.get("type") == "instrument"]

    report = {
        "pid_id": pid_id,
        "schema_version": "pid.graph.v0.1.1",
        "strategy_version": STRATEGY_VERSION,
        "stats": {
            "nodes": len(nodes),
            "edges": len(edges),
            "equipment": len(vessels),
            "valves": len(valves),
            "instruments": len(insts),
            "terminators": len([n for n in nodes if n.get("type") == "terminator"]),
        },
        "excel_validation": excel_summary,
        "ocr_validation": ocr_summary,
        "confidence_score": round(confidence, 1),
        "high_issues":   high_issues,
        "medium_issues": medium_issues,
        "all_warnings":  all_warnings,
        "summary": (
            f"Confidence: {confidence:.0f}%. "
            f"{len(nodes)} nodes, {len(edges)} edges. "
            f"OCR coverage: {ocr_summary.get('coverage_pct', 'N/A')}%. "
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
