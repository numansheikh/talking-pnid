"""
Step 5: Data Augmentation
==========================
Strategy:
  1. P&ID-appropriate augmentation pipeline (albumentations):
       - 90°/180°/270° rotations (valid for engineering symbols)
       - Horizontal + vertical flips (symbols can be mirrored)
       - Modest zoom / scale (±15%)
       - Brightness / contrast shifts (scan quality variation)
       - Gaussian blur + noise (scan degradation)
       - NOT: large arbitrary rotations, heavy color shifts, cutout

  2. General augmentation: every training tile gets 1 additional augmented copy
     (doubles the training set size cheaply).

  3. Minority-class oversampling: tiles containing pump/tank/inlet_outlet
     get extra copies until each minority class reaches a target annotation count.
       - pump:        target 5 000 annotations
       - tank:        target 5 000 annotations
       - inlet_outlet: target 3 000 annotations

Output:
  datasets/augmented/
    images/train/   (originals symlinked + augmented copies as .jpg)
    labels/train/   (originals copied + augmented .txt)
    images/val/     (symlinks from merged — no augmentation on val/test)
    images/test/    (symlinks from merged)
    labels/val/
    labels/test/
    dataset.yaml
    augmentation_report.yaml

Usage:
  python scripts/step5_augment.py
"""

import random
import shutil
import yaml
import cv2
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict

import albumentations as A
from albumentations.core.composition import BboxParams

# ─── Config ──────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.parent
MERGED  = ROOT / "datasets" / "merged"
AUG_OUT = ROOT / "datasets" / "augmented"

SEED = 42
rng  = random.Random(SEED)
np.random.seed(SEED)

# Minority class targets (annotation counts in final augmented train set)
MINORITY_CLASSES  = {5: "pump", 6: "tank", 8: "inlet_outlet"}
MINORITY_TARGETS  = {5: 5000, 6: 5000, 8: 3000}

with open(ROOT / "datasets" / "class_names.yaml") as f:
    CLASS_CFG = yaml.safe_load(f)
UNIFIED_NAMES = CLASS_CFG["names"]
NC = CLASS_CFG["nc"]

# ─── Augmentation pipeline ───────────────────────────────────────────────────

def make_pipeline(seed: int) -> A.Compose:
    """
    P&ID-appropriate augmentation pipeline.
    BboxParams with yolo format handles bbox remapping automatically.
    """
    return A.Compose([
        # Geometry — valid for engineering diagrams
        A.RandomRotate90(p=0.6),
        A.HorizontalFlip(p=0.4),
        A.VerticalFlip(p=0.3),
        A.ShiftScaleRotate(
            shift_limit=0.03,
            scale_limit=0.15,
            rotate_limit=0,        # no arbitrary rotation
            border_mode=cv2.BORDER_CONSTANT,
            value=255,             # pad with white
            p=0.4,
        ),
        # Photometric — scan quality variation
        A.RandomBrightnessContrast(brightness_limit=0.15, contrast_limit=0.15, p=0.5),
        A.GaussianBlur(blur_limit=(3, 5), p=0.2),
        A.GaussNoise(std_range=(0.01, 0.05), p=0.2),
        A.ImageCompression(quality_range=(75, 95), p=0.2),
    ],
    bbox_params=BboxParams(
        format="yolo",
        label_fields=["class_labels"],
        min_visibility=0.25,    # drop bbox if <25% remains after transform
        clip=True,
    ),
    seed=seed)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def make_symlink(src: Path, dst: Path):
    if not dst.exists():
        dst.symlink_to(src.resolve())


def read_yolo(lbl_path: Path):
    """Returns (class_labels list, bboxes list of [cx,cy,bw,bh])."""
    classes, bboxes = [], []
    if lbl_path.exists() and lbl_path.stat().st_size > 0:
        for line in lbl_path.read_text().strip().splitlines():
            parts = line.split()
            if len(parts) == 5:
                classes.append(int(parts[0]))
                bboxes.append([float(x) for x in parts[1:]])
    return classes, bboxes


def write_yolo(lbl_path: Path, classes, bboxes):
    lines = [f"{int(float(c))} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"
             for c, (cx, cy, bw, bh) in zip(classes, bboxes)]
    lbl_path.write_text("\n".join(lines))


def augment_one(img_path: Path, lbl_path: Path,
                out_img: Path, out_lbl: Path,
                pipeline: A.Compose) -> bool:
    """
    Apply pipeline to one image+label pair.
    Writes output files. Returns True on success.
    """
    img = cv2.imread(str(img_path))
    if img is None:
        return False
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    classes, bboxes = read_yolo(lbl_path)

    try:
        result = pipeline(image=img_rgb, bboxes=bboxes, class_labels=classes)
    except Exception:
        return False

    aug_img   = result["image"]
    aug_bboxes = result["bboxes"]
    aug_cls   = result["class_labels"]

    # Save image
    out_bgr = cv2.cvtColor(aug_img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_img), out_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])

    # Save label
    write_yolo(out_lbl, aug_cls, aug_bboxes)
    return True


def count_class_anns(lbl_dir: Path, cls_id: int) -> int:
    total = 0
    for f in lbl_dir.glob("*.txt"):
        for line in f.read_text().strip().splitlines():
            parts = line.split()
            if parts and int(float(parts[0])) == cls_id:
                total += 1
    return total


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("Step 5: Data Augmentation")
    print(f"  MERGED  → {MERGED}")
    print(f"  AUG_OUT → {AUG_OUT}")

    src_img_train = MERGED / "images" / "train"
    src_lbl_train = MERGED / "labels" / "train"

    out_img_train = ensure_dir(AUG_OUT / "images" / "train")
    out_lbl_train = ensure_dir(AUG_OUT / "labels" / "train")

    # Val and test: just symlink — no augmentation
    for split in ["val", "test"]:
        out_img = ensure_dir(AUG_OUT / "images" / split)
        out_lbl = ensure_dir(AUG_OUT / "labels" / split)
        for f in (MERGED / "images" / split).iterdir():
            make_symlink(f, out_img / f.name)
        for f in (MERGED / "labels" / split).iterdir():
            lbl_dst = out_lbl / f.name
            if not lbl_dst.exists():
                shutil.copy2(f, lbl_dst)

    # ── Step 1: symlink all original train images + copy labels ──────────────
    print("\n  [1/3] Linking original training tiles ...")
    train_imgs = sorted(src_img_train.iterdir())
    for img in train_imgs:
        make_symlink(img, out_img_train / img.name)
        lbl_src = src_lbl_train / f"{img.stem}.txt"
        lbl_dst = out_lbl_train / f"{img.stem}.txt"
        if not lbl_dst.exists():
            if lbl_src.exists():
                shutil.copy2(lbl_src, lbl_dst)
            else:
                lbl_dst.write_text("")
    print(f"    {len(train_imgs)} original tiles linked")

    # ── Step 2: general augmentation — 1 extra copy per tile ─────────────────
    print("\n  [2/3] General augmentation (1× extra copy per training tile) ...")
    pipeline = make_pipeline(SEED)
    gen_ok = gen_fail = 0

    for img_src in train_imgs:
        stem = img_src.stem
        lbl_src = src_lbl_train / f"{stem}.txt"

        aug_stem = f"aug1__{stem}"
        out_img  = out_img_train / f"{aug_stem}.jpg"
        out_lbl  = out_lbl_train / f"{aug_stem}.txt"

        if out_img.exists():
            gen_ok += 1
            continue

        ok = augment_one(img_src, lbl_src, out_img, out_lbl, pipeline)
        if ok:
            gen_ok += 1
        else:
            gen_fail += 1

    print(f"    {gen_ok} augmented, {gen_fail} failed")

    # ── Step 3: minority class oversampling ───────────────────────────────────
    print("\n  [3/3] Minority class oversampling ...")

    # Find tiles that contain each minority class
    minority_tile_pool = defaultdict(list)
    for lbl in src_lbl_train.glob("*.txt"):
        classes_in = set()
        for line in lbl.read_text().strip().splitlines():
            cls = int(line.split()[0])
            if cls in MINORITY_CLASSES:
                classes_in.add(cls)
        for cls in classes_in:
            minority_tile_pool[cls].append(lbl.stem)

    for cls_id, cls_name in MINORITY_CLASSES.items():
        target = MINORITY_TARGETS[cls_id]
        current = count_class_anns(out_lbl_train, cls_id)
        pool    = minority_tile_pool[cls_id]

        print(f"\n    {cls_name} (cls {cls_id}): current={current}, target={target}, "
              f"pool={len(pool)} tiles")

        copy_idx = 0
        attempts = 0
        max_attempts = (target - current) * 5  # safety limit

        while current < target and pool and attempts < max_attempts:
            stem = rng.choice(pool)
            img_src = None
            for ext in [".jpg", ".png"]:
                c = src_img_train / f"{stem}{ext}"
                if c.exists():
                    img_src = c
                    break
            if img_src is None:
                attempts += 1
                continue

            lbl_src  = src_lbl_train / f"{stem}.txt"
            aug_stem = f"minority_{cls_name}_{copy_idx:05d}__{stem}"
            out_img  = out_img_train / f"{aug_stem}.jpg"
            out_lbl  = out_lbl_train / f"{aug_stem}.txt"

            pipe = make_pipeline(SEED + copy_idx)
            ok = augment_one(img_src, lbl_src, out_img, out_lbl, pipe)
            if ok:
                added = sum(1 for l in out_lbl.read_text().strip().splitlines()
                            if int(l.split()[0]) == cls_id)
                current += added
                copy_idx += 1
            attempts += 1

        final = count_class_anns(out_lbl_train, cls_id)
        print(f"    {cls_name}: {final} annotations after oversampling "
              f"({copy_idx} extra tiles generated)")

    # ── dataset.yaml ─────────────────────────────────────────────────────────
    dataset_yaml = {
        "path":  str(AUG_OUT.resolve()),
        "train": "images/train",
        "val":   "images/val",
        "test":  "images/test",
        "nc":    NC,
        "names": [UNIFIED_NAMES[i] for i in range(NC)],
        "notes": (
            "Augmented training set. Val/test are unchanged from merged/. "
            "General aug: 1× extra copy per tile (random rotate90, flip, scale, "
            "brightness, blur, noise). Minority oversampling: pump/tank/inlet_outlet "
            "boosted to target annotation counts."
        ),
    }
    with open(AUG_OUT / "dataset.yaml", "w") as f:
        yaml.dump(dataset_yaml, f, default_flow_style=False, sort_keys=False)

    # ── Final report ──────────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("Step 5 Complete — Augmented dataset summary")
    print("="*65)

    total_ann_train = Counter()
    for lbl in out_lbl_train.glob("*.txt"):
        for line in lbl.read_text().strip().splitlines():
            total_ann_train[int(line.split()[0])] += 1

    total_imgs = len(list(out_img_train.iterdir()))
    print(f"\n  Train images (orig + augmented): {total_imgs}")
    print(f"  Val images:  {len(list((AUG_OUT/'images'/'val').iterdir()))}")
    print(f"  Test images: {len(list((AUG_OUT/'images'/'test').iterdir()))}")
    print(f"\n  Train class distribution:")
    for cls_id in range(NC):
        name  = UNIFIED_NAMES[cls_id]
        count = total_ann_train.get(cls_id, 0)
        bar   = "█" * min(40, int(40 * count / max(total_ann_train.values(), 1)))
        print(f"    {name:<18} {count:>8}  {bar}")

    # Save augmentation report
    report = {
        "train_tiles_original": len(train_imgs),
        "train_tiles_after_augmentation": total_imgs,
        "val_tiles": len(list((AUG_OUT / "images" / "val").iterdir())),
        "test_tiles": len(list((AUG_OUT / "images" / "test").iterdir())),
        "class_distribution_train": {
            UNIFIED_NAMES[i]: int(total_ann_train.get(i, 0)) for i in range(NC)
        },
    }
    with open(AUG_OUT / "augmentation_report.yaml", "w") as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False)

    print(f"\n  Report saved: {AUG_OUT / 'augmentation_report.yaml'}")


if __name__ == "__main__":
    main()
