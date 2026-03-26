"""
Step 2: Standardize Dataset Formats
====================================
Converts all raw datasets to YOLO format with a unified class taxonomy.

Output structure:
  datasets/processed/
    kaggle_pid_symbols/
      images/          (symlinks to raw tiles - already 1280x1280)
      labels/          (YOLO .txt, class IDs remapped 1-indexed → 0-indexed)
      dataset.yaml
    pid2graph_dataset_pid/
      images/          (symlinks to raw full-size PNGs)
      labels/          (YOLO .txt converted from GraphML, unified class IDs)
      dataset.yaml
    pid2graph_open100/
      images/
      labels/
      dataset.yaml
    pid2graph_synthetic/
      images/
      labels/
      dataset.yaml
    eng_diagrams/
      images/          (100x100 PNG images reconstructed from CSV)
      labels/          (YOLO .txt: whole-image bbox for each symbol)
      dataset.yaml

Each dataset.yaml is self-contained for standalone training or debugging.
A master merged dataset is produced in Step 4.

Usage:
  python scripts/step2_standardize.py
"""

import os
import csv
import glob
import shutil
import yaml
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
import numpy as np

# ─── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent  # model-pretrain/
RAW = ROOT / "datasets" / "raw"
PROC = ROOT / "datasets" / "processed"

# ─── Unified class taxonomy ──────────────────────────────────────────────────
with open(ROOT / "datasets" / "class_names.yaml") as f:
    CLASS_CFG = yaml.safe_load(f)

UNIFIED_NAMES = CLASS_CFG["names"]          # {0: "arrow", 1: "crossing", ...}
PID2GRAPH_MAP = CLASS_CFG["pid2graph_map"]  # {str: int|None}
ENG_MAP       = CLASS_CFG["eng_diagrams_map"]  # {str: int}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_symlink(src: Path, dst: Path):
    """Create a symlink dst → src. Skip if dst already exists."""
    if not dst.exists():
        dst.symlink_to(src.resolve())


def write_dataset_yaml(out_dir: Path, name: str, nc: int, names: dict, notes: str = ""):
    data = {
        "path": str(out_dir.resolve()),
        "train": "images",
        "val": "images",   # placeholder — split in Step 4
        "nc": nc,
        "names": [names[i] for i in sorted(names)],
    }
    if notes:
        data["notes"] = notes
    with open(out_dir / "dataset.yaml", "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def yolo_line(cls_id: int, xmin: float, ymin: float, xmax: float, ymax: float,
              img_w: int, img_h: int) -> str | None:
    """Convert pixel bbox to YOLO format line. Returns None if bbox is degenerate."""
    bw = xmax - xmin
    bh = ymax - ymin
    if bw <= 0 or bh <= 0:
        return None
    cx = (xmin + bw / 2) / img_w
    cy = (ymin + bh / 2) / img_h
    bw_n = bw / img_w
    bh_n = bh / img_h
    # Clamp to [0, 1]
    cx = max(0.0, min(1.0, cx))
    cy = max(0.0, min(1.0, cy))
    bw_n = max(0.0, min(1.0, bw_n))
    bh_n = max(0.0, min(1.0, bh_n))
    return f"{cls_id} {cx:.6f} {cy:.6f} {bw_n:.6f} {bh_n:.6f}"


# ─── Dataset 1: kaggle_pid_symbols ──────────────────────────────────────────

def process_kaggle():
    """
    Kaggle dataset is already in YOLO format.
    Source: https://github.com/ch-hristov/p-id-symbols
    Raw class IDs are 1-indexed (1–32); mapped directly to unified class IDs.
    Images are symlinked; labels are rewritten with unified class IDs.
    """
    print("\n[1/4] Processing kaggle_pid_symbols ...")
    src_img_dir   = RAW / "kaggle_pid_symbols" / "images (3)"
    src_lbl_dir   = RAW / "kaggle_pid_symbols" / "labels (2)"
    src_train_txt = RAW / "kaggle_pid_symbols" / "train (2).txt"
    src_val_txt   = RAW / "kaggle_pid_symbols" / "val (1).txt"

    out_dir = ensure_dir(PROC / "kaggle_pid_symbols")
    img_out = ensure_dir(out_dir / "images")
    lbl_out = ensure_dir(out_dir / "labels")

    # Build raw_id → unified_class_id map from class_names.yaml
    kaggle_raw_map = {}  # raw_id (int) → unified_id (int)
    for raw_id, (name, unified_id) in CLASS_CFG["kaggle_class_map"].items():
        kaggle_raw_map[int(raw_id)] = int(unified_id)

    skipped_corrupt = 0
    skipped_unknown_class = 0
    processed = 0

    for lbl_src in sorted(src_lbl_dir.glob("*.txt")):
        stem = lbl_src.stem
        img_src = src_img_dir / f"{stem}.jpg"
        if not img_src.exists():
            continue

        content = lbl_src.read_text().strip()
        new_lines = []
        valid = True
        if content:
            for line in content.splitlines():
                parts = line.strip().split()
                if len(parts) != 5:
                    skipped_corrupt += 1
                    valid = False
                    break
                cls_raw = int(parts[0])
                unified_id = kaggle_raw_map.get(cls_raw)
                if unified_id is None:
                    skipped_unknown_class += 1
                    valid = False
                    break
                new_lines.append(f"{unified_id} {' '.join(parts[1:])}")

        if not valid:
            continue

        (lbl_out / lbl_src.name).write_text("\n".join(new_lines))
        make_symlink(img_src, img_out / img_src.name)
        processed += 1

    def rewrite_split(src_txt: Path, dst_txt: Path):
        if not src_txt.exists():
            return
        lines = []
        for line in src_txt.read_text().splitlines():
            stem = Path(line.strip()).stem
            lines.append(f"images/{stem}.jpg")
        dst_txt.write_text("\n".join(lines))

    rewrite_split(src_train_txt, out_dir / "train.txt")
    rewrite_split(src_val_txt,   out_dir / "val.txt")

    write_dataset_yaml(out_dir, "kaggle_pid_symbols", CLASS_CFG["nc"], UNIFIED_NAMES,
                       notes="Source: github.com/ch-hristov/p-id-symbols. "
                             "32 original classes mapped to unified 9-class taxonomy. "
                             "Dominant classes: valve (16 subtypes), instrumentation, general, arrow.")

    print(f"    Processed {processed} pairs, skipped {skipped_corrupt} corrupt, "
          f"{skipped_unknown_class} unknown class.")


# ─── Dataset 2–4: PID2Graph (Dataset PID, OPEN100, Synthetic) ───────────────

def convert_graphml_to_yolo(graphml_path: Path, img_path: Path, out_lbl_path: Path,
                             class_map: dict) -> int:
    """
    Parse a GraphML file and write a YOLO label file.
    Returns number of annotations written.
    """
    ns = "{http://graphml.graphdrawing.org/xmlns}"
    try:
        tree = ET.parse(graphml_path)
    except ET.ParseError:
        return 0

    root = tree.getroot()
    # Build key_id → attr_name mapping
    keys = {}
    for key in root.findall(ns + "key"):
        keys[key.get("id")] = key.get("attr.name")

    try:
        img = Image.open(img_path)
        img_w, img_h = img.size
    except Exception:
        return 0

    lines = []
    for node in root.findall(".//" + ns + "node"):
        data = {}
        for d in node.findall(ns + "data"):
            attr = keys.get(d.get("key"), "")
            if attr and d.text:
                # Prefer long (integer) over double when both exist
                if attr not in data:
                    data[attr] = d.text
                else:
                    # Keep the integer version (last key overrides)
                    data[attr] = d.text

        label = data.get("label", "").strip()
        if not label:
            continue

        cls_id = class_map.get(label)
        if cls_id is None:  # background or unknown → skip
            continue

        try:
            xmin = float(data.get("xmin", 0))
            ymin = float(data.get("ymin", 0))
            xmax = float(data.get("xmax", 0))
            ymax = float(data.get("ymax", 0))
        except ValueError:
            continue

        line = yolo_line(cls_id, xmin, ymin, xmax, ymax, img_w, img_h)
        if line:
            lines.append(line)

    out_lbl_path.write_text("\n".join(lines))
    return len(lines)


def process_pid2graph(subdir_name: str, out_name: str, ext: str = ".png"):
    """Generic processor for any PID2Graph Complete subdirectory."""
    print(f"\n[2/4] Processing PID2Graph/{subdir_name} ...")
    src_dir = RAW / "PID2Graph" / "PID2Graph" / "Complete" / subdir_name
    out_dir  = ensure_dir(PROC / out_name)
    img_out  = ensure_dir(out_dir / "images")
    lbl_out  = ensure_dir(out_dir / "labels")

    total_ann = 0
    processed = 0
    skipped = 0

    for graphml_path in sorted(src_dir.glob("*.graphml")):
        stem = graphml_path.stem
        img_path = src_dir / f"{stem}{ext}"
        if not img_path.exists():
            skipped += 1
            continue

        out_lbl = lbl_out / f"{stem}.txt"
        n = convert_graphml_to_yolo(graphml_path, img_path, out_lbl, PID2GRAPH_MAP)
        total_ann += n

        make_symlink(img_path, img_out / img_path.name)
        processed += 1

    write_dataset_yaml(out_dir, out_name, CLASS_CFG["nc"], UNIFIED_NAMES,
                       notes=f"Converted from PID2Graph GraphML. "
                             f"Full-size images ({ext}); tile in Step 3 before training.")

    print(f"    {processed} images, {total_ann} annotations, {skipped} skipped.")


# ─── Dataset 5: eng_diagrams ─────────────────────────────────────────────────

def process_eng_diagrams():
    """
    Reconstruct 100x100 PNG images from CSV pixel data.
    Each image = one symbol; YOLO label = whole-image bbox for the unified class.
    Symbols with no mapping in ENG_MAP are skipped.
    """
    print("\n[4/4] Processing eng_diagrams ...")
    src_csv = RAW / "eng_diagrams" / "data" / "Symbols_pixel.csv"
    out_dir  = ensure_dir(PROC / "eng_diagrams")
    img_out  = ensure_dir(out_dir / "images")
    lbl_out  = ensure_dir(out_dir / "labels")

    processed = 0
    skipped = 0
    class_counters = {}

    with open(src_csv, newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    for idx, row in enumerate(rows):
        label_str = row[-1].strip()
        cls_id = ENG_MAP.get(label_str)
        if cls_id is None:
            skipped += 1
            continue

        # Reconstruct 100x100 grayscale image
        pixels = np.array([int(v) for v in row[:-1]], dtype=np.uint8).reshape(100, 100)
        img = Image.fromarray(pixels, mode="L").convert("RGB")

        count = class_counters.get(label_str, 0)
        class_counters[label_str] = count + 1
        safe_label = label_str.replace(" ", "_").replace("/", "_").replace("&", "and")
        stem = f"{safe_label}_{count:04d}"

        img.save(img_out / f"{stem}.png")
        # Whole-image bbox: cx=0.5, cy=0.5, w=1.0, h=1.0
        (lbl_out / f"{stem}.txt").write_text(f"{cls_id} 0.500000 0.500000 1.000000 1.000000")
        processed += 1

    write_dataset_yaml(out_dir, "eng_diagrams", CLASS_CFG["nc"], UNIFIED_NAMES,
                       notes="Individual 100x100 symbol crops from eng_diagrams CSV. "
                             "Whole-image bbox. Useful for augmentation; very small images — "
                             "resize to model input size in Step 3.")
    print(f"    {processed} images written, {skipped} skipped (no class mapping).")


# ─── Summary report ──────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "="*60)
    print("Step 2 Complete — Processed dataset summary")
    print("="*60)
    for ds_dir in sorted(PROC.iterdir()):
        if not ds_dir.is_dir():
            continue
        img_count = len(list((ds_dir / "images").glob("*"))) if (ds_dir / "images").exists() else 0
        lbl_count = len(list((ds_dir / "labels").glob("*.txt"))) if (ds_dir / "labels").exists() else 0
        non_empty = sum(1 for f in (ds_dir / "labels").glob("*.txt") if f.stat().st_size > 0) \
                    if (ds_dir / "labels").exists() else 0
        print(f"  {ds_dir.name:<30} images: {img_count:>6}  labels: {lbl_count:>6}  non-empty: {non_empty:>6}")
    print()


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Step 2: Standardize Dataset Formats")
    print(f"  RAW  → {RAW}")
    print(f"  PROC → {PROC}")

    process_kaggle()
    process_pid2graph("Dataset PID",       "pid2graph_dataset_pid", ext=".png")
    process_pid2graph("PID2Graph OPEN100", "pid2graph_open100",      ext=".png")
    process_pid2graph("PID2Graph Synthetic","pid2graph_synthetic",   ext=".jpg")
    process_eng_diagrams()
    print_summary()
