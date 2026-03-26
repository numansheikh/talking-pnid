"""
Step 4: Merge Datasets
======================
Combines all preprocessed datasets into a single master dataset with
unified train/val/test splits (80/10/10), stratified per source dataset.

Output:
  datasets/merged/
    images/
      train/   *.jpg
      val/     *.jpg
      test/    *.jpg
    labels/
      train/   *.txt
      val/     *.txt
      test/    *.txt
    dataset.yaml
    manifest.csv    (stem, source_dataset, split, ann_count)

Usage:
  python scripts/step4_merge.py
"""

import os
import csv
import shutil
import random
import yaml
from pathlib import Path
from collections import defaultdict, Counter

# ─── Config ──────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.parent
PREPROC = ROOT / "datasets" / "preprocessed"
MERGED  = ROOT / "datasets" / "merged"

TRAIN_RATIO = 0.80
VAL_RATIO   = 0.10
TEST_RATIO  = 0.10

SEED = 42

# Datasets and the weight to use for sampling.
# eng_diagrams symbols are tiny crops — useful but we don't want them to dominate.
# All others contribute fully.
DATASET_WEIGHTS = {
    "pid2graph_dataset_pid": 1.0,
    "pid2graph_open100":     1.0,
    "pid2graph_synthetic":   1.0,
    "kaggle_pid_symbols":    1.0,
    "eng_diagrams":          1.0,
}

with open(ROOT / "datasets" / "class_names.yaml") as f:
    CLASS_CFG = yaml.safe_load(f)
UNIFIED_NAMES = CLASS_CFG["names"]
NC = CLASS_CFG["nc"]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def split_list(items: list, train_r: float, val_r: float, rng: random.Random):
    """Shuffle and split a list into train/val/test."""
    rng.shuffle(items)
    n = len(items)
    n_train = int(n * train_r)
    n_val   = int(n * val_r)
    return items[:n_train], items[n_train:n_train+n_val], items[n_train+n_val:]


def count_annotations(lbl_path: Path) -> int:
    if not lbl_path.exists() or lbl_path.stat().st_size == 0:
        return 0
    return len(lbl_path.read_text().strip().splitlines())


def class_dist(lbl_path: Path) -> Counter:
    c = Counter()
    if lbl_path.exists() and lbl_path.stat().st_size > 0:
        for line in lbl_path.read_text().strip().splitlines():
            c[int(line.split()[0])] += 1
    return c


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    rng = random.Random(SEED)

    # Create output dirs
    for split in ["train", "val", "test"]:
        ensure_dir(MERGED / "images" / split)
        ensure_dir(MERGED / "labels" / split)

    manifest_rows = []   # (stem, source, split, ann_count)
    split_counts  = defaultdict(int)
    class_dist_by_split = {s: Counter() for s in ["train", "val", "test"]}

    print("Step 4: Merge Datasets")
    print(f"  PREPROC → {PREPROC}")
    print(f"  MERGED  → {MERGED}")
    print(f"  Split   → train={TRAIN_RATIO} val={VAL_RATIO} test={TEST_RATIO}  seed={SEED}")

    for ds_name, weight in DATASET_WEIGHTS.items():
        ds_dir = PREPROC / ds_name
        img_dir = ds_dir / "images"
        lbl_dir = ds_dir / "labels"
        if not img_dir.exists():
            print(f"  [SKIP] {ds_name} — not found in preprocessed/")
            continue

        # Collect all image stems
        img_files = sorted(img_dir.iterdir())
        stems = [f.stem for f in img_files]

        # Split per-dataset (stratified by dataset)
        train_s, val_s, test_s = split_list(stems, TRAIN_RATIO, VAL_RATIO, rng)
        ds_splits = {"train": train_s, "val": val_s, "test": test_s}

        total_anns = 0
        for split, split_stems in ds_splits.items():
            for stem in split_stems:
                # Find image file (could be .jpg or .png)
                img_src = None
                for ext in [".jpg", ".png"]:
                    candidate = img_dir / f"{stem}{ext}"
                    if candidate.exists():
                        img_src = candidate
                        break
                if img_src is None:
                    continue

                lbl_src = lbl_dir / f"{stem}.txt"
                ann_count = count_annotations(lbl_src)

                # Unique stem to avoid collisions across datasets
                unique_stem = f"{ds_name}__{stem}"
                dst_img = MERGED / "images" / split / f"{unique_stem}{img_src.suffix}"
                dst_lbl = MERGED / "labels" / split / f"{unique_stem}.txt"

                # Symlink image, copy label
                if not dst_img.exists():
                    dst_img.symlink_to(img_src.resolve())
                if lbl_src.exists():
                    shutil.copy2(lbl_src, dst_lbl)
                else:
                    dst_lbl.write_text("")

                # Track stats
                cd = class_dist(dst_lbl)
                class_dist_by_split[split] += cd
                split_counts[split] += 1
                total_anns += ann_count
                manifest_rows.append((unique_stem, ds_name, split, ann_count))

        print(f"  [{ds_name}]  {len(stems)} tiles → "
              f"train={len(train_s)}  val={len(val_s)}  test={len(test_s)}  "
              f"(total anns in ds: {total_anns})")

    # Write manifest CSV
    manifest_path = MERGED / "manifest.csv"
    with open(manifest_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stem", "source_dataset", "split", "annotation_count"])
        w.writerows(manifest_rows)

    # Write master dataset.yaml
    dataset_yaml = {
        "path": str(MERGED.resolve()),
        "train": "images/train",
        "val":   "images/val",
        "test":  "images/test",
        "nc":    NC,
        "names": [UNIFIED_NAMES[i] for i in range(NC)],
        "notes": (
            f"Merged from {len(DATASET_WEIGHTS)} preprocessed datasets. "
            f"Split: train={TRAIN_RATIO} / val={VAL_RATIO} / test={TEST_RATIO}. "
            f"Seed={SEED}. See manifest.csv for per-tile provenance."
        ),
    }
    with open(MERGED / "dataset.yaml", "w") as f:
        yaml.dump(dataset_yaml, f, default_flow_style=False, sort_keys=False)

    # ─── Integrity check ─────────────────────────────────────────────────────
    print("\n  Running integrity checks ...")
    errors = []
    for split in ["train", "val", "test"]:
        img_files = set(f.stem for f in (MERGED / "images" / split).iterdir())
        lbl_files = set(f.stem for f in (MERGED / "labels" / split).iterdir())
        imgs_no_lbl = img_files - lbl_files
        lbls_no_img = lbl_files - img_files
        if imgs_no_lbl:
            errors.append(f"  {split}: {len(imgs_no_lbl)} images without labels")
        if lbls_no_img:
            errors.append(f"  {split}: {len(lbls_no_img)} labels without images")
        # Check for corrupt label lines
        corrupt = 0
        for lbl in (MERGED / "labels" / split).iterdir():
            for line in lbl.read_text().strip().splitlines():
                parts = line.split()
                if len(parts) != 5:
                    corrupt += 1
                    continue
                cls = int(parts[0])
                vals = [float(x) for x in parts[1:]]
                if not (0 <= cls < NC and all(0 <= v <= 1 for v in vals)):
                    corrupt += 1
        if corrupt:
            errors.append(f"  {split}: {corrupt} corrupt annotation lines")

    if errors:
        print("  ERRORS:")
        for e in errors:
            print(f"    {e}")
    else:
        print("  All checks passed — no missing files, no corrupt labels.")

    # ─── Final report ────────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("Step 4 Complete — Master dataset summary")
    print("="*65)

    total_all = sum(split_counts.values())
    for split in ["train", "val", "test"]:
        print(f"\n  {split.upper()} — {split_counts[split]} tiles")
        cd = class_dist_by_split[split]
        total_anns = sum(cd.values())
        for cls_id in range(NC):
            name = UNIFIED_NAMES[cls_id]
            count = cd.get(cls_id, 0)
            bar = "█" * min(40, int(40 * count / max(total_anns, 1)))
            print(f"    {name:<18} {count:>8}  {bar}")

    print(f"\n  Total tiles in merged dataset: {total_all}")
    print(f"  Manifest: {manifest_path}")
    print(f"  dataset.yaml: {MERGED / 'dataset.yaml'}")


if __name__ == "__main__":
    main()
