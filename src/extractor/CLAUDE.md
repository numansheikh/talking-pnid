# P&ID Extractor — Session Context

## What this folder does
Standalone Python tooling to extract structured data from scanned P&ID PDF drawings using OCR. Completely independent from the main talking-pnid backend/frontend code.

## Environment
- Python 3.13 via direnv virtualenv at `/Users/numan/Projects/talking-pnid/.direnv/python-3.13/`
- Always run scripts with `python3` from this folder — the virtualenv activates automatically via `.envrc`

## Installed packages (already present, no need to reinstall)
- `pymupdf` — PDF rendering (`import fitz`)
- `pytesseract` — OCR wrapper
- `pillow` — image handling
- `pdfplumber` — alternative PDF text extraction
- System: `tesseract` installed via Homebrew

## Trained Detector Model
- Path: `/Users/numan/Projects/talking-pnid/src/model-pretrain/runs/best.pt`
- Trained YOLO model (ultralytics) for P&ID symbol detection
- 9 classes: `arrow`, `crossing`, `connector`, `valve`, `instrumentation`, `pump`, `tank`, `general`, `inlet_outlet`

## Source PDFs
Location: `/Users/numan/Projects/talking-pnid/data/pdfs/`

29 PDFs from contract 100478 (all scanned raster images, no embedded text):
- PID-0001 (17 sheets), PID-0002, PID-0003, PID-0004, PID-0005, PID-0006, PID-0007, PID-0008, PID-0009
- Also: 3 PFD (Process Flow Diagrams), 2 LST (Line Designation Tables)

Primary P&IDs processed so far:
1. `100478CP-N-PG-PP01-PR-PID-0006-001-C02.pdf` — Scraper Launcher (DS-3), system 361
2. `100478CP-N-PG-PP01-PR-PID-0007-001-C02.pdf` — system 361 related
3. `100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf` — Fuel Gas KO Drum PP01-362-V001

---

## Module Architecture

```
extractor/
├── pid_extractor.py    # Main orchestration + CLI entry point (OCR pipeline)
├── ocr.py              # OCR pipeline helpers (render, rotate, Tesseract, coord transforms)
├── extract.py          # Tag detection, deduplication, line numbers, context notes
├── tags.py             # ISA 5.1 instrument/valve type registries + compiled regexes
├── annotate.py         # Annotate PDF with coloured bounding boxes (OCR results)
└── yolo_infer.py       # YOLO inference on PDFs — saves JSON + annotated PDF
```

### `tags.py`
Defines all known tag types and compiled regexes.
- `VALVE_TYPES` — ~25 valve codes (HV, ESDV, EZV, PSV, MOV, XV, PV, etc.)
- `INSTRUMENT_TYPES` — ~60+ ISA 5.1 codes (PT, TT, FT, LT, AT, ZS, etc.)
- `ALL_TYPES` — merged dict, valve codes take precedence for shared prefixes
- `TAG_RE` — regex matching `PREFIX[-]NUMBER` (e.g. `HV-0059`, `FIT-0002`, `PV-1011/2011`)
- `LINE_RE` — regex for pipe line numbers: `{size}"-PPxx-{system}-{tag}-{spec}`
- `tag_category(code)` — returns `"valve"`, `"instrument"`, or `"unknown"`

### `ocr.py`
Low-level OCR plumbing.
- `render_page(page, dpi)` → PIL image + pixel dimensions
- `rotate_image(img, angle)` — PIL CCW rotation with expand
- `ocr_word_data(img)` → Tesseract word-level bbox dict (`--psm 11 --oem 3`)
- `px_to_pt(px, dpi)` — pixel → PDF point conversion
- `transform_bbox_to_original(left, top, w, h, rotation, orig_w, orig_h)` — maps bboxes from rotated space back to original page coords (handles 0°/90°/180°/270°)
- `page_similarity(doc, idx_a, idx_b, sample_dpi=36)` — pixel-level similarity (0–1) for revision detection
- `group_pages_by_sheet(doc, threshold=0.70)` — groups consecutive similar pages as revisions of the same sheet
- `ROTATIONS = [0, 90, 270]` — angles used per page

### `extract.py`
Core tag detection logic.
- `find_tags_with_coords(word_data, dpi, img_w, img_h, rotation, orig_w, orig_h)` — scans Tesseract output with 1/2/3-word sliding windows; transforms bboxes back to original space; deduplicates prefix-matches at same position
- `deduplicate_tags(tags, proximity_px=50)` — merges hits from multiple rotation passes, keeping highest-confidence occurrence per tag per location
- `extract_line_numbers(text)` — finds pipe line numbers via `LINE_RE`
- `extract_note_for_tag(text, tag)` — returns ±120-char context windows around tag mentions

### `pid_extractor.py`
Main orchestration module.
- `extract_pid(pdf_path, dpi=300, all_pages=False)` — full pipeline:
  1. Groups pages by sheet (revision detection)
  2. Per page: renders → rotates × 3 → OCR → tag detection → deduplication
  3. Aggregates tags across pages, extracts notes and nearby line numbers
  4. Returns structured dict
- `print_report(result)` — formatted console output grouped by category/type
- CLI: `python3 pid_extractor.py <pdf> [--output out.json] [--dpi 300] [--all-pages]`
- Auto-saves JSON next to PDF as `<stem>_tags.json`

### `annotate.py`
PDF annotation overlays using PyMuPDF.
- `annotate_pdf(pdf_path, json_path)` — reads `_tags.json`, draws colour-coded rectangles + label text per occurrence on a copy of the PDF
- Colours by type: safety/shutdown=red, relief=orange, actuated=dark blue, manual=mid blue, control=green, pressure instruments=purple, temperature=amber, flow=teal, level=lime, analysis=magenta
- CLI: `python3 annotate.py <pdf> [--json <tags.json>]`
- Saves as `<stem>_annotated.pdf` next to original

---

## Output JSON schema (`_tags.json`)

```json
{
  "source_pdf": "filename.pdf",
  "total_pages": 2,
  "processed_pages": [2],
  "pipe_line_numbers": ["4\"-PP01-361-GF0024-BO3E7"],
  "tag_count": 12,
  "valve_count": 7,
  "instrument_count": 5,
  "tags": [
    {
      "tag": "HV-0059",
      "category": "valve",
      "type_code": "HV",
      "type_description": "Hand Valve (Manual)",
      "number": "0059",
      "notes": ["...context text..."],
      "nearby_line_numbers": [],
      "occurrences": [
        {
          "page": 1,
          "ocr_confidence": 60,
          "coordinates": {
            "page_x_px": 1326, "page_y_px": 1822,
            "width_px": 62,    "height_px": 17,
            "page_x_pt": 318.24, "page_y_pt": 437.28,
            "width_pt": 14.88,   "height_pt": 4.08,
            "normalized_x": 0.2672, "normalized_y": 0.5192
          }
        }
      ]
    }
  ]
}
```

**Coordinate system:** origin = top-left of page. All bboxes are in original (unrotated) page space. Provided in pixels (at render DPI), PDF points (pt = 1/72 inch), and normalised 0–1.

---

## Valve tag naming convention (this drawing set)
- Prefix identifies type: `HV` hand valve, `EZV` ESD zone valve, `PSV` pressure safety valve, `PV` control valve, `XV` actuated, `MOV` motor-operated, etc.
- Number is 4 digits: e.g. `HV-0059`
- Pipe line format: `{size}"-PP01-{system}-{tag}-{spec}` e.g. `20"-PP01-361-GF0002-B03F9`
- System 361 = DS-3 pipeline

## OCR Extraction Results (all 3 PDFs, latest revision page only)

| PDF | Tags | Valves | Instruments |
|-----|------|--------|-------------|
| 0006 (Scraper Launcher DS-3, system 361) | 19 | 16 | 3 |
| 0007 | 23 | 22 | 1 |
| 0008 | 36 | 36 | 0 |

## YOLO Detection Results (all 3 PDFs, latest revision page only)

| PDF | Detections | Classes seen |
|-----|-----------|--------------|
| 0006 | 16 | connector(2), crossing(8), general(2), valve(4) |
| 0007 | 7  | connector(4), crossing(3) |
| 0008 | 40 | connector(14), crossing(17), general(1), instrumentation(2), valve(6) |

### `yolo_infer.py`
YOLO object detection pipeline.
- `run_yolo_on_pdf(pdf_path, model_path, output_dir, conf, dpi, all_pages)` — renders each page, runs YOLO, saves JSON + annotated PDF
- Uses same `group_pages_by_sheet` revision deduplication as OCR pipeline
- Output JSON schema: `source_pdf`, `model`, `conf_threshold`, `dpi`, `total_pages`, `processed_pages`, `detection_count`, `pages[].detections[]`
- Each detection: `class`, `class_id`, `confidence`, `coordinates` (px / pt / normalized)
- CLI: `python3 yolo_infer.py <pdf> [--output-dir dir] [--conf 0.25] [--dpi 300] [--all-pages]`

---

## Output Folders

| Folder | Contents |
|--------|----------|
| `data/outputs/ocr/` | `*_tags.json` + `*_annotated.pdf` from OCR extractor |
| `data/outputs/yolo/` | `*_yolo.json` + `*_yolo.pdf` from YOLO detector |

## Pipeline — Order of Scripts

1. **OCR extraction:** `python3 pid_extractor.py <pdf> --output data/outputs/ocr/<stem>_tags.json`
2. **OCR visualisation:** `python3 annotate.py <pdf> --json <tags.json> --output <stem>_annotated.pdf`
3. **YOLO inference + visualisation:** `python3 yolo_infer.py <pdf> --output-dir data/outputs/yolo/`

## Known limitations / TODO
- PDFs are scanned raster images — OCR accuracy is ~60–90% confidence per tag
- Some tags with low confidence may be missed (e.g. HV-0065 seen in exploratory pass but not in final run)
- PSV tag number not cleanly extracted (number appears on separate line from prefix)
- `nearby_line_numbers` often empty — OCR doesn't preserve spatial proximity in text stream
- TODO: run extractor on PDFs 0007 and 0008
- TODO: consider higher DPI (400) or image pre-processing (contrast, denoise) to improve recall
- TODO: handle split tags where prefix and number are on separate OCR lines
