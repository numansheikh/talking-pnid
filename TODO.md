# Talking P&IDs — TODO List

> Prioritized list of open work across all components.
> Updated: 2026-03-26

---

## Priority 1 — High Impact / Blocking

### [ ] Train YOLO model (Step 7)
- All 6 prep steps done; training script `src/model-pretrain/scripts/step7_train.py` ready
- Requires: CUDA GPU (RTX 3090 24GB), ~95.8k samples ready
- Command: `cd src/model-pretrain && python scripts/step7_train.py`
- Output: `runs/detect/pid_baseline_yolov8m/`
- Note: `best.pt` currently in use is an earlier checkpoint — this would replace it

### [ ] Re-run extractor on PID-0007 and PID-0008 with improvements
- OCR outputs exist but were generated with current limitations
- After implementing DPI/preprocessing improvements below, re-run all 3 PDFs
- Command: `cd src/extractor && python3 pid_extractor.py <pdf> --dpi 400 --output ...`

---

## Priority 2 — Quality Improvements

### [ ] Improve OCR recall (extractor)
- Try DPI 400 (currently 300)
- Add image preprocessing: contrast enhancement, denoise, binarization
- Measure recall improvement against known ground truth tags
- File: `src/extractor/ocr.py` → `render_page()` and preprocessing step

### [ ] Fix split tag extraction (extractor)
- Some tags have prefix (`HV`) and number (`0065`) on separate OCR lines
- Need to join nearby OCR tokens spatially before regex matching
- File: `src/extractor/extract.py` → `find_tags_with_coords()`

### [ ] Fix `nearby_line_numbers` extraction (extractor)
- Currently often empty because OCR text stream doesn't preserve spatial proximity
- Need spatial search: find pipe line number tokens within N pixels of each tag
- File: `src/extractor/extract.py`

### [ ] Enable PID-006 and PID-007 in web app
- `src/talking-pnids-py/config/file-mappings.json` — currently only pid-008 enabled
- Need to verify 006.md and 007.md are good quality context docs before enabling
- Consider expanding 007.md (currently only 106 lines vs 008.md at 1539 lines)

---

## Priority 3 — New Features

### [ ] Integrate tag JSON data into web app responses
- OCR-extracted `_tags.json` contains precise coordinates for every tag
- Could return tag coordinates in LLM response for frontend to highlight on PDF
- Backend: add tag lookup to `api/query.py`
- Frontend: add PDF highlight layer over iframe

### [ ] Add PID-0005 to the system
- PDF exists at `data/Talking PNID Extra/Tech Ventures/100478CP-N-PG-PP01-PR-PID-0005-001-C02.pdf`
- Not yet processed by extractor or added to web app
- Steps: run extractor → create markdown doc → add to file-mappings.json

### [ ] Add real P&ID tiles as YOLO training data
- 3 annotated P&IDs available: `_tags.json` + `_annotated.pdf` per PDF
- Pipeline: rasterize PDFs → convert normalized coords to YOLO format → tile 640×640 → merge into dataset
- File: `src/model-pretrain/` — create `scripts/step_add_real_pids.py`

### [ ] Session persistence
- Current in-memory session dict lost on server restart
- Options: Redis, SQLite, or filesystem JSON
- File: `src/talking-pnids-py/backend/utils/langchain_setup.py`

### [ ] Auth system
- `frontend/src/contexts/AuthContext.tsx` has TODO placeholders
- Login is currently mocked/disabled
- Decide if multi-user support is needed before implementing

---

## Priority 4 — Infrastructure / Housekeeping

### [ ] Commit untracked source code
- `src/extractor/`, `src/model-pretrain/`, `src/pnid-analyze/` not in git
- These represent significant work; should be versioned
- Note: exclude large binary files (datasets, model weights) via .gitignore

### [ ] Add `.gitignore` entries for data/models
- `data/outputs/`, `data/sources/` currently untracked
- Model weights (`best.pt`, `runs/`) should not be committed — too large
- Training datasets (`datasets/`) should not be committed

### [ ] Expand 007.md documentation
- `src/talking-pnids-py/data/mds/007.md` is only 106 lines (sparse)
- `008.md` is 1539 lines — similar detail needed for 007 for good LLM responses

### [ ] Write tests
- `/tests/` directory exists but is empty
- Minimum: extractor unit tests (tag regex, dedup, coord transform)
- Backend: API integration tests

---

## Completed

### [x] OCR extraction — all 3 P&IDs
- PID-006: 19 tags (16 valves, 3 instruments)
- PID-007: 23 tags (22 valves, 1 instrument)
- PID-008: 36 tags (36 valves)
- Outputs: `data/outputs/ocr/`

### [x] YOLO inference — all 3 P&IDs
- Using existing `best.pt` model
- Outputs: `data/outputs/yolo/`

### [x] Graph analysis — PID-008
- `src/pnid-analyze/unified_pid_graph.json` + `unified_pid_graph_clean.json`
- Interactive HTML visualization: `pid_graph.html`

### [x] Training pipeline steps 1–6
- ~95.8k merged samples, 161k augmented training samples
- Config ready for YOLOv8m training

### [x] Web app deployed
- Backend on Koyeb, frontend on Vercel
- PID-008 live and functional

### [x] 0008.md comprehensive documentation
- 1539-line markdown spec covering all equipment, nozzles, instruments, logic

### [x] Model routing for reasoning models
- gpt-4/gpt-4o via LangChain, o1/o3/gpt-5.x via direct OpenAI API
