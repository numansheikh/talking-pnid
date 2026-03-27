# Talking P&IDs — Planning

> All strategic plans, alternatives, brainstorming, and architectural decisions.
> Updated: 2026-03-27

---

## Current Status

The ingestion pipeline is complete. We have knowledge graphs for all 3 P&IDs.
The next phase is wiring those graphs into the product and building the RAG layer.

| Component | Status |
|-----------|--------|
| Ingestion pipeline | Done — all 3 P&IDs |
| pid.graph.v0.1.1 graphs | Done — 006, 007, 008 |
| Supergraph | Done — 1 inter-P&ID connection |
| Web app (graph-powered) | Not started |
| RAG pipeline | Not started |
| Frontend redesign | Not started |

---

## Plan A — RAG Pipeline

**Goal:** Add narrative document search alongside graph query. Gives experts a way to test graph vs RAG answers.

**Why RAG in addition to graph:**
- Graph = structural knowledge: topology, tags, connections, design conditions
- RAG = narrative knowledge: operating procedures, system descriptions, engineering notes
- Complementary — graph answers "what is connected to X", RAG answers "why does X exist"
- Expert testers want to see a "source selector" so they can compare approaches

**Architecture:**
```
narratives/ (DOCX)
    ↓ chunk (500 tokens, 50 overlap)
    ↓ embed (text-embedding-3-small or Claude)
    ↓ FAISS / Chroma index
    ↓ tag chunks with P&ID IDs: [pid-008], [pid-006, pid-007], [global]
    → at query time: filter by selected P&ID → top-k retrieval → inject as context
```

**Chunk tagging strategy:**
- `[pid-008]` — content specific to PID-008 (KO drum system)
- `[pid-006]` — content specific to PID-006 (scraper launcher)
- `[pid-007]` — content specific to PID-007
- `[global]` — applicable to all P&IDs (general procedures, legend definitions)
- A chunk can have multiple tags (e.g., `[pid-006, pid-007]` if it covers both systems)

**File plan:**
- `src/ingestion/rag.py` — indexing script (run once, or on new docs)
- `src/talking-pnids-py/backend/utils/rag.py` — query-time retrieval
- `src/talking-pnids-py/data/rag/` — FAISS index + chunk metadata

**Alternatives considered:**
- Full document injection (current approach): works for small docs, breaks for 100+ pages
- LlamaIndex / LangChain RAG: heavier dependency, similar outcome
- **Decision:** Build lightweight custom RAG (chunk → embed → FAISS) to keep dependencies minimal

---

## Plan B — Graph Query Layer

**Goal:** Replace flat markdown context injection with structured graph queries.

**Current approach (broken):**
- All markdown docs loaded into LLM system prompt every query
- Works for PID-008 (1539-line doc), but brittle — hallucinations when doc doesn't have the answer
- Can't scale to more P&IDs without exceeding context window

**New approach:**
```
User query
    → intent classification (which P&ID? what type of question?)
    → graph agent with tools:
        get_node(tag)          → return full node JSON for a tag
        list_nodes(type)       → all nodes of a given type (all valves, all instruments)
        find_path(from, to)    → shortest path between two nodes
        impact_region(tag)     → all nodes reachable from tag (upstream/downstream)
        get_edge(from, to)     → connection details (pipe spec, line tag, fluid code)
        search_nodes(query)    → fuzzy tag/service search
    → LLM assembles answer from tool results
```

**Supergraph role:**
- Loaded alongside individual P&ID graphs
- Enables cross-P&ID questions: "what does PID-008 connect to on PID-007?"
- `find_path()` traverses supergraph edges to cross P&ID boundaries

**Fallback if graph query fails:**
- Inject graph JSON directly as context (simpler, less token-efficient)
- Works for small graphs (<200 nodes), but won't scale

**File plan:**
- `src/talking-pnids-py/backend/utils/graph_tools.py` — tool implementations
- `src/talking-pnids-py/backend/api/query.py` — update to use graph agent
- `src/talking-pnids-py/config/file-mappings.json` — add `"graph"` field per P&ID

---

## Plan C — Frontend Redesign

**Goal:** Remove dead controls, add source transparency, improve information hierarchy.

**Current problems:**
1. "Start Session" button — confusing, not industry-standard, initialization should be automatic
2. Three P&IDs visible but only one works — misleading
3. No indication of where the AI's answer came from
4. PDF viewer is an iframe — can't draw overlays for tag highlighting
5. No way for user to mark interesting tags or flag errors
6. Session controls (new session etc.) are prominent but low-value

**Redesigned layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  [logo]  Talking P&IDs              [P&ID selector: 006▼]  │
├──────────────────────────┬──────────────────────────────────┤
│                          │  Source: [x] Diagram  [x] Notes  │
│    PDF viewer            │─────────────────────────────────-│
│    (PDF.js)              │  [message history]               │
│                          │                                  │
│    [tag overlays]        │  ╔══════════════════════════════╗│
│                          │  ║ Answer from: Diagram + Notes ║│
│                          │  ║ HV-0059 is a 4" gate valve...║│
│                          │  ╚══════════════════════════════╝│
│                          │─────────────────────────────────-│
│                          │  [type your question...]    [→]  │
└──────────────────────────┴──────────────────────────────────┘
```

**Key UX decisions:**
- Session auto-starts on page load — no "Start Session" button
- Source selector: "Diagram Analysis" (graph only), "Engineering Notes" (RAG only), "Full Picture" (both)
- Each AI message shows a source callout: which graph nodes / which RAG chunks were used
- Clickable tag links in AI responses highlight the tag on the PDF viewer
- P&ID selector in header (not sidebar) — cleaner

**Alternative layouts considered:**
- Three-panel (current) — too much chrome, sidebar wastes space
- Two-panel (PDF left, chat right) — simpler, preferred
- Mobile-first — not needed for industrial/desktop use case
- **Decision:** Two-panel, PDF.js viewer, source checkboxes above chat

**Tag highlight overlay:**
- Requires PDF.js (canvas-based) instead of iframe
- Backend returns tag coordinates from `data/outputs/ocr/*_tags.json`
- Frontend draws translucent rectangles at tag positions when AI mentions them
- Click on highlighted tag → scroll to in PDF

---

## Plan D — Benchmark Validation

**Goal:** Prove the graph+RAG approach answers the 10 sample questions correctly.

**10 benchmark questions (PID-008):**

| # | Question |
|---|----------|
| Q1 | Design/operating pressure and temperature for vessel 362-V001 |
| Q2 | All isolation valves on vessel 362-V001 |
| Q3 | EZV-002 closes — what are upstream pressure effects and safeguards? |
| Q4 | HV0027 inadvertently closed — what critical instrumentation is affected? |
| Q5 | All instruments with HH/H/L/LL alarm functions (tabular format) |
| Q6 | All locked open (LO) and locked closed (LC) valves |
| Q7 | Purpose of BDZV0001, effects if stuck open vs stuck closed |
| Q8 | Spectacle blinds — list all with sizes |
| Q9 | Which lines does Note 10 apply to? |
| Q10 | All spec breaks with boundary equipment and pipe specs |

**Current baseline (markdown context only):** ~5-6/10

**Target (graph + RAG):** ≥8/10

**Measurement:** Run each question via API, score manually with process engineer review

---

## Plan E — Ingestion Scale-Up

**Goal:** Process more P&IDs as the system grows.

**Current state:**
- 3 P&IDs ingested (006, 007, 008)
- PID-005 exists but not processed
- 29 PDFs total in `data/pdfs/` (many are legend/format sheets)

**Cost per P&ID:**
- Extract: ~$6.00 (12 Opus calls + 6 Sonnet calls, with caching)
- Schema: ~$0.40 (1 Sonnet call)
- Total per P&ID: ~$6.40
- 10 P&IDs: ~$64

**Options for cost reduction:**
- Increase tile size (fewer tiles → fewer calls) — risk: harder for LLM to read dense areas
- Skip Pass 3 (Sonnet verification) — saves ~$0.10, minimal quality impact
- Batch multiple tiles per call — not supported by Anthropic API
- **Current choice:** keep 3-pass approach for quality, accept $6-7/P&ID cost

---

## Architectural Alternatives Considered

### Graph-only vs Graph+RAG
- **Graph-only:** Answers structural questions perfectly. Fails on "why", "purpose", "procedure" questions.
- **RAG-only:** Good for prose answers. Fails on precise topology questions (missed connections, wrong specs).
- **Graph+RAG:** Best of both. Source selector lets experts validate each independently.
- **Decision:** Graph+RAG for production. Build graph first (done), RAG next.

### LangChain agent vs direct tool calls
- **LangChain agent:** Easy to build, good tooling, but adds ~800 lines of abstraction
- **Direct tool calls:** Anthropic's tool_use API — cleaner, easier to debug, no framework dependency
- **Decision:** Direct tool_use API calls

### FAISS vs Chroma vs Pinecone for RAG
- **FAISS:** In-process, no server, fast, well-understood. No persistence built-in.
- **Chroma:** Persistent, easy API, heavier. Overkill for 3 P&IDs.
- **Pinecone:** Managed, scales, costs money. Unnecessary at this scale.
- **Decision:** FAISS with filesystem persistence (serialize index to `data/rag/`)

### Iframe vs PDF.js for PDF viewer
- **Iframe:** Zero code, works for basic viewing. Can't draw overlays.
- **PDF.js:** Canvas-based, full control, can draw overlays, tag highlights, annotations.
- **Decision:** PDF.js. Required for tag highlight feature. Worth the complexity.

### Graph schema: pid.graph.v0.1.1 vs custom
- **Custom flat JSON:** Simpler to query, but loses structural relationships
- **pid.graph.v0.1.1:** Well-defined node/edge types, additionalProperties: false for discipline
- **Decision:** pid.graph.v0.1.1. Invest in schema discipline now — enables future cross-version comparison.

---

## Investor / Demo Story

**Problem:** P&ID diagrams are the "source of truth" for industrial plants but are locked in scanned PDFs.
Engineers spend hours hunting for information that should be instantly queryable.

**Solution:** AI that reads P&IDs like an engineer — understands topology, equipment, connections, design conditions.

**Differentiation:**
1. Graph-structured knowledge (not just OCR/text search) — answers "what's connected to X"
2. Cross-diagram traversal via supergraph — answers questions that span multiple P&IDs
3. Source transparency — engineers can see exactly which diagram element the answer came from
4. Scalable ingestion pipeline — $6-7 per P&ID, fully automated

**Demo script:**
1. "What is the design pressure and temperature for the KO drum?" → graph answers precisely
2. "What happens if EZV-002 closes?" → impact_region() traversal shows upstream effects
3. "Show me all instruments with high-high alarm" → list_nodes() filtered by alarm type
4. Compare "Diagram Analysis" vs "Engineering Notes" answers on same question

**Target customers:** Oil & gas operators, EPC contractors, plant engineering teams
**Scale:** A single refinery has 500-2000 P&IDs. At $7/diagram: $3.5k-$14k for full plant graph.

---

## Backup Approaches

### If graph quality is insufficient (confidence <70%)
- Add a Pass 4: targeted re-extraction of low-confidence tiles with a custom prompt
- Add human-in-the-loop correction interface (mark errors, regenerate specific nodes)
- Fall back to: inject full graph JSON as context (acceptable for small graphs, <200 nodes)

### If Claude vision extraction fails on complex tiles
- Try GPT-4o vision (different model, potentially better at dense diagrams)
- Try higher DPI tiles (300 → 400 DPI)
- Try smaller tiles (4×3 instead of 3×2) — more calls but higher zoom per tile

### If RAG retrieval is poor
- Improve chunking strategy (paragraph-based vs token-based)
- Add metadata filtering (system type, P&ID ID) as hard filters before embedding search
- Use HyDE (hypothetical document embeddings) — generate a hypothetical answer, search for similar chunks

### If LLM can't use graph tools reliably
- Pre-compile common query patterns (isolation valves, alarm instruments) to direct graph queries
- Add few-shot examples of tool usage in system prompt
- Use a smaller, faster model for tool selection + larger model for answer synthesis
