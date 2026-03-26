# Ingestion Pipeline — Build Plan
> Updated: 2026-03-26

## Goal
Automatically convert scanned P&ID PDFs into a structured knowledge graph (pid.graph.v0.1.1 JSON)
that the chatbot can query reliably — replacing the current markdown-based context injection.

---

## Input
| Input | Location | Notes |
|-------|----------|-------|
| P&ID PDFs | `data/pdfs/` | Scanned rasters, 2-page (original + raster) |
| Legend Sheet 1 | `data/Legends/Format Specific/...-0001-001...pdf` | Abbreviations |
| Legend Sheet 2 | `data/Legends/Format Specific/...-0001-002...pdf` | Piping symbols |
| OCR tag list | `data/outputs/ocr/*_tags.json` | Cross-validation source |

## Output
| Output | Location |
|--------|----------|
| Per-P&ID graph | `src/talking-pnids-py/data/graphs/pid-00X.graph.json` |
| Super graph | `src/talking-pnids-py/data/graphs/supergraph.json` |
| Confidence report | `data/outputs/ingestion/pid-00X_report.json` |

---

## Architecture

```
Step 1 — tile.py
    PDF page 2 (raster) → 3×2 grid PNG tiles (15% overlap)
    Also extract embedded text from page 1 (PyMuPDF)

Step 2 — extract.py
    Legend sheets → project context (loaded once)
    Per tile: image + legend context + embedded text → Claude Opus 4.6 (vision)
    Pass 1: components + connections
    Pass 2: targeted hunt — setpoints, locked positions, spec breaks, vessel internals, notes
    Pass 3: self-verification — "what did I miss?"
    Output: per-tile JSON (r1c1...r2c3)

Step 3 — stitch.py
    6 tile JSONs → resolve edge components → deduplicate overlap zones
    Output: unified_extraction.json

Step 4 — schema.py
    unified_extraction.json → Claude Sonnet 4.6
    Prompt: convert to pid.graph.v0.1.1 schema
    Output: pid-00X.graph.json

Step 5 — validate.py
    pid-00X.graph.json vs OCR _tags.json
    Completeness rules check:
      - Every vessel has design/op pressure + temp
      - Every PSV has set pressure + size
      - Every control loop has transmitter + controller + output valve
      - Every valve has normal position (LO/LC/NO/NC/FO/FC)
      - Every spec break has two pipe specs + boundary component
    Output: pid-00X_report.json (confidence scores + flagged gaps)

Step 6 — supergraph.py
    All 3 pid-00X.graph.json files
    Wire off_page_ref terminator nodes across P&IDs
    Output: supergraph.json
```

---

## Models

| Step | Model | Reason |
|------|-------|--------|
| tile extraction (3 passes) | claude-opus-4-6 | Vision quality critical |
| schema conversion | claude-sonnet-4-6 | Structured output, cheaper |
| self-verification | claude-sonnet-4-6 | Review pass, cheaper |
| supergraph wiring | claude-sonnet-4-6 | Logic only, no vision |

---

## CLI Interface

```bash
# Single P&ID — full pipeline
python ingest.py --pdf data/pdfs/100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf

# All three POC P&IDs
python ingest.py --all

# Specific step only (for re-runs during tuning)
python ingest.py --pdf ... --step extract
python ingest.py --pdf ... --step stitch
python ingest.py --pdf ... --step schema
python ingest.py --pdf ... --step validate

# Build super graph from existing P&ID graphs
python ingest.py --supergraph
```

---

## Chatbot Integration (minimal changes)

1. `file-mappings.json` — add `"graph"` field per entry
2. `backend/api/query.py` — add graph query function:
   - Parse question intent
   - Query graph for relevant nodes/edges
   - Inject targeted data into LLM prompt (not full markdown)
   - Markdown stays as fallback for narrative questions
3. Query model routing:
   - Topology/reasoning (Q2, Q3, Q4) → claude-opus-4-6 or o3
   - Standard Q&A (Q1, Q7, Q9) → claude-sonnet-4-6 or gpt-4o
   - Simple lookups (Q5, Q6, Q8) → claude-haiku-4-5

---

## Build Order

1. `tile.py` — PDF tiling + embedded text extraction
2. `extract.py` — Claude vision calls with legend context
3. `stitch.py` — merge/dedup tile JSONs
4. `schema.py` — schema conversion
5. `validate.py` — completeness checks + OCR cross-reference
6. `supergraph.py` — cross-P&ID wiring
7. `ingest.py` — CLI orchestrator
8. Chatbot query layer update

---

## POC Success Criteria
Run the 10 sample questions against PID-008 via the updated chatbot.
Target: all 10 answered correctly and completely.
Current baseline: ~5-6/10 partially correct.

## Legend Context (fed to every extraction call)
- Abbreviations sheet: LO, LC, ILO, NO, NC, FC, FO, FL, HHL, LLLL etc.
- Symbols sheet: valve types, fitting types, line types, off-drawing connector format
- Loaded once at pipeline start, passed as system context to every Claude call
