"""
tile.py — Step 1 of the ingestion pipeline.

PDF (page 2 raster) → 3×2 grid of PNG tiles with 15% overlap.
Also extracts embedded text from page 1 (PyMuPDF).

All outputs are written to data/outputs/ingestion/<pid_id>/tiles/.
Resume: skips if tile_metadata.json already exists.
"""

import json
import math
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from config import (
    TILE_ROWS, TILE_COLS, TILE_OVERLAP, TILE_DPI,
    pid_work_dir, save_json,
)


def tile_pdf(pdf_path: Path, pid_id: str, force: bool = False) -> dict:
    """
    Tile the raster page of a P&ID PDF into a 3×2 grid.

    Returns metadata dict describing each tile (path, row, col, pixel bounds).
    If already done (tile_metadata.json exists), returns cached result unless force=True.
    """
    work_dir = pid_work_dir(pid_id)
    tiles_dir = work_dir / "tiles"
    meta_path = tiles_dir / "tile_metadata.json"

    if meta_path.exists() and not force:
        print(f"[tile] Resume: tiles already exist for {pid_id}")
        return json.loads(meta_path.read_text())

    print(f"[tile] Processing {pdf_path.name} → {tiles_dir}")
    doc = fitz.open(str(pdf_path))

    # ── Extract embedded text from page 1 (original PDF layer) ──────────────
    if doc.page_count >= 1:
        page0 = doc[0]
        embedded_text = page0.get_text("text")
        save_json(tiles_dir / "embedded_text.json", {"text": embedded_text})
        print(f"[tile] Extracted {len(embedded_text)} chars of embedded text from page 1")
    else:
        save_json(tiles_dir / "embedded_text.json", {"text": ""})

    # ── Select the raster page (page 2 if available, else page 1) ───────────
    raster_page_idx = 1 if doc.page_count >= 2 else 0
    page = doc[raster_page_idx]

    # Render at full TILE_DPI resolution
    mat = fitz.Matrix(TILE_DPI / 72, TILE_DPI / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)

    # Save full-resolution image for reference
    full_path = tiles_dir / "full_page.png"
    pix.save(str(full_path))
    print(f"[tile] Full page rendered: {pix.width}×{pix.height}px → {full_path.name}")

    # ── Convert to PIL for cropping ──────────────────────────────────────────
    full_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    W, H = full_img.size

    # ── Compute tile boundaries with overlap ─────────────────────────────────
    # Base tile size (without overlap)
    base_w = W / TILE_COLS
    base_h = H / TILE_ROWS

    overlap_px_w = int(base_w * TILE_OVERLAP)
    overlap_px_h = int(base_h * TILE_OVERLAP)

    tiles_meta = []
    for row in range(TILE_ROWS):
        for col in range(TILE_COLS):
            # Base position (no overlap)
            x0 = int(col * base_w)
            y0 = int(row * base_h)
            x1 = int((col + 1) * base_w)
            y1 = int((row + 1) * base_h)

            # Expand with overlap (clamp to image bounds)
            ox0 = max(0, x0 - overlap_px_w)
            oy0 = max(0, y0 - overlap_px_h)
            ox1 = min(W, x1 + overlap_px_w)
            oy1 = min(H, y1 + overlap_px_h)

            tile_img = full_img.crop((ox0, oy0, ox1, oy1))
            tile_name = f"tile_r{row+1}c{col+1}.png"
            tile_path = tiles_dir / tile_name
            tile_img.save(str(tile_path), "PNG")

            tiles_meta.append({
                "name": tile_name,
                "path": str(tile_path),
                "row": row + 1,
                "col": col + 1,
                "bounds": {
                    "x0": ox0, "y0": oy0,
                    "x1": ox1, "y1": oy1,
                    "width": ox1 - ox0,
                    "height": oy1 - oy0,
                },
                "full_image_size": {"width": W, "height": H},
                "base_bounds": {
                    "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                },
            })
            print(f"[tile]   Saved {tile_name} ({ox1-ox0}×{oy1-oy0}px)")

    doc.close()

    metadata = {
        "pid_id": pid_id,
        "pdf": str(pdf_path),
        "raster_page_index": raster_page_idx,
        "full_image_size": {"width": W, "height": H},
        "tile_dpi": TILE_DPI,
        "tile_rows": TILE_ROWS,
        "tile_cols": TILE_COLS,
        "overlap_fraction": TILE_OVERLAP,
        "tiles": tiles_meta,
    }

    save_json(meta_path, metadata)
    print(f"[tile] Done: {len(tiles_meta)} tiles written, metadata → {meta_path}")
    return metadata


if __name__ == "__main__":
    import sys
    from config import PDFS_DIR, pid_id_from_pdf

    if len(sys.argv) < 2:
        print("Usage: python tile.py <path/to/pid.pdf> [--force]")
        sys.exit(1)

    pdf = Path(sys.argv[1])
    force = "--force" in sys.argv
    pid = pid_id_from_pdf(pdf)
    tile_pdf(pdf, pid, force=force)
