# Talking P&IDs — Planning

> Strategic roadmap and implementation plans for major upcoming work.
> Updated: 2026-03-26

---

## Roadmap Overview

```
Phase 1 (Now)     Web app live, OCR done, graph done, training pipeline ready
Phase 2 (Next)    Train YOLO model, improve OCR, enable all 3 P&IDs in app
Phase 3           Integrate ML outputs into web app (coordinate-based highlights)
Phase 4           Scale to more P&IDs, full auth, session persistence
```

---

## Plan A: Train YOLO Model (Step 7)

**Goal:** Produce a production-quality YOLOv8m model for P&ID symbol detection.

**Pre-conditions (all met):**
- Steps 1–6 complete: datasets collected, standardized, preprocessed, merged, augmented, config generated
- ~95,800 merged samples, 161k augmented training samples
- `config/train_config.yaml` ready (YOLOv8m, 640px, batch 32, 100 epochs)

**Steps:**
1. Ensure CUDA GPU available: `nvidia-smi`
2. Activate environment: `cd src/model-pretrain`
3. Run: `python scripts/step7_train.py`
4. Monitor: tensorboard or ultralytics console output in `runs/detect/pid_baseline_yolov8m/`
5. Evaluate on test set: check mAP50, mAP50-95 per class
6. Replace `best.pt` if new model outperforms current checkpoint

**Expected output:** `runs/detect/pid_baseline_yolov8m/weights/best.pt`

**Risk:** Training data may be biased toward synthetic/schematic symbols; real P&ID performance may be lower.
**Mitigation:** After training, run inference on real P&IDs and compare with OCR outputs.

---

## Plan B: Improve OCR Extractor

**Goal:** Increase tag recall from ~60–90% to >95%.

**Known gaps:**
1. DPI 300 may miss fine-print tags — try 400
2. Split tags (prefix `HV` + number `0065` on separate OCR lines) — need spatial join
3. `nearby_line_numbers` empty — need spatial search instead of text-stream proximity

**Steps:**
1. **DPI test:** Run extractor at 400 DPI on PID-008, compare tag count vs current 36
   - File: `src/extractor/ocr.py` → `render_page()`, change default DPI
2. **Preprocessing:** Add contrast/denoise step before OCR
   - Add `preprocess_image(img)` in `ocr.py` using PIL `ImageEnhance` + `ImageFilter`
3. **Split tag fix:** After sliding-window pass, run a second pass that spatially joins
   prefix-only hits with number-only hits within 50px
   - File: `src/extractor/extract.py` → new function `join_split_tags()`
4. **Line number spatial search:** Replace text-stream approach with spatial bbox lookup
   - For each tag, search all OCR words within 100px radius for line number pattern
   - File: `src/extractor/extract.py` → `extract_nearby_line_numbers(word_data, tag_bbox)`

---

## Plan C: Enable All 3 P&IDs in Web App

**Goal:** All three P&IDs selectable and queryable in the chat interface.

**Steps:**
1. Verify 006.md and 007.md quality (currently 172 and 106 lines vs 1539 for 008)
2. Expand 007.md to match 008.md depth — use `comprehensive_pid_summary.md` and docx files as source
3. Update `src/talking-pnids-py/config/file-mappings.json` — uncomment/re-enable pid-006 and pid-007 entries
4. Test locally: start session, switch between diagrams, verify LLM responses for each
5. Deploy backend update to Koyeb

---

## Plan D: Integrate Tag Coordinates into Web App

**Goal:** When LLM mentions a tag (e.g. HV-0059), highlight it on the PDF viewer.

**Steps:**
1. Backend: load `_tags.json` files at startup; add tag lookup to `api/query.py`
2. When LLM response mentions a tag ID, append its coordinates in response JSON
3. Frontend: receive tag coords in response; use PDF.js (replace iframe) to draw highlight overlay
4. UX: clicking a tag in the chat response scrolls to and highlights it in the PDF viewer

**Dependency:** Need to replace `<iframe>` PDF viewer with PDF.js for overlay support.

---

## Plan E: Add PID-0005

**Goal:** Add the unprocessed PID-0005 document to the system.

**Steps:**
1. Copy `data/Talking PNID Extra/Tech Ventures/100478CP-N-PG-PP01-PR-PID-0005-001-C02.pdf`
   to `data/sources/pdf/`
2. Run OCR extractor: `python3 pid_extractor.py ... --output data/outputs/ocr/pid-005_tags.json`
3. Run YOLO inference: `python3 yolo_infer.py ...`
4. Create markdown doc `src/talking-pnids-py/data/mds/005.md` — document the system
5. Add entry to `file-mappings.json`
6. Test in web app

---

## Options & Decisions

### Dataset expansion for YOLO training
**Option 1:** Use existing synthetic data only (~95.8k samples) — faster, simpler
**Option 2:** Add real P&ID tiles from OCR outputs — better real-world performance, more work
**Recommendation:** Start with Option 1; evaluate model on real P&IDs; add real tiles if recall is poor

### Session persistence
**Option 1:** Redis — best for production, requires additional service
**Option 2:** SQLite — simple, single-file, no extra service
**Option 3:** Filesystem JSON — simplest, fine for low traffic
**Recommendation:** Option 3 (filesystem) as quick solution; upgrade to Redis when scaling

### Multi-user auth
**Current state:** Auth disabled, single shared session concept
**Option 1:** JWT auth with user accounts (full solution)
**Option 2:** Simple API key per session (no accounts)
**Recommendation:** Defer until there are actual multiple users who need isolation
