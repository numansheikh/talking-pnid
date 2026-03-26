"""
Export 5 cropped sample images per class (45 total) into a single folder.
Crops the bounding box with padding so context is visible.
"""

import random
from pathlib import Path
from PIL import Image, ImageDraw

ROOT    = Path(__file__).parent.parent
PREPROC = ROOT / "datasets" / "preprocessed"
OUT_DIR = ROOT / "samples"
OUT_DIR.mkdir(exist_ok=True)

CLASSES = {
    0: "arrow",
    1: "crossing",
    2: "connector",
    3: "valve",
    4: "instrumentation",
    5: "pump",
    6: "tank",
    7: "general",
    8: "inlet_outlet",
}

SAMPLES_PER_CLASS = 5
PAD_FACTOR = 1.5   # crop = bbox + 150% padding on each side
MIN_CROP   = 128   # minimum output crop size (px)
OUT_SIZE   = 512   # resize final crop to this square
SEED       = 7

random.seed(SEED)

# ── Collect all (image_path, bbox, cls) tuples per class ─────────────────────
candidates = {cls_id: [] for cls_id in CLASSES}

for ds_dir in sorted(PREPROC.iterdir()):
    if not ds_dir.is_dir():
        continue
    lbl_dir = ds_dir / "labels"
    img_dir = ds_dir / "images"
    if not lbl_dir.exists():
        continue

    for lbl_file in lbl_dir.glob("*.txt"):
        content = lbl_file.read_text().strip()
        if not content:
            continue
        # Find matching image
        img_path = None
        for ext in [".jpg", ".png"]:
            p = img_dir / f"{lbl_file.stem}{ext}"
            if p.exists():
                img_path = p
                break
        if not img_path:
            continue

        for line in content.splitlines():
            parts = line.split()
            if len(parts) != 5:
                continue
            cls_id = int(float(parts[0]))
            if cls_id not in candidates:
                continue
            cx, cy, bw, bh = [float(x) for x in parts[1:]]
            # skip very tiny boxes (crossings on full-size images)
            if bw < 0.01 or bh < 0.01:
                continue
            candidates[cls_id].append((img_path, cx, cy, bw, bh))

# ── Crop and save ─────────────────────────────────────────────────────────────
def crop_symbol(img_path: Path, cx, cy, bw, bh) -> Image.Image:
    img = Image.open(img_path).convert("RGB")
    W, H = img.size

    # bbox in pixels
    bx = cx * W;  by = cy * H
    bw_px = bw * W;  bh_px = bh * H

    pad_x = bw_px * PAD_FACTOR
    pad_y = bh_px * PAD_FACTOR

    x0 = max(0, int(bx - bw_px/2 - pad_x))
    y0 = max(0, int(by - bh_px/2 - pad_y))
    x1 = min(W, int(bx + bw_px/2 + pad_x))
    y1 = min(H, int(by + bh_px/2 + pad_y))

    # Ensure minimum crop size
    if (x1 - x0) < MIN_CROP:
        cx_mid = (x0 + x1) // 2
        x0 = max(0, cx_mid - MIN_CROP // 2)
        x1 = min(W, cx_mid + MIN_CROP // 2)
    if (y1 - y0) < MIN_CROP:
        cy_mid = (y0 + y1) // 2
        y0 = max(0, cy_mid - MIN_CROP // 2)
        y1 = min(H, cy_mid + MIN_CROP // 2)

    crop = img.crop((x0, y0, x1, y1))
    crop = crop.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)
    return crop


print(f"Exporting {SAMPLES_PER_CLASS} samples × {len(CLASSES)} classes → {OUT_DIR}")
print()

for cls_id, cls_name in CLASSES.items():
    pool = candidates[cls_id]
    if not pool:
        print(f"  {cls_name}: NO SAMPLES FOUND")
        continue

    # Shuffle and pick diverse samples
    random.shuffle(pool)
    saved = 0
    seen_images = set()

    for img_path, cx, cy, bw, bh in pool:
        if saved >= SAMPLES_PER_CLASS:
            break
        # Prefer different source images for variety
        if img_path in seen_images and len(seen_images) < len(pool) // 2:
            continue
        try:
            crop = crop_symbol(img_path, cx, cy, bw, bh)
            out_name = f"{cls_name}-{saved+1:02d}.png"
            crop.save(OUT_DIR / out_name)
            seen_images.add(img_path)
            saved += 1
        except Exception as e:
            continue

    print(f"  {cls_name:<18} {saved} samples saved")

print(f"\nDone. All samples in: {OUT_DIR}")
print(f"Files: {sorted(f.name for f in OUT_DIR.glob('*.png'))}")
