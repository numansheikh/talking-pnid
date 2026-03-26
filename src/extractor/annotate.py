"""
P&ID PDF Annotator

Overlays extracted tag bounding boxes onto a copy of the PDF.
Boxes and labels are colour-coded by instrument/valve category and type.

Usage:
    python3 annotate.py <pdf_path>
    python3 annotate.py <pdf_path> --json <tags_json_path>

Library usage:
    from annotate import annotate_pdf
    out_path = annotate_pdf("/path/to/drawing.pdf", "/path/to/drawing_tags.json")
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


# ── Colour palette (RGB 0–1) ───────────────────────────────────────────────────
# Valves: blue/red family.  Instruments: grouped by measured variable.

_COLORS: dict[str, tuple[float, float, float]] = {
    # ── Valves ──────────────────────────────────────────────────────────────
    # Safety / shutdown — red
    "ESDV": (0.85, 0.10, 0.10),
    "EZV":  (0.85, 0.10, 0.10),
    "SDV":  (0.85, 0.10, 0.10),
    "BDV":  (0.85, 0.10, 0.10),
    # Relief — orange-red
    "PSV":  (0.90, 0.40, 0.05),
    "PRV":  (0.90, 0.40, 0.05),
    # Actuated — dark blue
    "MOV":  (0.10, 0.20, 0.75),
    "XV":   (0.10, 0.20, 0.75),
    # Manual / isolation — mid blue
    "HV":   (0.15, 0.45, 0.90),
    "BV":   (0.15, 0.45, 0.90),
    "GV":   (0.15, 0.45, 0.90),
    "GLV":  (0.15, 0.45, 0.90),
    "NRV":  (0.15, 0.45, 0.90),
    "BFV":  (0.15, 0.45, 0.90),
    "CSE":  (0.15, 0.45, 0.90),
    # Control valves — green
    "PCV":  (0.10, 0.65, 0.30),
    "FCV":  (0.10, 0.65, 0.30),
    "LCV":  (0.10, 0.65, 0.30),
    "TCV":  (0.10, 0.65, 0.30),
    "PV":   (0.10, 0.65, 0.30),
    "FV":   (0.10, 0.65, 0.30),
    "LV":   (0.10, 0.65, 0.30),
    "TV":   (0.10, 0.65, 0.30),
    # ── Instruments ─────────────────────────────────────────────────────────
    # Pressure — purple / violet
    "PAHH": (0.60, 0.10, 0.80),
    "PALL": (0.60, 0.10, 0.80),
    "PAH":  (0.60, 0.10, 0.80),
    "PAL":  (0.60, 0.10, 0.80),
    "PDT":  (0.60, 0.10, 0.80),
    "PDI":  (0.60, 0.10, 0.80),
    "PIC":  (0.60, 0.10, 0.80),
    "PIT":  (0.60, 0.10, 0.80),
    "PZT":  (0.60, 0.10, 0.80),
    "PT":   (0.60, 0.10, 0.80),
    "PI":   (0.60, 0.10, 0.80),
    "PS":   (0.60, 0.10, 0.80),
    # Temperature — amber
    "TAHH": (0.85, 0.55, 0.00),
    "TALL": (0.85, 0.55, 0.00),
    "TAH":  (0.85, 0.55, 0.00),
    "TAL":  (0.85, 0.55, 0.00),
    "TIC":  (0.85, 0.55, 0.00),
    "TIT":  (0.85, 0.55, 0.00),
    "TT":   (0.85, 0.55, 0.00),
    "TI":   (0.85, 0.55, 0.00),
    "TS":   (0.85, 0.55, 0.00),
    "TE":   (0.85, 0.55, 0.00),
    "TW":   (0.85, 0.55, 0.00),
    # Flow — teal / cyan
    "FAHH": (0.00, 0.70, 0.70),
    "FALL": (0.00, 0.70, 0.70),
    "FAH":  (0.00, 0.70, 0.70),
    "FAL":  (0.00, 0.70, 0.70),
    "FIC":  (0.00, 0.70, 0.70),
    "FIT":  (0.00, 0.70, 0.70),
    "FT":   (0.00, 0.70, 0.70),
    "FI":   (0.00, 0.70, 0.70),
    "FQ":   (0.00, 0.70, 0.70),
    "FE":   (0.00, 0.70, 0.70),
    "FS":   (0.00, 0.70, 0.70),
    # Level — lime green
    "LAHH": (0.40, 0.80, 0.10),
    "LALL": (0.40, 0.80, 0.10),
    "LAH":  (0.40, 0.80, 0.10),
    "LAL":  (0.40, 0.80, 0.10),
    "LIC":  (0.40, 0.80, 0.10),
    "LIT":  (0.40, 0.80, 0.10),
    "LT":   (0.40, 0.80, 0.10),
    "LI":   (0.40, 0.80, 0.10),
    "LG":   (0.40, 0.80, 0.10),
    "LS":   (0.40, 0.80, 0.10),
    "LE":   (0.40, 0.80, 0.10),
    # Analysis — magenta / pink
    "AIC":  (0.85, 0.15, 0.55),
    "AT":   (0.85, 0.15, 0.55),
    "AI":   (0.85, 0.15, 0.55),
    "AS":   (0.85, 0.15, 0.55),
    # Position — steel blue
    "ZIC":  (0.25, 0.50, 0.70),
    "ZT":   (0.25, 0.50, 0.70),
    "ZI":   (0.25, 0.50, 0.70),
    "ZS":   (0.25, 0.50, 0.70),
    # Speed — dark cyan
    "SSHH": (0.00, 0.50, 0.50),
    "SSH":  (0.00, 0.50, 0.50),
    "ST":   (0.00, 0.50, 0.50),
    "SI":   (0.00, 0.50, 0.50),
    "SE":   (0.00, 0.50, 0.50),
    "SS":   (0.00, 0.50, 0.50),
}

_DEFAULT_COLOR = (0.40, 0.40, 0.40)   # grey for anything not in palette


def _color_for(type_code: str) -> tuple[float, float, float]:
    return _COLORS.get(type_code.upper(), _DEFAULT_COLOR)


# ── Annotation logic ───────────────────────────────────────────────────────────

def annotate_pdf(pdf_path: str, json_path: str, out_path: str | None = None) -> Path:
    """Draw coloured bounding boxes and tag labels onto a copy of the PDF.

    Args:
        pdf_path:  Path to the original P&ID PDF.
        json_path: Path to the _tags.json produced by pid_extractor.py.
        out_path:  Optional output path for the annotated PDF.
                   Defaults to <stem>_annotated.pdf next to the source PDF.

    Returns:
        Path to the saved annotated PDF.
    """
    data = json.loads(Path(json_path).read_text())
    doc  = fitz.open(pdf_path)

    # Index occurrences by page number (1-based)
    page_occs: dict[int, list] = {}
    for tag in data["tags"]:
        for occ in tag["occurrences"]:
            pg = occ["page"]
            page_occs.setdefault(pg, []).append({
                "tag":       tag["tag"],
                "type_code": tag["type_code"],
                "category":  tag["category"],
                "coords":    occ["coordinates"],
                "conf":      occ["ocr_confidence"],
            })

    for page_num in range(doc.page_count):
        page = doc[page_num]
        for occ in page_occs.get(page_num + 1, []):
            c     = occ["coords"]
            color = _color_for(occ["type_code"])

            x0 = c["page_x_pt"]
            y0 = c["page_y_pt"]
            x1 = x0 + c["width_pt"]
            y1 = y0 + c["height_pt"]

            pad  = 4
            rect = fitz.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
            page.draw_rect(rect, color=color, fill=None, width=1.5)

            # Label just above (or below if at page top)
            label_y = max(y0 - pad - 1, 8)
            page.insert_text(
                fitz.Point(x0 - pad, label_y),
                occ["tag"],
                fontsize=7,
                color=color,
            )

    if out_path is None:
        out_path = Path(pdf_path).with_stem(Path(pdf_path).stem + "_annotated")
    else:
        out_path = Path(out_path)
    doc.save(str(out_path))
    doc.close()
    return out_path


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Overlay P&ID tag bounding boxes onto a PDF copy"
    )
    parser.add_argument("pdf",    help="Path to the P&ID PDF file")
    parser.add_argument("--json", "-j",
                        help="Path to the _tags.json (default: auto-detect next to PDF)")
    parser.add_argument("--output", "-o",
                        help="Output path for annotated PDF (default: <stem>_annotated.pdf next to source)")
    args = parser.parse_args()

    if args.json:
        json_path = args.json
    else:
        stem      = Path(args.pdf).stem
        json_path = str(Path(args.pdf).parent / f"{stem}_tags.json")
        if not Path(json_path).exists():
            # Fall back to legacy _valves.json name
            json_path = str(Path(args.pdf).parent / f"{stem}_valves.json")
            if not Path(json_path).exists():
                print(f"No JSON found. Run pid_extractor.py first, or pass --json.")
                sys.exit(1)

    print(f"PDF  : {args.pdf}")
    print(f"JSON : {json_path}")
    print("Annotating...", end=" ", flush=True)
    out = annotate_pdf(args.pdf, json_path, out_path=args.output)
    print(f"done.\nSaved: {out}")


if __name__ == "__main__":
    main()
