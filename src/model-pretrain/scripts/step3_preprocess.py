"""
Step 3: Preprocess Images
==========================
- Tile large PID2Graph images (7168×4562) into 640×640 patches with overlap
- Normalize image colour format (all → RGB)
- Resize eng_diagrams symbols (100×100 → 640×640, padded to square)
- Pass-through kaggle tiles (already 1280×1280, keep as-is)
- Filter: skip tiles that are >92% near-white (blank background tiles)
- For each tile, clip + remap YOLO annotations; discard annotations
  whose clipped area is <30% of their original area

Output:
  datasets/preprocessed/
    {dataset_name}/
      images/   *.jpg / *.png
      labels/   *.txt  (YOLO, unified class IDs)
    dataset.yaml

Usage:
  python scripts/step3_preprocess.py
"""

import os
import glob
import shutil
import numpy as np
import yaml
from pathlib import Path
from PIL import Image, ImageOps

# ─── Config ──────────────────────────────────────────────────────────────────
ROOT   = Path(__file__).parent.parent
PROC   = ROOT / "datasets" / "processed"
PREPROC = ROOT / "datasets" / "preprocessed"

TILE_SIZE    = 640    # px — target tile side length
OVERLAP      = 100    # px — overlap between adjacent tiles
STRIDE       = TILE_SIZE - OVERLAP   # = 540 px

MIN_VIS      = 0.30   # annotation must have ≥30% area inside tile to be kept
BLANK_THRESH = 0.92   # tile is blank if ≥92% pixels are near-white (≥240)
BLANK_PIXEL  = 240    # grayscale threshold for "white"

ENG_OUT_SIZE = 640    # resize eng_diagrams symbols to this (with padding)

with open(ROOT / "datasets" / "class_names.yaml") as f:
    CLASS_CFG = yaml.safe_load(f)
UNIFIED_NAMES = CLASS_CFG["names"]
NC = CLASS_CFG["nc"]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def make_symlink(src: Path, dst: Path):
    if not dst.exists():
        dst.symlink_to(src.resolve())


def is_blank(arr: np.ndarray) -> bool:
    """Return True if >=BLANK_THRESH fraction of pixels are near-white."""
    gray = arr.mean(axis=2) if arr.ndim == 3 else arr
    frac = (gray >= BLANK_PIXEL).sum() / gray.size
    return frac >= BLANK_THRESH


def write_dataset_yaml(out_dir: Path, name: str, notes: str = ""):
    data = {
        "path": str(out_dir.resolve()),
        "train": "images",
        "val":   "images",
        "nc":    NC,
        "names": [UNIFIED_NAMES[i] for i in range(NC)],
    }
    if notes:
        data["notes"] = notes
    with open(out_dir / "dataset.yaml", "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def read_yolo_labels(lbl_path: Path):
    """Return list of (cls_id, cx, cy, bw, bh) in [0,1] normalised coords."""
    annotations = []
    if not lbl_path.exists() or lbl_path.stat().st_size == 0:
        return annotations
    for line in lbl_path.read_text().strip().splitlines():
        parts = line.strip().split()
        if len(parts) == 5:
            annotations.append((int(parts[0]), *[float(x) for x in parts[1:]]))
    return annotations


def clip_annotations_to_tile(annotations, tile_x, tile_y, tile_w, tile_h,
                               img_w, img_h, min_vis=MIN_VIS):
    """
    Given full-image YOLO annotations and a tile rectangle, return
    annotations clipped and renormalised to the tile.
    annotations: list of (cls_id, cx_n, cy_n, bw_n, bh_n) — normalised to full image
    tile_x/y: top-left corner of tile in pixels (full-image coords)
    tile_w/h: tile size in pixels
    Returns list of (cls_id, cx_t, cy_t, bw_t, bh_t) — normalised to tile
    """
    result = []
    for cls_id, cx_n, cy_n, bw_n, bh_n in annotations:
        # Convert to full-image pixel coords
        cx_px = cx_n * img_w
        cy_px = cy_n * img_h
        bw_px = bw_n * img_w
        bh_px = bh_n * img_h
        xmin = cx_px - bw_px / 2
        ymin = cy_px - bh_px / 2
        xmax = cx_px + bw_px / 2
        ymax = cy_px + bh_px / 2

        orig_area = max(bw_px * bh_px, 1e-6)

        # Clip to tile
        tx0, ty0 = tile_x, tile_y
        tx1, ty1 = tile_x + tile_w, tile_y + tile_h
        cx0 = max(xmin, tx0)
        cy0 = max(ymin, ty0)
        cx1 = min(xmax, tx1)
        cy1 = min(ymax, ty1)

        if cx1 <= cx0 or cy1 <= cy0:
            continue  # no overlap

        clipped_area = (cx1 - cx0) * (cy1 - cy0)
        if clipped_area / orig_area < min_vis:
            continue  # too little of the bbox is in this tile

        # Renormalise to tile coords
        ncx = ((cx0 + cx1) / 2 - tx0) / tile_w
        ncy = ((cy0 + cy1) / 2 - ty0) / tile_h
        nbw = (cx1 - cx0) / tile_w
        nbh = (cy1 - cy0) / tile_h

        ncx = max(0.0, min(1.0, ncx))
        ncy = max(0.0, min(1.0, ncy))
        nbw = max(1e-6, min(1.0, nbw))
        nbh = max(1e-6, min(1.0, nbh))

        result.append((cls_id, ncx, ncy, nbw, nbh))
    return result


def tile_image(img_path: Path, lbl_path: Path,
               img_out: Path, lbl_out: Path, stem: str):
    """
    Tile a single large image into TILE_SIZE×TILE_SIZE patches.
    Returns (tiles_written, annotations_written).
    """
    img = Image.open(img_path).convert("RGB")
    img_w, img_h = img.size
    img_arr = np.array(img)

    annotations = read_yolo_labels(lbl_path)

    tiles_written = 0
    anns_written  = 0
    tile_idx      = 0

    # Generate tile grid with overlap
    y_starts = list(range(0, img_h - TILE_SIZE + 1, STRIDE))
    if not y_starts or y_starts[-1] + TILE_SIZE < img_h:
        y_starts.append(max(0, img_h - TILE_SIZE))

    x_starts = list(range(0, img_w - TILE_SIZE + 1, STRIDE))
    if not x_starts or x_starts[-1] + TILE_SIZE < img_w:
        x_starts.append(max(0, img_w - TILE_SIZE))

    for ty in y_starts:
        for tx in x_starts:
            tw = min(TILE_SIZE, img_w - tx)
            th = min(TILE_SIZE, img_h - ty)

            tile_arr = img_arr[ty:ty+th, tx:tx+tw]

            # If tile is smaller than TILE_SIZE (edge case), pad with white
            if tw < TILE_SIZE or th < TILE_SIZE:
                padded = np.full((TILE_SIZE, TILE_SIZE, 3), 255, dtype=np.uint8)
                padded[:th, :tw] = tile_arr
                tile_arr = padded
                tw = th = TILE_SIZE

            # Clip annotations first — always keep tiles that have annotations
            tile_anns = clip_annotations_to_tile(
                annotations, tx, ty, tw, th, img_w, img_h)

            # Skip blank tiles only if they also have no annotations
            if not tile_anns and is_blank(tile_arr):
                tile_idx += 1
                continue

            tile_stem = f"{stem}_t{tile_idx:04d}"
            lbl_lines = [f"{c} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"
                         for c, cx, cy, bw, bh in tile_anns]
            (lbl_out / f"{tile_stem}.txt").write_text("\n".join(lbl_lines))

            # Save tile image as JPEG
            tile_img = Image.fromarray(tile_arr)
            tile_img.save(img_out / f"{tile_stem}.jpg", quality=95)

            anns_written  += len(tile_anns)
            tiles_written += 1
            tile_idx      += 1

    return tiles_written, anns_written


# ─── Dataset processors ──────────────────────────────────────────────────────

def process_pid2graph(ds_name: str):
    """Tile full-size PID2Graph images."""
    print(f"\n  Tiling {ds_name} ...")
    src = PROC / ds_name
    out = ensure_dir(PREPROC / ds_name)
    img_out = ensure_dir(out / "images")
    lbl_out = ensure_dir(out / "labels")

    img_files = sorted((src / "images").iterdir())
    total_tiles = total_anns = 0

    for img_path in img_files:
        stem = img_path.stem
        lbl_path = src / "labels" / f"{stem}.txt"
        t, a = tile_image(img_path, lbl_path, img_out, lbl_out, stem)
        total_tiles += t
        total_anns  += a

    write_dataset_yaml(out, ds_name,
        notes=f"Tiled from full-size P&IDs. Tile={TILE_SIZE}px, stride={STRIDE}px, "
              f"overlap={OVERLAP}px. Blank tiles (>{int(BLANK_THRESH*100)}% white) skipped.")
    print(f"    {len(img_files)} source images → {total_tiles} tiles, {total_anns} annotations")
    return total_tiles, total_anns


def process_kaggle():
    """
    Kaggle tiles are already 1280×1280.
    Symlink images and copy labels directly — no tiling needed.
    """
    print("\n  Pass-through kaggle_pid_symbols (1280×1280 tiles, no re-tiling) ...")
    src = PROC / "kaggle_pid_symbols"
    out = ensure_dir(PREPROC / "kaggle_pid_symbols")
    img_out = ensure_dir(out / "images")
    lbl_out = ensure_dir(out / "labels")

    img_files = sorted((src / "images").iterdir())
    total_anns = 0
    kept = 0
    skipped_blank = 0

    for img_path in img_files:
        # Quick blank check
        img_arr = np.array(Image.open(img_path).convert("RGB"))
        if is_blank(img_arr):
            skipped_blank += 1
            continue

        stem = img_path.stem
        lbl_src = src / "labels" / f"{stem}.txt"

        make_symlink(img_path.resolve(), img_out / img_path.name)
        lbl_dst = lbl_out / f"{stem}.txt"
        if lbl_src.exists():
            shutil.copy2(lbl_src, lbl_dst)
            total_anns += len(read_yolo_labels(lbl_dst))
        else:
            lbl_dst.write_text("")
        kept += 1

    # Copy split files
    for txt in ["train.txt", "val.txt"]:
        if (src / txt).exists():
            shutil.copy2(src / txt, out / txt)

    write_dataset_yaml(out, "kaggle_pid_symbols",
        notes="Kaggle tiles already 1280×1280. Blank tiles filtered out.")
    print(f"    {len(img_files)} source tiles → {kept} kept, {skipped_blank} blank removed, "
          f"{total_anns} annotations")
    return kept, total_anns


def process_eng_diagrams():
    """
    Resize 100×100 symbol images to ENG_OUT_SIZE×ENG_OUT_SIZE with white padding.
    Labels stay the same (whole-image bbox).
    """
    print(f"\n  Resizing eng_diagrams (100×100 → {ENG_OUT_SIZE}×{ENG_OUT_SIZE} padded) ...")
    src = PROC / "eng_diagrams"
    out = ensure_dir(PREPROC / "eng_diagrams")
    img_out = ensure_dir(out / "images")
    lbl_out = ensure_dir(out / "labels")

    img_files = sorted((src / "images").iterdir())
    for img_path in img_files:
        img = Image.open(img_path).convert("RGB")
        # Pad to square then resize — keeps aspect ratio (already square 100×100)
        resized = img.resize((ENG_OUT_SIZE, ENG_OUT_SIZE), Image.LANCZOS)
        resized.save(img_out / f"{img_path.stem}.jpg", quality=95)

        lbl_src = src / "labels" / f"{img_path.stem}.txt"
        lbl_dst = lbl_out / f"{img_path.stem}.txt"
        if lbl_src.exists():
            shutil.copy2(lbl_src, lbl_dst)
        else:
            lbl_dst.write_text("")

    write_dataset_yaml(out, "eng_diagrams",
        notes=f"Individual P&ID symbols resized from 100×100 to {ENG_OUT_SIZE}×{ENG_OUT_SIZE}. "
              "Whole-image bounding box. Use primarily for augmentation.")
    print(f"    {len(img_files)} images resized")
    return len(img_files), len(img_files)


# ─── Quality report ───────────────────────────────────────────────────────────

def quality_report():
    print("\n" + "="*65)
    print("Step 3 Complete — Preprocessed dataset summary")
    print("="*65)
    grand_imgs = grand_anns = 0
    for ds_dir in sorted(PREPROC.iterdir()):
        if not ds_dir.is_dir():
            continue
        img_dir = ds_dir / "images"
        lbl_dir = ds_dir / "labels"
        if not img_dir.exists():
            continue
        imgs = list(img_dir.iterdir())
        lbls = [f for f in lbl_dir.glob("*.txt")] if lbl_dir.exists() else []
        anns = sum(
            len(f.read_text().strip().splitlines())
            for f in lbls if f.stat().st_size > 0
        )
        non_empty = sum(1 for f in lbls if f.stat().st_size > 0)
        grand_imgs += len(imgs)
        grand_anns += anns
        print(f"  {ds_dir.name:<32} {len(imgs):>7} imgs  "
              f"{anns:>8} anns  ({non_empty} non-empty)")
    print(f"  {'TOTAL':<32} {grand_imgs:>7} imgs  {grand_anns:>8} anns")
    print()


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Step 3: Preprocess Images")
    print(f"  PROC    → {PROC}")
    print(f"  PREPROC → {PREPROC}")
    print(f"  Tile size={TILE_SIZE}px  stride={STRIDE}px  overlap={OVERLAP}px")
    print(f"  Blank filter={int(BLANK_THRESH*100)}%  min annotation visibility={int(MIN_VIS*100)}%")

    process_pid2graph("pid2graph_dataset_pid")
    process_pid2graph("pid2graph_open100")
    process_pid2graph("pid2graph_synthetic")
    process_kaggle()
    process_eng_diagrams()
    quality_report()
