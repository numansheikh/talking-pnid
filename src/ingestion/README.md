# P&ID Ingestion Pipeline

Automated CLI pipeline that converts scanned P&ID PDFs into structured knowledge graphs for the Talking P&IDs chatbot.

## What it does

```
PDF → tile → extract (Claude Vision) → stitch → schema → validate → graph JSON
```

Outputs `pid.graph.v0.1.1` JSON consumed by the chatbot query layer — replacing unreliable markdown context injection with precise structured data.

## Quick Start

```bash
cd src/ingestion

# Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# Run full pipeline on PID-008
python ingest.py --pdf ../../data/pdfs/100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf

# Run all three POC P&IDs
python ingest.py --all

# Build super graph after all three are done
python ingest.py --supergraph
```

## Pipeline Steps

| Script | Input | Output |
|--------|-------|--------|
| `tile.py` | PDF | 6 PNG tiles + embedded text |
| `extract.py` | Tiles + legend context | Per-tile JSON (3 passes) |
| `stitch.py` | 6 tile JSONs | Unified extraction JSON |
| `schema.py` | Unified extraction | pid.graph.v0.1.1 JSON |
| `validate.py` | Graph + OCR tags | Confidence report |
| `supergraph.py` | 3 P&ID graphs | Cross-P&ID super graph |

## Outputs

- `src/talking-pnids-py/data/graphs/pid-006.graph.json`
- `src/talking-pnids-py/data/graphs/pid-007.graph.json`
- `src/talking-pnids-py/data/graphs/pid-008.graph.json`
- `src/talking-pnids-py/data/graphs/supergraph.json`
- `data/outputs/ingestion/pid-00X_report.json` — confidence + flagged gaps
