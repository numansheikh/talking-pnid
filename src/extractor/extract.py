"""
Core extraction logic for P&ID tag detection.

Provides:
- find_tags_with_coords()  — scan Tesseract word data for P&ID tags
- deduplicate_tags()       — merge hits from multiple OCR rotation passes
- extract_line_numbers()   — find pipe line numbers in OCR text
- extract_note_for_tag()   — pull context sentence(s) around a tag from OCR text
"""

import re

from ocr import px_to_pt, transform_bbox_to_original
from tags import TAG_RE, LINE_RE, ALL_TYPES, tag_category


# ── Tag detection ──────────────────────────────────────────────────────────────

def find_tags_with_coords(
    word_data: dict,
    dpi: int,
    img_w: int,
    img_h: int,
    rotation: int = 0,
    orig_w: int = None,
    orig_h: int = None,
) -> list[dict]:
    """Scan Tesseract word-level data for P&ID instrument/valve tags.

    Tries single words plus 2- and 3-word sliding windows to catch tags split
    across OCR tokens (e.g. 'PT' + '0012' recognised as separate words).

    When the image was rotated before OCR, pass rotation and the original image
    dimensions so bounding boxes are transformed back into original page space.

    Returns a list of dicts, one per detected tag occurrence.
    """
    if orig_w is None:
        orig_w = img_w
    if orig_h is None:
        orig_h = img_h

    words = word_data["text"]
    results: list[dict] = []
    seen: set[tuple] = set()   # (tag, orig_left, orig_top) — dedup within this pass

    def make_coord(left: int, top: int, width: int, height: int) -> dict:
        """Build the coordinates dict, transforming to original space first."""
        if rotation != 0:
            left, top, width, height = transform_bbox_to_original(
                left, top, width, height, rotation, orig_w, orig_h
            )
        left = max(0, left)
        top  = max(0, top)
        return {
            "page_x_px":    left,
            "page_y_px":    top,
            "width_px":     width,
            "height_px":    height,
            "page_x_pt":    px_to_pt(left,   dpi),
            "page_y_pt":    px_to_pt(top,    dpi),
            "width_pt":     px_to_pt(width,  dpi),
            "height_pt":    px_to_pt(height, dpi),
            "normalized_x": round(left  / orig_w, 4),
            "normalized_y": round(top   / orig_h, 4),
        }

    def try_match(text: str, left: int, top: int, width: int, height: int, conf: int):
        for m in TAG_RE.finditer(text):
            prefix = m.group(1).upper()
            number = m.group(2)
            tag    = f"{prefix}-{number}"
            coord  = make_coord(left, top, width, height)
            key    = (tag, coord["page_x_px"], coord["page_y_px"])
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "tag":              tag,
                "category":         tag_category(prefix),
                "type_code":        prefix,
                "type_description": ALL_TYPES.get(prefix, "Unknown"),
                "number":           number,
                "ocr_confidence":   conf,
                "coordinates":      coord,
            })

    n = len(words)
    for i in range(n):
        w = words[i].strip()
        if not w:
            continue
        left   = word_data["left"][i]
        top    = word_data["top"][i]
        width  = word_data["width"][i]
        height = word_data["height"][i]
        conf   = word_data["conf"][i]

        # Single word
        try_match(w, left, top, width, height, conf)

        # 2-word window (catches "PT 0012" or "HV 0059" split by space)
        if i + 1 < n:
            w2 = words[i + 1].strip()
            if w2:
                combined_w = (word_data["left"][i + 1] + word_data["width"][i + 1]) - left
                try_match(
                    w + w2, left, top, combined_w, height,
                    min(conf, word_data["conf"][i + 1]),
                )

        # 3-word window
        if i + 2 < n:
            w3 = words[i + 2].strip()
            if w3:
                combined_w = (word_data["left"][i + 2] + word_data["width"][i + 2]) - left
                try_match(
                    w + words[i + 1].strip() + w3, left, top, combined_w, height,
                    min(conf, word_data["conf"][i + 2]),
                )

    # Drop shorter tags that are a prefix of a longer tag at the exact same position
    # e.g. keep PV-1011/2011 and drop PV-1011 when both appear at the same coords.
    def same_pos(a: dict, b: dict) -> bool:
        return (
            a["coordinates"]["page_x_px"] == b["coordinates"]["page_x_px"]
            and a["coordinates"]["page_y_px"] == b["coordinates"]["page_y_px"]
        )

    filtered = [
        r for r in results
        if not any(
            other is not r and same_pos(r, other) and other["tag"].startswith(r["tag"])
            for other in results
        )
    ]
    return filtered


# ── Cross-rotation deduplication ───────────────────────────────────────────────

def deduplicate_tags(tags: list[dict], proximity_px: int = 50) -> list[dict]:
    """Merge tag detections from multiple rotation passes.

    If two detections of the same tag land within proximity_px of each other
    (in original page space), keep only the higher-confidence one.
    """
    result: list[dict] = []
    for t in sorted(tags, key=lambda x: -x["ocr_confidence"]):
        tx = t["coordinates"]["page_x_px"]
        ty = t["coordinates"]["page_y_px"]
        duplicate = any(
            r["tag"] == t["tag"]
            and abs(r["coordinates"]["page_x_px"] - tx) < proximity_px
            and abs(r["coordinates"]["page_y_px"] - ty) < proximity_px
            for r in result
        )
        if not duplicate:
            result.append(t)
    return result


# ── Pipe line numbers ──────────────────────────────────────────────────────────

def extract_line_numbers(text: str) -> list[str]:
    """Extract pipe line number strings from OCR text."""
    return list({m.group(0).upper() for m in LINE_RE.finditer(text)})


# ── Context notes ──────────────────────────────────────────────────────────────

def extract_note_for_tag(text: str, tag: str) -> str | None:
    """Return up to two context windows (±120 chars) around mentions of tag in text."""
    for variant in [tag, tag.replace("-", "")]:
        pattern = re.compile(rf".{{0,120}}{re.escape(variant)}.{{0,120}}", re.IGNORECASE)
        matches = pattern.findall(text)
        if matches:
            return " | ".join(m.strip() for m in matches[:2])
    return None
