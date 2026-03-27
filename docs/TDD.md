# Talking P&IDs — Technical Design Document

> Version: 0.3 (post-ingestion, pre-RAG)
> Updated: 2026-03-27
> Author: Built with Claude Code (claude-sonnet-4-6)

---

## 1. Overview

Talking P&IDs is an AI-powered Q&A system for industrial Piping & Instrumentation Diagrams.
Process and field engineers upload or select P&ID diagrams and ask natural-language questions.
The system answers using structured knowledge graphs extracted from the diagrams.

**Real dataset:** Rumaila Oil Field early power plant (Iraq, contract 100478). 3 P&IDs covering
scraper launchers and fuel gas KO drum systems.

---

## 2. System Architecture

### 2.1 Current State (v0.2 — Markdown Context)

```
User query
    → FastAPI backend
    → load all markdown docs into system prompt
    → OpenAI GPT (gpt-4 / gpt-5.x)
    → return text answer
```

Limitation: markdown is flat text. LLM hallucinates connections, misses alarm levels,
can't traverse topology. ~5-6/10 benchmark questions answered correctly.

### 2.2 Target State (v0.3 — Graph + RAG)

```
User query + selected P&ID
    ├── Graph Agent (structural questions)
    │   → load pid-00X.graph.json + supergraph.json
    │   → LLM uses tool_use: get_node, find_path, impact_region, list_nodes
    │   → structured answer with exact node/edge data
    │
    └── RAG Agent (narrative questions)
        → filter FAISS index by P&ID ID tag
        → top-k chunk retrieval
        → inject as context
        → prose answer from engineering notes

Combined answer with source callout:
    "This answer uses: [graph: 3 nodes] [notes: 2 passages]"
```

---

## 3. Data Pipeline (Ingestion)

### 3.1 Flow

```
P&ID PDF (scanned raster A3, ~3300×2330px native)
    │
    ▼ tile.py
    Extract native embedded image (no re-render — preserves resolution)
    Split into 3×2 grid with 15% overlap → 6 PNG tiles (~1400×1340px)
    Extract title block text (drawing title, system name, revision)
    │
    ▼ extract.py (18 API calls per P&ID)
    For each tile (6 tiles × sequential):
        Legend sheets (4 pages, grayscale JPEG, prompt-cached) sent every call
        Pass 1 → Claude Opus 4.6 vision → components + connections JSON
        Pass 2 → Claude Opus 4.6 vision → setpoints, locked positions, conditions
        Pass 3 → Claude Sonnet 4.6 vision → self-verify, corrections, quality flags
        Each pass saved individually → resumable on interruption
    │
    ▼ stitch.py
    Merge 6 tile JSONs
    Apply Pass 3 corrections to Pass 1+2 data
    Deduplicate by normalized tag (overlap regions)
    Resolve EDGE_LEFT/RIGHT/TOP/BOTTOM cross-tile connections
    → unified_extraction.json
    │
    ▼ schema.py (1 API call)
    Claude Sonnet 4.6 converts unified extraction → pid.graph.v0.1.1 JSON
    Streaming (output can be 20K+ tokens for large graphs)
    → pid-00X.graph.json
    │
    ▼ validate.py
    Source 1: OCR tag list (from scanned image, ground truth for tags)
    Source 2: Completeness rules (vessel has P/T conditions, PSV has setpoints, etc.)
    → confidence score % + validation_report.json
    │
    ▼ supergraph.py (after all P&IDs)
    Match off_page_ref nodes across all P&ID graphs
    Wire inter-P&ID edges
    → supergraph.json
```

### 3.2 Models Used

| Step | Model | Reason |
|------|-------|--------|
| Tile extraction pass 1+2 | claude-opus-4-6 | Best vision quality for dense engineering drawings |
| Tile extraction pass 3 | claude-sonnet-4-6 | Self-verification — reasoning, not vision-heavy. 5× cheaper. |
| Schema conversion | claude-sonnet-4-6 | Structured JSON transformation, no vision needed |
| Supergraph wiring | claude-sonnet-4-6 | Graph matching logic, no vision needed |

### 3.3 Cost Per P&ID (Actual)

| P&ID | Extract | Schema | Total |
|------|---------|--------|-------|
| PID-006 | $6.17 | $0.44 | **$6.61** |
| PID-007 | $5.79 | $0.37 | **$6.16** |
| PID-008 | ~$6.14 | $0.46 | **~$6.60** |

Optimizations applied:
- Grayscale JPEG compression: tiles 267KB avg (vs 850KB PNG), legends 1MB (vs 5.6MB)
- Prompt caching on legend sheets: ~$1.30 saved per P&ID
- Pass 3 on Sonnet instead of Opus: ~$0.60 saved per P&ID

### 3.4 Results

| P&ID | Nodes | Edges | Confidence | OCR Coverage |
|------|-------|-------|-----------|--------------|
| PID-006 | 113 | 83 | 81% | 94.7% |
| PID-007 | 109 | 69 | 84% | 100% |
| PID-008 | 144 | 96 | 79% | 100% |
| Supergraph | 366 total | 249 total | — | 1 inter-P&ID |

### 3.5 Graph Schema (pid.graph.v0.1.1)

Node types: `equipment`, `valve`, `instrument`, `junction`, `terminator`, `nozzle`, `annotation`

Edge kinds: `process`, `signal`, `impulse`, `association`, `containment`

Key node fields: `id`, `type`, `subtype`, `tag`, `layer`, `status`, `service`, `loop_id`,
`signal_type`, `off_page_ref`, `off_page_doc_id`, `props`

Key edge fields: `id`, `from`, `to`, `kind`, `line_tag`, `pipe_class`, `diameter`,
`fluid_code`, `flow_dir`, `layer`, `status`, `props`

Strategy version `v0.1.0` embedded in every graph's `metadata`.

---

## 4. RAG System Design (Planned)

### 4.1 Document Sources

| Document | Content | P&ID Tags |
|----------|---------|-----------|
| PID-008 operational narrative | System description, operating procedures | `[pid-008]` |
| PID-006 narrative | Scraper launcher procedures | `[pid-006]` |
| PID-007 narrative | System 361 procedures | `[pid-006, pid-007]` |
| Legend sheets (text) | Symbol definitions, abbreviations | `[global]` |
| Engineering standards | General P&ID conventions | `[global]` |

Source docs in: `data/datasets/rumaila-pp01/narratives/`

### 4.2 Indexing Pipeline

```python
# src/ingestion/rag.py (to be built)
for doc in narrative_docs:
    chunks = chunk(doc, size=500, overlap=50)
    for chunk in chunks:
        tags = infer_pid_tags(chunk)  # [pid-008] etc.
        embedding = embed(chunk.text)  # text-embedding-3-small
        index.add(embedding, metadata={"text": chunk.text, "source": doc.name, "tags": tags})
index.save("src/talking-pnids-py/data/rag/")
```

### 4.3 Query-Time Retrieval

```python
# src/talking-pnids-py/backend/utils/rag.py (to be built)
def retrieve(query: str, pid_id: str, k: int = 5) -> list[str]:
    query_embedding = embed(query)
    candidates = index.search(query_embedding, k=50)
    # Filter: keep chunks tagged with this P&ID or [global]
    filtered = [c for c in candidates if pid_id in c.tags or "global" in c.tags]
    return [c.text for c in filtered[:k]]
```

---

## 5. Query Layer Design (Planned)

### 5.1 Agent Architecture

```python
# POST /api/query
# Input: {query, session_id, pid_id, sources: ["graph", "rag"]}

tools = [
    get_node(tag),           # → full node JSON
    list_nodes(type, pid_id), # → all nodes of type in P&ID
    find_path(from_tag, to_tag), # → list of edges (shortest path)
    impact_region(tag),      # → all downstream/upstream nodes
    get_edge(from_tag, to_tag), # → edge details (pipe spec, fluid)
    search_nodes(query),     # → fuzzy tag/service search
]

answer = llm.invoke(
    system=SYSTEM_PROMPT,
    tools=tools if "graph" in sources else [],
    rag_context=retrieve(query, pid_id) if "rag" in sources else [],
    messages=session_history,
    user=query,
)
```

### 5.2 System Prompt (Graph Mode)

> "You are a senior process engineer answering questions about P&ID diagrams.
> You have access to a structured knowledge graph of the diagram. Use the tools
> to look up exact node data before answering. Always include the tag numbers
> you referenced. If a question requires tracing a path (e.g. upstream effects),
> use find_path() or impact_region() to traverse the graph systematically."

### 5.3 Source Attribution in Response

Each response will include a `sources` field:
```json
{
  "answer": "HV-0059 is a 4-inch gate valve, normally locked open (LO)...",
  "sources": {
    "graph_nodes": ["HV-0059", "PP01-362-V001"],
    "rag_chunks": ["008-narrative-p3", "008-narrative-p7"]
  }
}
```

Frontend renders this as a "source callout" below each message.

---

## 6. Frontend Design (Planned)

### 6.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Talking P&IDs          [P&ID: PID-008 Fuel Gas KO Drum ▼]    │
├────────────────────────────┬────────────────────────────────────┤
│                            │ Sources: [x] Diagram  [x] Notes   │
│   PDF Viewer (PDF.js)      │────────────────────────────────────│
│                            │ [message 1]                        │
│   [highlighted tags        │ [message 2]                        │
│    drawn as overlays]      │ ┌─ Answer ───────────────────────┐ │
│                            │ │ HV-0059 is a 4" gate valve...  │ │
│                            │ │ Sources: [graph:HV-0059] [note]│ │
│                            │ └────────────────────────────────┘ │
│                            │────────────────────────────────────│
│                            │ [Ask about this diagram...]  [→]  │
└────────────────────────────┴────────────────────────────────────┘
```

### 6.2 Key Changes from Current UI

| Current | New |
|---------|-----|
| "Start Session" button | Auto-initialize on page load |
| Sidebar with P&ID list | Dropdown selector in header |
| No source indication | Source callout per message |
| iframe PDF viewer | PDF.js with tag highlight overlay |
| Only PID-008 works | All 3 P&IDs selectable |
| Single context mode | Source selector: Diagram / Notes / Both |

### 6.3 P&ID Link Processing (Keep)

Current regex parsing of LLM responses for `[doc_id:...]` or `[PID-####]` references → convert
to clickable links that switch the active diagram. This works well and should be kept.

---

## 7. Deployment

### 7.1 Current

| Service | URL | Platform |
|---------|-----|----------|
| Backend | https://decent-lilli-cogit-0d306da3.koyeb.app | Koyeb |
| Frontend | https://talking-pnid.vercel.app/app | Vercel |

### 7.2 Configuration

Priority: environment variables > `config/config.json` > built-in defaults

Key env vars:
- `OPENAI_API_KEY` — required for query layer
- `ANTHROPIC_API_KEY` — required for ingestion pipeline (not needed at runtime)
- `MODEL` — OpenAI model name (default: gpt-4o)
- `PDFS_DIR`, `MDS_DIR`, `JSONS_DIR` — absolute paths for Koyeb deployment

### 7.3 Data files at runtime

```
src/talking-pnids-py/data/
├── pdfs/          # P&ID PDFs served to frontend
├── mds/           # Markdown context (current — to be replaced by graph)
├── jsons/         # Equipment JSON schemas
├── graphs/        # pid.graph.v0.1.1 JSON files (NEW)
│   ├── pid-006.graph.json
│   ├── pid-007.graph.json
│   ├── pid-008.graph.json
│   └── supergraph.json
└── rag/           # FAISS index + chunk metadata (PLANNED)
```

---

## 8. Key Design Decisions & Rationale

### Graph vs markdown context injection
Graph wins for structural/topology questions. Markdown works for narrative questions.
Use both — "Full Picture" mode combines both sources.

### Anthropic tool_use vs LangChain agents
Direct `tool_use` API chosen: fewer dependencies, easier to debug, clearer token accounting.

### Supergraph
One graph to rule them all — individual P&ID graphs are nodes; off_page_ref edges are wired
into inter-P&ID connections. Enables cross-diagram queries without loading all graphs simultaneously.

### Strategy versioning (STRATEGY_VERSION = "v0.1.0")
Every graph and validation report embeds the strategy version. When extraction prompts or models
change, bump the version and the testing team can compare before/after quality.

### Prompt caching on legend sheets
Legend sheets are 4 PDF pages of abbreviations and piping symbols. Same for every API call.
Anthropic's prompt caching saves ~90% on legend tokens after the first call in a session.
Cache control placed on the last legend block (`cache_control: {"type": "ephemeral"}`).

### Grayscale JPEG for image compression
P&IDs are black-and-white engineering drawings. Converting PNG tiles to grayscale JPEG:
- Tiles: 850KB → 267KB (3× smaller)
- Legend sheets: 5.6MB → 1.4MB (4× smaller, avoids 5MB API limit)
Visual quality for line drawings: no meaningful loss.

### Excel ground truth disabled
`PID Data.xlsx` exists but has not been independently verified as correct. Enabled it was
adding false failures to the confidence score. Disabled until a process engineer signs off.
Functions kept in `validate.py` for future reactivation.

---

## 9. File Map

### Ingestion Pipeline
```
src/ingestion/
├── ingest.py       — CLI orchestrator
├── tile.py         — PDF → tiles
├── extract.py      — tiles → Claude vision (3 passes)
├── stitch.py       — 6 tiles → unified_extraction.json
├── schema.py       — unified → pid.graph.v0.1.1 JSON
├── validate.py     — graph vs OCR + completeness rules
├── supergraph.py   — wire cross-P&ID edges
├── config.py       — constants, paths, cost calculator
├── PLAN.md         — original build plan
├── STRATEGIES.md   — strategy version log
└── CLAUDE.md       — session context for AI assistant
```

### Web App Backend
```
src/talking-pnids-py/backend/
├── main.py                    — FastAPI app, CORS, route registration
├── api/session.py             — POST /api/session
├── api/query.py               — POST /api/query (needs graph integration)
├── api/files.py               — GET /api/files
├── api/pdf.py                 — GET /api/pdf/{filename}
├── utils/langchain_setup.py   — model routing, session history
├── utils/config.py            — config loading
├── utils/paths.py             — path resolution
└── utils/markdown_cache.py    — markdown caching
```

### Web App Frontend
```
src/talking-pnids-py/frontend/src/
├── pages/AppPage.tsx          — main UI (~600 lines)
├── utils/api.ts               — typed API client
├── App.tsx                    — router
└── ...
```

---

## 10. Benchmark Questions (PID-008)

The measure of success. All 10 should be answered correctly after graph+RAG integration.

| # | Question | Required knowledge |
|---|----------|--------------------|
| Q1 | Design/op pressure+temp for 362-V001 | Node props |
| Q2 | All isolation valves for 362-V001 | find_neighbors(V001, type=valve) |
| Q3 | EZV-002 closes — upstream effects + safeguards | impact_region(EZV-002, direction=upstream) |
| Q4 | HV0027 closed — critical instrumentation | impact_region(HV0027) |
| Q5 | All HH/H/L/LL instruments (tabular) | list_nodes(instrument) → filter props.alarms |
| Q6 | All LO/LC valves | list_nodes(valve) → filter props.normal_position |
| Q7 | Purpose of BDZV0001, stuck effects | Node props + impact_region |
| Q8 | Spectacle blinds with sizes | list_nodes(valve, subtype=spectacle_blind) |
| Q9 | Note 10 applicable lines | Annotation nodes + edge traversal |
| Q10 | All spec breaks with boundary equipment | junction nodes where props.spec_change=true |

---

## 11. Open Questions

1. **RAG embedding model:** text-embedding-3-small vs Cohere vs Claude? Need to benchmark retrieval quality on P&ID narratives.

2. **Graph query tool design:** Should `find_path` return all paths or shortest only? How deep should `impact_region` traverse before stopping?

3. **Supergraph completeness:** Only 1 inter-P&ID connection found via off_page_ref matching. Are there more that weren't matched? Manual review needed.

4. **PDF.js vs react-pdf:** react-pdf wraps PDF.js; might be simpler to integrate with React while still supporting canvas overlays.

5. **Multi-user isolation:** Currently one shared graph loaded per P&ID. Fine for demo/POC. For production with concurrent users, need to ensure tool invocations are stateless.
