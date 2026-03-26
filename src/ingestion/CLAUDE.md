# Ingestion Pipeline — Session Context

## What this folder does
Automated CLI pipeline that converts scanned P&ID PDFs into structured knowledge graphs
(pid.graph.v0.1.1 JSON). Output feeds directly into the talking-pnids-py chatbot query layer.
This is a batch/offline process — run once per P&ID, not on every query.

## Environment
- Python 3.13 via direnv virtualenv at `/Users/numan/Projects/talking-pnid/.direnv/python-3.13/`
- Key packages: `anthropic`, `pymupdf`, `pillow`, `networkx`
- Anthropic API key required: set `ANTHROPIC_API_KEY` in environment

## Pipeline Steps

```
tile.py        → PDF → 3×2 PNG tiles (15% overlap) + embedded text extraction
extract.py     → tiles + legend context → Claude Opus 4.6 vision → per-tile JSON (3 passes)
stitch.py      → 6 tile JSONs → resolve edges → deduplicate → unified_extraction.json
schema.py      → unified_extraction.json → Claude Sonnet 4.6 → pid.graph.v0.1.1 JSON
validate.py    → graph JSON vs OCR tags → completeness rules → confidence report
supergraph.py  → 3 P&ID graphs → wire off_page_ref nodes → supergraph.json
ingest.py      → CLI orchestrator for all steps
```

## CLI Usage

```bash
cd src/ingestion

# Full pipeline on one P&ID
python ingest.py --pdf ../../data/pdfs/100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf

# All three POC P&IDs
python ingest.py --all

# Single step (for re-runs during tuning)
python ingest.py --pdf ... --step extract
python ingest.py --pdf ... --step stitch
python ingest.py --pdf ... --step schema
python ingest.py --pdf ... --step validate

# Build super graph from existing P&ID graphs
python ingest.py --supergraph
```

## Key Inputs
| Input | Location |
|-------|----------|
| P&ID PDFs | `data/pdfs/` |
| Legend Sheet 1 (abbreviations) | `data/Legends/Format Specific/*-0001-001*.pdf` |
| Legend Sheet 2 (piping symbols) | `data/Legends/Format Specific/*-0001-002*.pdf` |
| OCR tag lists | `data/outputs/ocr/*_tags.json` |
| pid.graph.v0.1.1 schema | `data/archive/extra/prompt.txt` |

## Key Outputs
| Output | Location |
|--------|----------|
| Per-P&ID graph | `src/talking-pnids-py/data/graphs/pid-00X.graph.json` |
| Super graph | `src/talking-pnids-py/data/graphs/supergraph.json` |
| Confidence report | `data/outputs/ingestion/pid-00X_report.json` |
| Intermediate tile JSONs | `data/outputs/ingestion/pid-00X/tiles/` |

## Models
| Step | Model | Why |
|------|-------|-----|
| Tile extraction (3 passes) | claude-opus-4-6 | Vision quality critical |
| Schema conversion | claude-sonnet-4-6 | Structured output, cheaper |
| Self-verification | claude-sonnet-4-6 | Review pass |
| Supergraph wiring | claude-sonnet-4-6 | Logic only, no vision |

## Legend Context (CRITICAL)
Legend sheets must be loaded and passed as system context to EVERY extraction call.
- Sheet 1: defines LO/LC/ILO/NO/NC/FC/FO/FL/HHL/LLLL etc.
- Sheet 2: defines valve symbols, fitting symbols, line types, off-drawing connector format
Without this context the LLM guesses conventions → wrong locked positions, missed alarm levels.

## Extraction Passes (per tile)
1. **Pass 1** — all components + connections (standard extraction)
2. **Pass 2** — targeted: setpoints (HH/H/L/LL with values), locked positions, spec breaks, vessel internals, note references
3. **Pass 3** — self-verification: show model its own output + tile image → "what did you miss?"

## Completeness Validation Rules
- Every vessel must have: design pressure, design temp, op pressure, op temp
- Every PSV must have: set pressure, size code
- Every control loop must have: transmitter + controller + output valve
- Every valve must have: normal position (LO/LC/NO/NC/FO/FC/FL)
- Every spec break must have: two pipe specs + boundary component

## POC Success Criteria
10 sample questions answered correctly against PID-008 via updated chatbot.
See `PLAN.md` for full build plan and `data/archive/extra/prompt.txt` for the schema.
