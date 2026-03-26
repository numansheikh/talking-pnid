"""
YOLO P&ID Inference

Runs the trained YOLO detector on scanned P&ID PDFs and saves:
  - <stem>_yolo.json    — detection results (class, confidence, coordinates)
  - <stem>_yolo.pdf     — annotated PDF with colour-coded bounding boxes

Usage:
    python3 yolo_infer.py <pdf_path>
    python3 yolo_infer.py <pdf_path> --output-dir /path/to/dir
    python3 yolo_infer.py <pdf_path> --conf 0.25 --dpi 300

Library usage:
    from yolo_infer import run_yolo_on_pdf
    result = run_yolo_on_pdf("/path/to/drawing.pdf", output_dir="/path/to/dir")
"""

import sys
import json
import argparse
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Install PyMuPDF: pip install pymupdf")
    sys.exit(1)

try:
    from ultralytics import YOLO
except ImportError:
    print("Install ultralytics: pip install ultralytics")
    sys.exit(1)

from ocr import render_page, px_to_pt, group_pages_by_sheet

# ── Model path ────────────────────────────────────────────────────────────────

MODEL_PATH = Path(__file__).parent.parent / "model-pretrain" / "runs" / "best.pt"

# ── Colour palette per class (RGB 0–1) ────────────────────────────────────────

_CLASS_COLORS: dict[str, tuple[float, float, float]] = {
    "arrow":         (0.50, 0.50, 0.50),  # grey
    "crossing":      (0.60, 0.40, 0.80),  # purple
    "connector":     (0.20, 0.60, 0.80),  # steel blue
    "valve":         (0.10, 0.30, 0.85),  # blue
    "instrumentation": (0.10, 0.65, 0.30),  # green
    "pump":          (0.85, 0.40, 0.05),  # orange
    "tank":          (0.00, 0.55, 0.55),  # teal
    "general":       (0.40, 0.40, 0.40),  # dark grey
    "inlet_outlet":  (0.85, 0.10, 0.10),  # red
}
_DEFAULT_COLOR = (0.30, 0.30, 0.30)


def _color_for(class_name: str) -> tuple[float, float, float]:
    return _CLASS_COLORS.get(class_name.lower(), _DEFAULT_COLOR)


# ── Core inference ────────────────────────────────────────────────────────────

def run_yolo_on_pdf(
    pdf_path: str,
    model_path: str | None = None,
    output_dir: str | None = None,
    conf: float = 0.25,
    dpi: int = 300,
    all_pages: bool = False,
) -> dict:
    """Run YOLO inference on a P&ID PDF.

    Args:
        pdf_path:   Path to the scanned P&ID PDF.
        model_path: Path to YOLO .pt weights (defaults to MODEL_PATH).
        output_dir: Directory to save JSON + annotated PDF. Defaults to next to source PDF.
        conf:       Minimum confidence threshold (0–1).
        dpi:        Render resolution for page images.
        all_pages:  If False, process only the latest revision of each sheet.

    Returns:
        dict with keys: source_pdf, total_pages, processed_pages, model, detection_count, pages.
    """
    pdf_path   = str(pdf_path)
    model_path = str(model_path or MODEL_PATH)
    doc        = fitz.open(pdf_path)
    pdf_name   = Path(pdf_path).name

    print(f"Model: {model_path}")
    model = YOLO(model_path)

    print(f"Processing: {pdf_name}")
    print(f"Pages: {doc.page_count} total", end="")

    if all_pages:
        page_indices = list(range(doc.page_count))
        print(" — processing all")
    else:
        sheets = group_pages_by_sheet(doc)
        page_indices = [group[-1] for group in sheets]
        if len(sheets) == 1 and len(sheets[0]) > 1:
            print(f" — {len(sheets[0])} revisions detected, using latest (page {page_indices[0]+1})")
        elif len(sheets) < doc.page_count:
            print(f" — {len(sheets)} sheet(s) detected, using latest revision of each: "
                  f"pages {[i+1 for i in page_indices]}")
        else:
            print(" — no duplicate pages detected, processing all")

    pages_results = []

    for page_num in page_indices:
        print(f"\n  Page {page_num + 1}: rendering at {dpi} DPI...", end=" ", flush=True)
        page = doc[page_num]
        img, orig_w, orig_h = render_page(page, dpi=dpi)

        print("running YOLO...", end=" ", flush=True)
        results = model(img, conf=conf, verbose=False)
        boxes   = results[0].boxes

        detections = []
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence      = float(box.conf[0])
            class_id        = int(box.cls[0])
            class_name      = model.names[class_id]

            w_px = x2 - x1
            h_px = y2 - y1

            detections.append({
                "class":      class_name,
                "class_id":   class_id,
                "confidence": round(confidence, 4),
                "coordinates": {
                    "page_x_px":    round(x1),
                    "page_y_px":    round(y1),
                    "width_px":     round(w_px),
                    "height_px":    round(h_px),
                    "page_x_pt":    round(px_to_pt(x1, dpi), 2),
                    "page_y_pt":    round(px_to_pt(y1, dpi), 2),
                    "width_pt":     round(px_to_pt(w_px, dpi), 2),
                    "height_pt":    round(px_to_pt(h_px, dpi), 2),
                    "normalized_x": round(x1 / orig_w, 4),
                    "normalized_y": round(y1 / orig_h, 4),
                },
            })

        print(f"found {len(detections)} detections.")
        pages_results.append({"page": page_num + 1, "detections": detections})

    total_detections = sum(len(p["detections"]) for p in pages_results)

    result = {
        "source_pdf":      pdf_name,
        "model":           str(Path(model_path).name),
        "conf_threshold":  conf,
        "dpi":             dpi,
        "total_pages":     doc.page_count,
        "processed_pages": [i + 1 for i in page_indices],
        "detection_count": total_detections,
        "pages":           pages_results,
    }

    # ── Save JSON ──────────────────────────────────────────────────────────────
    out_dir  = Path(output_dir) if output_dir else Path(pdf_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem     = Path(pdf_path).stem
    json_out = out_dir / f"{stem}_yolo.json"
    json_out.write_text(json.dumps(result, indent=2))
    print(f"\nJSON saved to: {json_out}")

    # ── Annotated PDF ──────────────────────────────────────────────────────────
    pdf_out = out_dir / f"{stem}_yolo.pdf"
    _annotate_pdf_yolo(pdf_path, result, pdf_out)
    print(f"PDF  saved to: {pdf_out}")

    return result


# ── PDF annotation ────────────────────────────────────────────────────────────

def _annotate_pdf_yolo(pdf_path: str, result: dict, out_path: Path) -> None:
    """Draw YOLO detection boxes onto a copy of the PDF."""
    doc = fitz.open(pdf_path)

    # Index detections by page number (1-based)
    page_dets: dict[int, list] = {p["page"]: p["detections"] for p in result["pages"]}

    for page_num in range(doc.page_count):
        page = doc[page_num]
        for det in page_dets.get(page_num + 1, []):
            c     = det["coordinates"]
            color = _color_for(det["class"])

            x0, y0 = c["page_x_pt"], c["page_y_pt"]
            x1 = x0 + c["width_pt"]
            y1 = y0 + c["height_pt"]

            rect = fitz.Rect(x0, y0, x1, y1)
            page.draw_rect(rect, color=color, fill=None, width=1.5)

            label = f"{det['class']} {det['confidence']:.2f}"
            label_y = max(y0 - 2, 8)
            page.insert_text(
                fitz.Point(x0, label_y),
                label,
                fontsize=6,
                color=color,
            )

    doc.save(str(out_path))
    doc.close()


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(result: dict) -> None:
    from collections import Counter
    print("\n" + "=" * 70)
    print("YOLO DETECTION REPORT")
    print(f"Source    : {result['source_pdf']}")
    print(f"Model     : {result['model']}")
    print(f"Pages     : {result['total_pages']} total, processed: {result['processed_pages']}")
    print(f"Detections: {result['detection_count']}")
    print("=" * 70)

    for page_data in result["pages"]:
        dets = page_data["detections"]
        if not dets:
            continue
        counts = Counter(d["class"] for d in dets)
        print(f"\n  Page {page_data['page']}  ({len(dets)} detections):")
        for cls, cnt in sorted(counts.items()):
            print(f"    {cls:20s}  {cnt}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run YOLO inference on a P&ID PDF"
    )
    parser.add_argument("pdf", help="Path to the P&ID PDF file")
    parser.add_argument("--model",      default=str(MODEL_PATH),
                        help=f"Path to YOLO .pt weights (default: {MODEL_PATH})")
    parser.add_argument("--output-dir", "-o",
                        help="Directory for output JSON + annotated PDF")
    parser.add_argument("--conf",       type=float, default=0.25,
                        help="Confidence threshold (default: 0.25)")
    parser.add_argument("--dpi",        type=int,   default=300,
                        help="Render DPI (default: 300)")
    parser.add_argument("--all-pages",  action="store_true",
                        help="Process all pages (default: latest revision only)")
    args = parser.parse_args()

    result = run_yolo_on_pdf(
        args.pdf,
        model_path  = args.model,
        output_dir  = args.output_dir,
        conf        = args.conf,
        dpi         = args.dpi,
        all_pages   = args.all_pages,
    )
    print_report(result)


if __name__ == "__main__":
    main()
