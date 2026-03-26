"""
P&ID Extractor — main orchestration and CLI entry point.

Extracts all tagged instruments and valves from a scanned P&ID PDF using
multi-angle OCR, and writes structured JSON output.

Usage:
    python3 pid_extractor.py <pdf_path>
    python3 pid_extractor.py <pdf_path> --output results.json
    python3 pid_extractor.py <pdf_path> --dpi 400

Library usage:
    from pid_extractor import extract_pid
    result = extract_pid("/path/to/drawing.pdf")
"""

import sys
import json
import argparse
from collections import defaultdict
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Install PyMuPDF: pip install pymupdf")
    sys.exit(1)

try:
    import pytesseract  # noqa: F401 — checked here so error surfaces early
    from PIL import Image  # noqa: F401
except ImportError:
    print("Install: pip install pytesseract pillow")
    sys.exit(1)

from ocr import render_page, rotate_image, ocr_word_data, ROTATIONS, group_pages_by_sheet
from extract import find_tags_with_coords, deduplicate_tags, extract_line_numbers, extract_note_for_tag


# ── Main extraction pipeline ───────────────────────────────────────────────────

def extract_pid(pdf_path: str, dpi: int = 300, all_pages: bool = False) -> dict:
    """Extract all instrument and valve tags from a P&ID PDF.

    Renders each page at `dpi`, runs Tesseract at multiple rotations to catch
    vertical labels, and returns a structured dict ready for JSON serialisation.

    Args:
        pdf_path:  Path to the scanned P&ID PDF.
        dpi:       Render resolution (higher = better OCR, slower).
        all_pages: If False (default), process only the last page. P&ID PDFs
                   commonly bundle multiple revisions of the same drawing; the
                   last page is the most recent. Pass True to process every page.

    Returns:
        dict with keys: source_pdf, total_pages, processed_pages,
                        pipe_line_numbers, tag_count, valve_count,
                        instrument_count, tags.
    """
    doc      = fitz.open(pdf_path)
    pdf_name = Path(pdf_path).name

    all_tags: dict[str, dict] = {}   # tag string → aggregated record
    all_line_numbers: list[str] = []
    all_text_pages: list[str]   = []

    print(f"Processing: {pdf_name}")
    print(f"Pages: {doc.page_count} total", end="")

    if all_pages:
        page_indices = list(range(doc.page_count))
        print(f" — processing all")
    else:
        sheets = group_pages_by_sheet(doc)
        page_indices = [group[-1] for group in sheets]   # latest revision of each sheet
        if len(sheets) == 1 and len(sheets[0]) > 1:
            print(f" — {len(sheets[0])} revisions detected, using latest (page {page_indices[0]+1})")
        elif len(sheets) < doc.page_count:
            print(f" — {len(sheets)} sheet(s) detected, using latest revision of each: "
                  f"pages {[i+1 for i in page_indices]}")
        else:
            print(f" — no duplicate pages detected, processing all")

    for page_num in page_indices:
        print(f"\n  Page {page_num + 1}: rendering at {dpi} DPI...", end=" ", flush=True)
        page = doc[page_num]
        img, orig_w, orig_h = render_page(page, dpi=dpi)

        print(f"OCR ({len(ROTATIONS)} rotations)...", end=" ", flush=True)
        all_rotation_tags: list[dict] = []

        for rot in ROTATIONS:
            rot_img      = rotate_image(img, rot)
            rot_w, rot_h = rot_img.size
            word_data    = ocr_word_data(rot_img)

            # Use 0° OCR text only for context/notes (rotated text is garbled)
            if rot == 0:
                all_text_pages.append(
                    " ".join(w for w in word_data["text"] if w.strip())
                )

            tags = find_tags_with_coords(
                word_data, dpi, rot_w, rot_h,
                rotation=rot, orig_w=orig_w, orig_h=orig_h,
            )
            all_rotation_tags.extend(tags)

        tags_found   = deduplicate_tags(all_rotation_tags)
        line_numbers = extract_line_numbers(all_text_pages[-1])
        all_line_numbers.extend(line_numbers)

        print(f"found {len(tags_found)} tags, {len(line_numbers)} line numbers.")

        for t in tags_found:
            tag_id = t["tag"]
            if tag_id not in all_tags:
                all_tags[tag_id] = {
                    "tag":              tag_id,
                    "category":         t["category"],
                    "type_code":        t["type_code"],
                    "type_description": t["type_description"],
                    "number":           t["number"],
                    "notes":            [],
                    "nearby_line_numbers": [],
                    "occurrences":      [],
                }
            all_tags[tag_id]["occurrences"].append({
                "page":           page_num + 1,
                "ocr_confidence": t["ocr_confidence"],
                "coordinates":    t["coordinates"],
            })

    # Build context notes from combined 0° OCR text
    combined_text = "\n".join(all_text_pages)
    for tag_id, record in all_tags.items():
        note = extract_note_for_tag(combined_text, tag_id)
        if note:
            record["notes"].append(note)

        # Find pipe line numbers mentioned near this tag
        import re
        for variant in [tag_id, tag_id.replace("-", "")]:
            for m in re.finditer(re.escape(variant), combined_text, re.IGNORECASE):
                window = combined_text[max(0, m.start() - 400): m.end() + 400]
                record["nearby_line_numbers"].extend(extract_line_numbers(window))
        record["nearby_line_numbers"] = list(set(record["nearby_line_numbers"]))

    tags_list      = list(all_tags.values())
    valve_count    = sum(1 for t in tags_list if t["category"] == "valve")
    instrument_count = sum(1 for t in tags_list if t["category"] == "instrument")

    return {
        "source_pdf":        pdf_name,
        "total_pages":       doc.page_count,
        "processed_pages":   [i + 1 for i in page_indices],
        "pipe_line_numbers": sorted(set(all_line_numbers)),
        "tag_count":         len(tags_list),
        "valve_count":       valve_count,
        "instrument_count":  instrument_count,
        "tags":              tags_list,
    }


# ── Report printing ────────────────────────────────────────────────────────────

def print_report(result: dict) -> None:
    print("\n" + "=" * 70)
    print("P&ID EXTRACTION REPORT")
    print(f"Source    : {result['source_pdf']}")
    print(f"Pages     : {result['total_pages']} total, processed: {result['processed_pages']}")
    print(f"Tags found: {result['tag_count']}  "
          f"(valves: {result['valve_count']}, instruments: {result['instrument_count']})")
    print("=" * 70)

    if result["pipe_line_numbers"]:
        print("\nPIPE LINE NUMBERS:")
        for ln in result["pipe_line_numbers"]:
            print(f"  {ln}")

    by_category: dict[str, list] = defaultdict(list)
    for t in result["tags"]:
        by_category[t["category"]].append(t)

    for category in ("valve", "instrument", "unknown"):
        items = by_category.get(category, [])
        if not items:
            continue
        print(f"\n── {category.upper()}S ({len(items)}) " + "─" * 40)

        by_type: dict[str, list] = defaultdict(list)
        for t in items:
            by_type[t["type_description"]].append(t)

        for type_desc, group in sorted(by_type.items()):
            print(f"\n  [{type_desc}]")
            for v in sorted(group, key=lambda x: x["tag"]):
                print(f"    {v['tag']}")
                for occ in v["occurrences"]:
                    c = occ["coordinates"]
                    print(f"      page {occ['page']}  "
                          f"({c['page_x_pt']}pt, {c['page_y_pt']}pt)  "
                          f"{c['width_pt']}x{c['height_pt']}pt  "
                          f"conf={occ['ocr_confidence']}")
                if v["nearby_line_numbers"]:
                    print(f"      lines: {', '.join(sorted(v['nearby_line_numbers']))}")
                if v["notes"]:
                    trimmed = v["notes"][0][:160] + ("…" if len(v["notes"][0]) > 160 else "")
                    print(f"      note:  {trimmed}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract instrument and valve tags from a P&ID PDF"
    )
    parser.add_argument("pdf",      help="Path to the P&ID PDF file")
    parser.add_argument("--output", "-o", help="Output JSON path (default: auto next to PDF)")
    parser.add_argument("--dpi",       type=int, default=300,
                        help="OCR render resolution in DPI (default: 300)")
    parser.add_argument("--all-pages", action="store_true",
                        help="Process all pages (default: last page only, as earlier "
                             "pages are typically older revisions of the same drawing)")
    args = parser.parse_args()

    result = extract_pid(args.pdf, dpi=args.dpi, all_pages=args.all_pages)

    out_path = (
        Path(args.output) if args.output
        else Path(args.pdf).parent / (Path(args.pdf).stem + "_tags.json")
    )
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\nJSON saved to: {out_path}")

    print_report(result)


if __name__ == "__main__":
    main()
