"""
ingest.py — CLI orchestrator for the P&ID ingestion pipeline.

Usage:
  python ingest.py --pdf ../../data/pdfs/100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf
  python ingest.py --all
  python ingest.py --pdf ... --step extract
  python ingest.py --supergraph
  python ingest.py --pdf ... --force   # re-run all steps even if outputs exist

Steps (all resume by default):
  tile      → PDF → 3×2 PNG tiles + embedded text
  extract   → tiles → Claude Opus vision (3 passes per tile)
  stitch    → 6 tile JSONs → unified_extraction.json
  schema    → unified_extraction → pid.graph.v0.1.1 JSON
  validate  → graph vs OCR tags → confidence report
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add src/ingestion to path so we can import modules directly
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    PDFS_DIR, POC_PIDS,
    pid_id_from_pdf, pid_work_dir, graphs_dir, load_json,
)
from tile       import tile_pdf
from extract    import extract_all_tiles
from stitch     import stitch
from schema     import convert_to_graph
from validate   import validate_graph
from supergraph import build_supergraph


PIPELINE_STEPS = ["tile", "extract", "stitch", "schema", "validate"]


def run_pipeline(pdf_path: Path, step: str | None = None, force: bool = False) -> None:
    """Run the full pipeline (or a single step) for one P&ID PDF."""
    if not pdf_path.exists():
        print(f"[ingest] ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    pid_id = pid_id_from_pdf(pdf_path)
    print(f"\n{'='*60}")
    print(f"[ingest] P&ID: {pid_id}")
    print(f"[ingest] PDF:  {pdf_path.name}")
    if step:
        print(f"[ingest] Step: {step} only")
    print(f"{'='*60}\n")

    t_start = time.time()

    def should_run(s: str) -> bool:
        return step is None or step == s

    # ── Step 1: Tile ─────────────────────────────────────────────────────────
    tile_meta = None
    if should_run("tile"):
        tile_meta = tile_pdf(pdf_path, pid_id, force=force)
        print()

    # Load tile metadata for subsequent steps
    if tile_meta is None:
        meta_path = pid_work_dir(pid_id) / "tiles" / "tile_metadata.json"
        if meta_path.exists():
            tile_meta = load_json(meta_path)
        else:
            if step and step != "tile":
                print(f"[ingest] ERROR: tile_metadata.json not found. Run 'tile' step first.")
                sys.exit(1)

    # ── Step 2: Extract ───────────────────────────────────────────────────────
    extractions = None
    if should_run("extract") and tile_meta:
        extractions = extract_all_tiles(pid_id, tile_meta, force=force)
        print()

    # Load extractions for subsequent steps
    if extractions is None:
        ext_path = pid_work_dir(pid_id) / "all_tile_extractions.json"
        if ext_path.exists():
            extractions = load_json(ext_path)
        else:
            if step and step in ("stitch", "schema", "validate"):
                print(f"[ingest] ERROR: all_tile_extractions.json not found. Run 'extract' step first.")
                sys.exit(1)

    # ── Step 3: Stitch ────────────────────────────────────────────────────────
    unified = None
    if should_run("stitch") and extractions is not None:
        unified = stitch(pid_id, extractions, force=force)
        print()

    # Load unified for subsequent steps
    if unified is None:
        uni_path = pid_work_dir(pid_id) / "unified_extraction.json"
        if uni_path.exists():
            unified = load_json(uni_path)
        else:
            if step and step in ("schema", "validate"):
                print(f"[ingest] ERROR: unified_extraction.json not found. Run 'stitch' step first.")
                sys.exit(1)

    # ── Step 4: Schema ────────────────────────────────────────────────────────
    graph = None
    if should_run("schema") and unified is not None:
        graph = convert_to_graph(pid_id, unified, force=force)
        print()

    # Load graph for validation
    if graph is None:
        gpath = graphs_dir() / f"{pid_id}.graph.json"
        if gpath.exists():
            graph = load_json(gpath)
        else:
            if step == "validate":
                print(f"[ingest] ERROR: {pid_id}.graph.json not found. Run 'schema' step first.")
                sys.exit(1)

    # ── Step 5: Validate ──────────────────────────────────────────────────────
    if should_run("validate") and graph is not None:
        report = validate_graph(pid_id, graph, force=force)
        print()
        print(f"[ingest] Validation: {report.get('summary', 'done')}")

    elapsed = time.time() - t_start
    print(f"\n[ingest] {pid_id} complete in {elapsed:.1f}s")


def main():
    parser = argparse.ArgumentParser(
        description="P&ID Ingestion Pipeline — PDF → knowledge graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest.py --pdf ../../data/pdfs/100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf
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
        print("[ingest] ERROR: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    if args.supergraph:
        build_supergraph(force=args.force)
        return

    if args.all:
        print(f"[ingest] Running all {len(POC_PIDS)} POC P&IDs")
        for pid_id, fname in POC_PIDS.items():
            pdf = PDFS_DIR / fname
            if pdf.exists():
                run_pipeline(pdf, step=args.step, force=args.force)
            else:
                print(f"[ingest] WARNING: {fname} not found, skipping {pid_id}")
        # Build supergraph after all P&IDs are done (unless single-step run)
        if args.step is None:
            print("\n[ingest] Building super graph...")
            build_supergraph(force=args.force)
        return

    if args.pdf:
        run_pipeline(args.pdf.resolve(), step=args.step, force=args.force)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
