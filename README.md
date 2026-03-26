# Talking P&IDs

AI-powered assistant for industrial Piping & Instrumentation Diagrams (P&IDs). Ask questions about plant equipment, processes, and instrumentation in natural language while viewing the actual diagrams.

**Live app:** https://talking-pnid.vercel.app/app

---

## What it does

- View P&ID drawings (PDF) alongside an AI chat interface
- Ask questions like "What valves control flow to the knockout drum?" or "Where is PSV-0001 located?"
- AI references specific diagrams with clickable cross-links
- Comprehensive context from engineering documentation fed into each query

## Data

Three real Piping & Instrumentation Diagrams from the Rumaila Oil Field (Iraq) early power plant, contract 100478:

| Diagram | System |
|---------|--------|
| PID-0006 | Scraper Launcher DS-3, system 361 |
| PID-0007 | System 361 (fuel gas distribution) |
| PID-0008 | Fuel Gas Knockout Drum PP01-362-V001 |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Web Application                          │
│                                                                  │
│  React + TypeScript (Vercel)  <->  FastAPI + OpenAI (Koyeb)     │
│  3-panel: files | PDF viewer | chat                              │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       Processing Pipeline                        │
│                                                                  │
│  P&ID PDFs -> OCR Extractor -> Tag JSON + Annotated PDFs        │
│           -> YOLO Detector -> Symbol Detection JSON             │
│           -> Graph Builder -> NetworkX topology + HTML viz      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                        ML Training                               │
│                                                                  │
│  Multi-dataset (Azure + Kaggle + PID2Graph) -> YOLOv8m          │
│  ~95,800 merged samples -> symbol detection model               │
└──────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Location | Description |
|-----------|----------|-------------|
| Web App | `src/talking-pnids-py/` | FastAPI backend + React frontend |
| OCR Extractor | `src/extractor/` | Extract instrument/valve tags from scanned PDFs |
| YOLO Trainer | `src/model-pretrain/` | Train symbol detection model (YOLOv8m) |
| Graph Analyzer | `src/pnid-analyze/` | Build topology graph from extracted data |

---

## Quick Start (Local Dev)

```bash
# Install frontend dependencies and start both services
cd src/talking-pnids-py
npm install
npm start
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

Requires: `OPENAI_API_KEY` in `src/talking-pnids-py/backend/.env` or as environment variable.

---

## OCR Extraction

```bash
cd src/extractor
python3 pid_extractor.py ../../data/sources/pdf/100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf \
  --output ../../data/outputs/ocr/pid-008_tags.json \
  --dpi 300
```

---

## YOLO Training

```bash
cd src/model-pretrain
# Steps 1-6 already done. Run step 7 to train:
python scripts/step7_train.py
# Requires: CUDA GPU (RTX 3090 recommended)
```

---

## Deployment

| Service | Platform | Config |
|---------|----------|--------|
| Backend | Koyeb | `src/talking-pnids-py/backend/` — env vars for API key + paths |
| Frontend | Vercel | `src/talking-pnids-py/frontend/` — `VITE_API_BASE_URL` env var |

---

## Tech Stack

- **Backend:** Python 3.13, FastAPI, LangChain, OpenAI API
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, react-markdown
- **OCR:** PyMuPDF, Tesseract, Pillow
- **ML:** Ultralytics YOLOv8, PyTorch
- **Graph:** NetworkX, Pyvis
- **Deploy:** Koyeb (backend), Vercel (frontend)
