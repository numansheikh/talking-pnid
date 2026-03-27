"""
ingest.py — CLI orchestrator for the P&ID ingestion pipeline.

Usage:
  python ingest.py --pdf ../../data/datasets/rumaila-pp01/pdfs/100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf
  python ingest.py --all
  python ingest.py --pdf ... --step extract
  python ingest.py --supergraph
  python ingest.py --pdf ... --force   # re-run all steps even if outputs exist

Steps (all resume by default):
  tile      → PDF → 3×2 PNG tiles + embedded text
  extract   → tiles → Claude Opus 4.6 vision (3 passes × 6 tiles = 18 API calls)
  stitch    → 6 tile JSONs → unified_extraction.json
  schema    → unified_extraction → pid.graph.v0.1.1 JSON
  validate  → graph vs Excel + OCR + completeness rules → confidence report
"""

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    PDFS_DIR, POC_PIDS, STRATEGY_VERSION,
    pid_id_from_pdf, pid_work_dir, graphs_dir, load_json,
)
from tile       import tile_pdf
from extract    import extract_all_tiles
from stitch     import stitch
from schema     import convert_to_graph
from validate   import validate_graph
from supergraph import build_supergraph


PIPELINE_STEPS = ["tile", "extract", "stitch", "schema", "validate"]

_step_estimates = {
    "tile":     "~5s",
    "extract":  "~15-25 min (18 Claude Opus calls)",
    "stitch":   "~5s",
    "schema":   "~1-2 min (1 Claude Sonnet call)",
    "validate": "~5s",
}


def _banner(msg: str, width: int = 60) -> None:
    print(f"\n{'='*width}")
    print(f"  {msg}")
    print(f"{'='*width}")


def _step_header(n: int, total: int, name: str) -> None:
    est = _step_estimates.get(name, "")
    print(f"\n── Step {n}/{total}: {name.upper()} {'  ' + est if est else ''}")
    print(f"   {'─'*50}")


def _step_done(name: str, elapsed: float) -> None:
    print(f"   ✓ {name} done in {elapsed:.1f}s")


def run_pipeline(pdf_path: Path, step: str | None = None, force: bool = False) -> None:
    """Run the full pipeline (or a single step) for one P&ID PDF."""
    if not pdf_path.exists():
        print(f"[ingest] ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    pid_id = pid_id_from_pdf(pdf_path)
    total_steps = 1 if step else len(PIPELINE_STEPS)

    _banner(f"P&ID: {pid_id}  |  Strategy: {STRATEGY_VERSION}")
    print(f"  PDF:  {pdf_path.name}")
    print(f"  Mode: {'single step — ' + step if step else 'full pipeline'}")
    print(f"  Out:  {pid_work_dir(pid_id)}")

    t_pipeline = time.time()
    step_results = {}

    def should_run(s: str) -> bool:
        return step is None or step == s

    step_num = [0]
    def next_step(name: str):
        step_num[0] += 1
        _step_header(step_num[0], total_steps, name)
        return time.time()

    # ── Step 1: Tile ─────────────────────────────────────────────────────────
    tile_meta = None
    if should_run("tile"):
        t = next_step("tile")
        tile_meta = tile_pdf(pdf_path, pid_id, force=force)
        _step_done("tile", time.time() - t)
        step_results["tile"] = {
            "tiles": len(tile_meta.get("tiles", [])),
            "resolution": f"{tile_meta.get('full_image_size', {}).get('width')}×{tile_meta.get('full_image_size', {}).get('height')}px",
        }

    if tile_meta is None:
        meta_path = pid_work_dir(pid_id) / "tiles" / "tile_metadata.json"
        if meta_path.exists():
            tile_meta = load_json(meta_path)
        elif step and step != "tile":
            print(f"\n[ingest] ERROR: tiles not found — run 'tile' step first.")
            sys.exit(1)

    # ── Step 2: Extract ───────────────────────────────────────────────────────
    extractions = None
    if should_run("extract") and tile_meta:
        t = next_step("extract")
        print(f"   Note: 6 tiles × 3 passes = 18 Claude Opus 4.6 calls. This takes a while.")
        print(f"         Resumable — interrupted runs continue from last completed pass.\n")
        extractions = extract_all_tiles(pid_id, tile_meta, force=force)
        _step_done("extract", time.time() - t)
        step_results["extract"] = {"tiles_extracted": len(extractions)}

    if extractions is None:
        ext_path = pid_work_dir(pid_id) / "all_tile_extractions.json"
        if ext_path.exists():
            extractions = load_json(ext_path)
        elif step and step in ("stitch", "schema", "validate"):
            print(f"\n[ingest] ERROR: extractions not found — run 'extract' step first.")
            sys.exit(1)

    # ── Step 3: Stitch ────────────────────────────────────────────────────────
    unified = None
    if should_run("stitch") and extractions is not None:
        t = next_step("stitch")
        unified = stitch(pid_id, extractions, force=force)
        _step_done("stitch", time.time() - t)
        step_results["stitch"] = {
            "components": unified.get("stats", {}).get("components_deduped"),
            "connections": len(unified.get("connections", [])),
        }

    if unified is None:
        uni_path = pid_work_dir(pid_id) / "unified_extraction.json"
        if uni_path.exists():
            unified = load_json(uni_path)
        elif step and step in ("schema", "validate"):
            print(f"\n[ingest] ERROR: unified extraction not found — run 'stitch' step first.")
            sys.exit(1)

    # ── Step 4: Schema ────────────────────────────────────────────────────────
    graph = None
    if should_run("schema") and unified is not None:
        t = next_step("schema")
        graph = convert_to_graph(pid_id, unified, force=force)
        _step_done("schema", time.time() - t)
        step_results["schema"] = {
            "nodes": len(graph.get("nodes", [])),
            "edges": len(graph.get("edges", [])),
        }

    if graph is None:
        gpath = graphs_dir() / f"{pid_id}.graph.json"
        if gpath.exists():
            graph = load_json(gpath)
        elif step == "validate":
            print(f"\n[ingest] ERROR: graph not found — run 'schema' step first.")
            sys.exit(1)

    # ── Step 5: Validate ──────────────────────────────────────────────────────
    report = None
    if should_run("validate") and graph is not None:
        t = next_step("validate")
        report = validate_graph(pid_id, graph, force=force)
        _step_done("validate", time.time() - t)
        step_results["validate"] = {
            "confidence": report.get("confidence_score"),
            "excel_coverage": report.get("excel_validation", {}).get("coverage_pct"),
            "ocr_coverage": report.get("ocr_validation", {}).get("coverage_pct"),
            "high_issues": len(report.get("high_issues", [])),
        }

    # ── Final summary ─────────────────────────────────────────────────────────
    elapsed = time.time() - t_pipeline
    _banner(f"DONE — {pid_id}  ({elapsed:.0f}s total)")

    if "tile" in step_results:
        r = step_results["tile"]
        print(f"  Tile:     {r['tiles']} tiles at {r['resolution']}")
    if "stitch" in step_results:
        r = step_results["stitch"]
        print(f"  Stitch:   {r['components']} components, {r['connections']} connections")
    if "schema" in step_results:
        r = step_results["schema"]
        print(f"  Graph:    {r['nodes']} nodes, {r['edges']} edges")
    if "validate" in step_results:
        r = step_results["validate"]
        print(f"  Validate: confidence {r['confidence']}%  |  "
              f"Excel {r['excel_coverage']}%  |  OCR {r['ocr_coverage']}%  |  "
              f"{r['high_issues']} high issues")
    if report:
        print(f"\n  → {graphs_dir() / f'{pid_id}.graph.json'}")
        print(f"  → {pid_work_dir(pid_id) / 'validation_report.json'}")


def main():
    parser = argparse.ArgumentParser(
        description="P&ID Ingestion Pipeline — PDF → knowledge graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest.py --pdf ../../data/datasets/rumaila-pp01/pdfs/100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf
  python ingest.py --all
  python ingest.py --pdf ... --step extract
  python ingest.py --supergraph
  python ingest.py --pdf ... --force
        """,
    )
    parser.add_argument("--pdf",        type=Path, help="Path to a P&ID PDF")
    parser.add_argument("--all",        action="store_true", help="Run all 3 POC P&IDs")
    parser.add_argument("--supergraph", action="store_true", help="Build super graph from existing P&ID graphs")
    parser.add_argument("--step",       choices=PIPELINE_STEPS, help="Run only this step")
    parser.add_argument("--force",      action="store_true", help="Re-run even if outputs exist")

    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[ingest] ERROR: ANTHROPIC_API_KEY not set and apikey-claude-talking-pnid not found")
        sys.exit(1)

    if args.supergraph:
        _banner("Building Super Graph")
        t = time.time()
        build_supergraph(force=args.force)
        print(f"\n  Done in {time.time()-t:.1f}s → {graphs_dir() / 'supergraph.json'}")
        return

    if args.all:
        _banner(f"Running all {len(POC_PIDS)} POC P&IDs  |  Strategy: {STRATEGY_VERSION}")
        t_all = time.time()
        for pid_id, fname in POC_PIDS.items():
            pdf = PDFS_DIR / fname
            if pdf.exists():
                run_pipeline(pdf, step=args.step, force=args.force)
            else:
                print(f"\n[ingest] WARNING: {fname} not found, skipping {pid_id}")
        if args.step is None:
            print("\n")
            _banner("Building Super Graph")
            build_supergraph(force=args.force)
        print(f"\n[ingest] All done in {time.time()-t_all:.0f}s")
        return

    if args.pdf:
        run_pipeline(args.pdf.resolve(), step=args.step, force=args.force)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
