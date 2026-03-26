# P&ID Graph Analyzer — Session Context

## What this folder does
Builds structured graph representations of P&ID topology from OCR/detection outputs. Generates interactive visualizations using NetworkX + Pyvis.

## Environment
- Python 3.13 via direnv virtualenv at `/Users/numan/Projects/talking-pnid/.direnv/python-3.13/`
- Key packages: `networkx`, `pyvis`

## Key Files

```
pnid-analyze/
├── build_graph.py              # Main graph construction + visualization
├── unified_pid_graph.json      # Component + pipe data (29 KB)
├── unified_pid_graph_clean.json # Enriched with inferred connections (37 KB)
├── pid_graph.html              # Interactive visualization (open in browser)
├── comprehensive_pid_summary.md # 1500+ line manual equipment specification
├── comparison_analysis.md      # Methodology notes
├── tiles/                      # 6 tiled sections (JSON + HTML per tile)
└── lib/                        # vis.js, tom-select (external libraries)
```

## Data Source
Based on PID-0008 (Fuel Gas KO Drum PP01-362-V001). Contains:
- 1 main vessel (PP01-362-V001)
- 52 HV (hand valve) components
- 2 PSVs (pressure safety valves)
- 10 pressure instruments, 15 level instruments, 8 others
- 2 logic/voting blocks, 8 reducers, 2 spectacle blinds
- 22+ named pipe lines with specs

## Running

```bash
cd src/pnid-analyze
python3 build_graph.py
# Generates pid_graph.html — open in browser for interactive view
```

## Graph Structure
- **Nodes:** equipment components (vessels, valves, instruments, pipes)
- **Edges:** connections/piping between components
- **Inferred nodes:** boundary nodes for cross-drawing connections (marked explicitly)
- **Inferred edges:** connections deduced from context (marked for manual verification)

## TODO
- Build graphs for PID-006 and PID-007
- Link graph data to web app for topology-aware Q&A
- Validate inferred connections against actual P&ID drawings
