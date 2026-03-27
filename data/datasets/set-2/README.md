# Dataset: set-2 — DigitizePID YOLO Training Dataset

**Purpose:** External P&ID symbol detection dataset for training the YOLO symbol detector (`src/model-pretrain/`)
**Archive:** `data/archive/extra/TechVenture/DigitizePID_Dataset-20260109T142718Z-1-001.zip` (939MB)
**Status:** Available, not yet extracted/used

Also in this folder:
- `data/archive/extra/TechVenture/pid-final-document.pdf` (3.7MB) — reference P&ID document

## To use

```bash
cd data/archive/extra/TechVenture
unzip DigitizePID_Dataset-20260109T142718Z-1-001.zip -d ../../datasets/set-2/
```

Add extracted contents to `.gitignore` (too large for git).
