# P&ID Detection Model — Pre-training Pipeline

## Purpose
Train a YOLOv8 object detection model to recognize P&ID symbols (valves, instruments, pumps, etc.) on industrial engineering diagrams.

## Pipeline Status
Steps 1–6 complete. Step 7 (training) is next.

| Step | Script | Status |
|------|--------|--------|
| 1. Collect datasets | `get_datasets.py` | Done |
| 2. Standardize formats | `step2.py` / `scripts/step2_standardize.py` | Done |
| 3. Preprocess images | `scripts/step3_preprocess.py` | Done |
| 4. Merge datasets | `scripts/step4_merge.py` | Done |
| 5. Augment | `scripts/step5_augment.py` | Done |
| 6. Prepare config | `scripts/step6_prepare_config.py` | Done |
| 7. Train | `scripts/step7_train.py` | Next |

## Key Directories
```
datasets/
  raw/                  # Original downloaded datasets
    azure_pid/
    eng_diagrams/
    kaggle_pid_symbols/ # 30,000 tiles (1280×1280)
    PID2Graph/
  processed/            # Standardized YOLO format
  preprocessed/         # Tiled/resized per-dataset
  merged/               # Master dataset (~95,800 samples, 80/10/10 split)
    images/{train,val,test}/
    labels/{train,val,test}/
    dataset.yaml
    manifest.csv        # per-tile provenance
    best.pt             # saved model checkpoint
  augmented/            # Offline-augmented training data
  class_names.yaml      # Unified 9-class taxonomy

config/
  train_config.yaml     # YOLOv8m training hyperparameters

scripts/                # One script per pipeline step
runs/                   # Training output (Ultralytics format)
```

## Class Taxonomy (9 classes)
```
0: arrow          - flow direction arrows
1: crossing       - pipe crossings (no connection)
2: connector      - tees, junctions
3: valve          - all valve types
4: instrumentation - sensors, transmitters, flow meters
5: pump           - pumps, compressors
6: tank           - vessels, separators
7: general        - misc symbols (reducers, blinds, flanges)
8: inlet_outlet   - boundary connectors
```

## Training Config
- Model: YOLOv8m (pretrained COCO weights)
- Image size: 640×640 tiles
- Batch: 32, Epochs: 100, Optimizer: AdamW
- Device: CUDA GPU 0 (RTX 3090 24GB)
- Config: `config/train_config.yaml`
- Output: `runs/detect/pid_baseline_yolov8m/`

## Real P&ID Input Data
3 annotated real-world P&IDs (Rumaila oil field) stored at:
`/Users/numan/Projects/talking-pnid/data/archive/extra/Talking p&ID/3 related pid/`

Files per P&ID:
- `*_C02.pdf` — original PDF
- `*_annotated.pdf` — annotated version
- `*_tags.json` — instrument tag positions (OCR-detected, normalized coords)
- `*_valves.json` — valve positions (for PID-006 only)

To add these as training data: rasterize PDFs → convert JSON coords to YOLO → tile → merge.

## Running the Pipeline
```bash
cd /Users/numan/Projects/talking-pnid/src/model-pretrain
python get_datasets.py          # Step 1
python step2.py                 # Step 2
python scripts/step3_preprocess.py
python scripts/step4_merge.py
python scripts/step5_augment.py
python scripts/step6_prepare_config.py
python scripts/step7_train.py   # Step 7 — trains model
```

## Notes
- All scripts run from the `model-pretrain/` root directory
- Tile size is 640×640px with 100px overlap (stride=540)
- Blank tiles (>92% white) are filtered out
- `manifest.csv` tracks provenance of every tile in the merged dataset
