# Talking P&IDs — Root CLAUDE.md

> AI-powered Q&A and analysis system for industrial Piping & Instrumentation Diagrams (P&IDs).
> Real data: Rumaila Oil Field early power plant (contract 100478), 3 P&ID documents.

---

## Repo Structure

```
talking-pnid/
├── src/
│   ├── talking-pnids-py/      # Full-stack web app (backend + frontend) — DEPLOYED
│   ├── extractor/             # OCR tag extraction pipeline — standalone Python
│   ├── pnid-analyze/          # Graph analysis + NetworkX visualization
│   └── model-pretrain/        # YOLOv8 symbol detection training pipeline
├── data/
│   ├── sources/               # Source P&ID PDFs
│   ├── outputs/               # OCR/YOLO extraction results
│   ├── POC/                   # Proof-of-concept data
│   └── Talking PNID Extra/    # Business docs, extra samples, LLM-generated diagrams
├── notebooks/                 # Jupyter exploratory analysis
├── models/                    # Model directory (placeholder)
├── runs/                      # Training run outputs
├── start.sh                   # Starts both backend + frontend locally
└── pyproject.toml             # Python project config
```

---

## Components Overview

| Component | Location | Status | Purpose |
|-----------|----------|--------|---------|
| Web App (backend) | `src/talking-pnids-py/backend/` | Live on Koyeb | FastAPI, graph agent Q&A, PDF serving |
| Web App (frontend) | `src/talking-pnids-py/frontend/` | Live on Vercel | React UI, chat, PDF viewer |
| Ingestion Pipeline | `src/ingestion/` | Done (pid-008), partial (006/007) | PDF → tiles → Claude Vision → graph JSON |
| OCR Extractor | `src/extractor/` | Working | Extract tags from scanned P&IDs |
| YOLO Trainer | `src/model-pretrain/` | Steps 1-6 done | Train symbol detector |
| Graph Analyzer | `src/pnid-analyze/` | Working | Build topology graph from extractions |

> Each component has its own CLAUDE.md with detailed context. See those first when working in a subfolder.

---

## Real P&ID Data

Three Rumaila Oil Field P&IDs (scanned raster PDFs):

| Doc ID | Filename | System |
|--------|----------|--------|
| PID-0006 | `100478CP-N-PG-PP01-PR-PID-0006-001-C02.pdf` | Scraper Launcher DS-3, system 361 |
| PID-0007 | `100478CP-N-PG-PP01-PR-PID-0007-001-C02.pdf` | System 361 related |
| PID-0008 | `100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf` | Fuel Gas KO Drum PP01-362-V001 |

PDFs live in `data/datasets/rumaila-pp01/pdfs/` (A3 originals with title block). Web app has its own copy at `src/talking-pnids-py/data/pdfs/`.
A fourth PDF (`PID-0005`) exists in `data/Talking PNID Extra/Tech Ventures/` but is not yet processed.

---

## Deployment

| Service | URL | Platform |
|---------|-----|----------|
| Backend | https://decent-lilli-cogit-0d306da3.koyeb.app | Koyeb |
| Frontend | https://talking-pnid.vercel.app/app | Vercel |

Local dev: `npm install && npm start` from `src/talking-pnids-py/` (or run `start.sh` from root).
Backend runs on port 8000, frontend on port 3000.

---

## Python Environment

- Python 3.13 via direnv virtualenv at `.direnv/python-3.13/`
- Run scripts with `python3` from the relevant subfolder
- Key packages: `pymupdf`, `pytesseract`, `pillow`, `ultralytics`, `networkx`, `pyvis`, `fastapi`, `openai`, `langchain`

---

## Benchmark

10 engineering questions against PID-008, judged by GPT-4o. See `src/talking-pnids-py/tests/BENCHMARK.md` for full details.

| Date | Strategy | Avg | P/P/F | Notes |
|------|----------|-----|-------|-------|
| 2026-03-27 | v0.1.0 | 74 | 2/5/3 | Initial graph query layer |
| 2026-03-28 | v0.1.1+pass2 | **79** | **5/4/1** | Pass2 re-run + agent prompt fixes |

Run: `python tests/run_benchmark.py` from `src/talking-pnids-py/` (backend must be up on port 8050).

---

## Open Work (High Level)

1. **Fix Q8 spectacle blinds** — HV0027/HV0050 in pid-008 graph need correct subtype
2. **Re-run pass2 for pid-006 and pid-007** — currently empty (0 components)
3. **YOLO Training (Step 7)** — pipeline ready, ~95.8k samples, needs RTX 3090
4. **Extractor improvements** — DPI 400, split tag handling
5. **Session persistence** — currently in-memory only

---

## Key Decisions & Constraints

- **No embedded text in PDFs** — all P&IDs are scanned rasters; OCR is the only extraction path
- **Multi-rotation OCR** — renders at 0°/90°/270° to catch vertical text labels
- **Reasoning model routing** — gpt-4/gpt-4o use LangChain; o1/o3/gpt-5.x use direct OpenAI API
- **Config priority** — env vars override config.json, which overrides defaults (safe for cloud deploy)
- **Session history** — in-memory dict keyed by sessionId; one instance only
- **Currently loaded in web app** — only PID-008 (006 and 007 disabled in file-mappings.json)
- **Auth** — hardcoded login gate: username `pnid`, password `pakistan` (sessionStorage, frontend only)
