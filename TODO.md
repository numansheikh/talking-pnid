# Talking P&IDs — TODO List

> Prioritized task list. Updated: 2026-03-27
> The ingestion pipeline is complete. All work is now focused on wiring the graphs into the product.

---

## Priority 0 — Immediate (do next)

### [ ] Build RAG pipeline for narrative documents
- **Why:** Experts want to compare "AI graph" vs "AI RAG" answers side-by-side (P0 validation requirement)
- Source docs: `data/datasets/rumaila-pp01/narratives/` — DOCX operational/engineering narratives
- Chunk + embed → FAISS or Chroma vector store
- Tag each chunk with relevant P&ID IDs: `[pid-008]`, `[pid-006, pid-007]`, `[global]`
- At query time: retrieve top-k chunks matching the selected P&ID
- File to create: `src/ingestion/rag.py` (build) + integration into backend query layer
- See PLANNING.md Plan B for full design

### [ ] Wire graph JSON into backend query layer
- **Why:** Core product improvement — structured knowledge graph instead of flat markdown
- `src/talking-pnids-py/backend/api/query.py` — currently injects markdown; replace with graph query
- Add graph as agent tools: `find_path(from, to)`, `impact_region(tag)`, `get_node(tag)`, `list_nodes(type)`
- Load graph JSON at startup from `data/graphs/pid-00X.graph.json`
- Use `supergraph.json` for cross-P&ID traversal
- See PLANNING.md Plan C for full design

### [ ] Frontend redesign
- **Why:** Current UI has dead controls, poor information hierarchy, confusing session concept
- Remove "Start Session" button — initialize automatically on page load
- Add source selector checkboxes: "Diagram Analysis" (graph), "Engineering Notes" (RAG), "Full Picture" (both)
- Show source callout per message: which sources contributed to the answer
- P&ID sidebar: clickable links switch the active diagram (already works, needs polish)
- Replace iframe PDF viewer with PDF.js to support tag highlight overlays
- See PLANNING.md Plan D for full design

---

## Priority 1 — High Impact

### [ ] Enable PID-006 and PID-007 in web app
- Update `src/talking-pnids-py/config/file-mappings.json` — add `graph` field pointing to graph JSON
- All three graphs exist at `src/talking-pnids-py/data/graphs/`
- Supergraph is live: `supergraph.json` (3 P&IDs, 1 inter-P&ID connection)
- Test cross-P&ID questions that traverse supergraph

### [ ] Tag highlight overlay (PDF viewer)
- When AI mentions a tag (e.g. HV-0059), highlight it on the PDF
- Requires: replace `<iframe>` PDF viewer with PDF.js
- Backend: tag → coordinates lookup from `_tags.json` OCR outputs
- Frontend: draw translucent rectangle overlay at tag position
- Dependency: frontend redesign (PDF.js integration)

### [ ] Validate system against 10 benchmark questions (PID-008)
- The real measure of whether the graph approach works
- Run all 10 questions via the updated query layer
- Target: ≥8/10 correct (currently estimated ~5-6/10 with markdown context)
- See benchmark questions in PLANNING.md

---

## Priority 2 — Quality Improvements

### [ ] Run ingestion pipeline on PID-005
- PDF exists at `data/Talking PNID Extra/Tech Ventures/100478CP-N-PG-PP01-PR-PID-0005-001-C02.pdf`
- Command: `python ingest.py --pdf <path>`
- Estimated cost: ~$7

### [ ] Improve validation confidence scores
- PID-008: 79%, PID-006: 81%, PID-007: 84%
- High issues: 3/3/2 per P&ID — investigate common failures
- Re-enable Excel validation once ground truth is verified
- Consider adding a Pass 4 (targeted re-extraction for low-confidence regions)

### [ ] Session persistence
- In-memory session dict lost on server restart
- Options: filesystem JSON (simplest), SQLite, Redis
- File: `src/talking-pnids-py/backend/utils/langchain_setup.py`

---

## Priority 3 — Deferred / Nice to Have

### [ ] Train YOLO model (Step 7)
- All 6 prep steps done; requires CUDA GPU
- ~95.8k samples ready; command: `python scripts/step7_train.py`
- Deferred: not needed for the graph/RAG approach

### [ ] Improve OCR extractor
- DPI 400, split tag handling, spatial line number extraction
- Useful if ingestion quality needs boosting (currently OCR coverage 94–100%)

### [ ] Auth system
- Currently mocked/disabled
- Defer until real multi-user usage

### [ ] Write tests
- `/tests/` directory empty
- Minimum: ingestion pipeline unit tests, backend API integration tests

---

## Completed

### [x] Ingestion pipeline — all 3 P&IDs
- PID-006: 113 nodes, 83 edges | 81% confidence | 94.7% OCR coverage | $6.61
- PID-007: 109 nodes, 69 edges | 84% confidence | 100% OCR coverage | $6.16
- PID-008: 144 nodes, 96 edges | 79% confidence | 100% OCR coverage | ~$6.6
- Supergraph: 366 nodes, 249 edges, 1 inter-P&ID connection
- Strategy version: v0.1.0

### [x] Pipeline features (ingestion)
- 3-pass Claude Opus 4.6 vision extraction per tile (6 tiles × 3 passes = 18 calls)
- Pass 3 on Sonnet (5× cheaper), prompt caching on legend sheets (~90% cheaper after 1st call)
- Grayscale JPEG compression (3× smaller than PNG)
- Retry with backoff (handles 429 rate limits + 529 overload)
- Resume at any pass — never re-runs completed work
- pid.graph.v0.1.1 schema with strategy version embedded

### [x] Supergraph
- Built from all 3 P&ID graphs
- Off-page reference matching → 1 inter-P&ID edge wired
- Saved to `src/talking-pnids-py/data/graphs/supergraph.json`

### [x] Web app deployed (PID-008 only, markdown context)
- Backend: Koyeb | Frontend: Vercel
- PID-006 and PID-007 disabled pending graph integration

### [x] OCR extraction — all 3 P&IDs
- Using scanned raster pipeline (no embedded text in PDFs)
- Outputs in `data/outputs/ocr/`

### [x] YOLO training pipeline steps 1–6
- ~95,800 merged samples, config ready for step 7

### [x] Graph analysis proof-of-concept
- NetworkX visualization for PID-008 (`src/pnid-analyze/`)
