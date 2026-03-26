import os
import shutil
import json
from pathlib import Path

# -------------------------------
# CONFIGURATION
# -------------------------------
RAW_DIR = Path("datasets/raw")
PROCESSED_DIR = Path("datasets/processed")
CLASS_MAP = {
    # normalize class labels across datasets
    "Pump": "pump",
    "Valve": "valve",
    "Pipe": "pipe",
    "Tank": "tank",
    "Motor": "motor",
    # Add other known class normalizations here
}
VALID_IMAGE_EXTS = [".jpg", ".jpeg", ".png"]
VALID_LABEL_EXTS = [".txt"]  # YOLO format

# Create processed directories
(PROCESSED_DIR / "images").mkdir(parents=True, exist_ok=True)
(PROCESSED_DIR / "labels").mkdir(parents=True, exist_ok=True)

# Log corrupt or skipped files
corrupt_log = []

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------
def normalize_class_label(label):
    return CLASS_MAP.get(label.strip(), label.strip().lower())

def process_yolo_label_file(label_path, dest_label_path):
    """
    Reads a YOLO label file, normalizes class names, and writes to destination.
    """
    try:
        with open(label_path, "r") as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) < 5:
                # invalid line
                continue
            class_id = parts[0]
            # Optionally normalize class names if you have mapping from id to name
            # For now we just keep numeric class_id
            new_lines.append(" ".join(parts))
        if new_lines:
            with open(dest_label_path, "w") as f:
                f.write("\n".join(new_lines))
        else:
            corrupt_log.append(str(label_path))
    except Exception as e:
        corrupt_log.append(str(label_path) + f" | {e}")

def copy_image(src_image_path, dest_image_path):
    try:
        shutil.copy2(src_image_path, dest_image_path)
    except Exception as e:
        corrupt_log.append(str(src_image_path) + f" | {e}")

# -------------------------------
# PROCESS RAW DATASETS
# -------------------------------
for dataset_folder in RAW_DIR.iterdir():
    if dataset_folder.is_dir():
        # Look for YOLO-style datasets first
        images_dir = dataset_folder / "images"
        labels_dir = dataset_folder / "labels"
        if images_dir.exists() and labels_dir.exists():
            print(f"Processing YOLO dataset: {dataset_folder.name}")
            for img_file in images_dir.iterdir():
                if img_file.suffix.lower() in VALID_IMAGE_EXTS:
                    # Corresponding label file
                    label_file = labels_dir / (img_file.stem + ".txt")
                    dest_img_path = PROCESSED_DIR / "images" / img_file.name
                    dest_label_path = PROCESSED_DIR / "labels" / (img_file.stem + ".txt")
                    copy_image(img_file, dest_img_path)
                    if label_file.exists():
                        process_yolo_label_file(label_file, dest_label_path)
                    else:
                        corrupt_log.append(f"No label for image: {img_file}")
        else:
            # Other datasets (e.g., PID2Graph .graphml) will need custom conversion later
            print(f"Skipping non-YOLO dataset for now: {dataset_folder.name}")

# -------------------------------
# WRITE LOG
# -------------------------------
with open(PROCESSED_DIR / "corrupt_files.log", "w") as f:
    for entry in corrupt_log:
        f.write(entry + "\n")

print("Step 2 (Standardize Dataset Formats) completed for YOLO datasets.")
print(f"Processed images and labels stored in: {PROCESSED_DIR}")
print(f"Corrupt or missing files logged in: {PROCESSED_DIR / 'corrupt_files.log'}")