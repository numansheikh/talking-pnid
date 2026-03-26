"""
OCR pipeline helpers for P&ID extraction.

Covers:
- Rendering PDF pages to PIL images via PyMuPDF
- Rotating images for multi-angle OCR
- Running Tesseract to get word-level bounding boxes
- Transforming bounding boxes from rotated space back to original page space
- Page similarity detection for grouping revision pages
"""

from PIL import Image

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("Install PyMuPDF: pip install pymupdf")

try:
    import pytesseract
except ImportError:
    raise ImportError("Install pytesseract: pip install pytesseract")


# Rotations applied per page (PIL CCW degrees).
# 0°   — normal horizontal text
# 90°  CCW — catches labels written bottom-to-top (ascending vertical)
# 270° CCW — catches labels written top-to-bottom (descending vertical)
ROTATIONS = [0, 90, 270]


# ── Page rendering ─────────────────────────────────────────────────────────────

def render_page(page, dpi: int = 300) -> tuple[Image.Image, int, int]:
    """Render a PDF page to a PIL RGB image at the given DPI.

    Returns (image, width_px, height_px).
    """
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img, pix.width, pix.height


# ── Image rotation ─────────────────────────────────────────────────────────────

def rotate_image(img: Image.Image, angle: int) -> Image.Image:
    """Rotate a PIL image CCW by angle degrees (0, 90, 180, or 270) with expand."""
    if angle == 0:
        return img
    return img.rotate(angle, expand=True)


# ── Tesseract OCR ──────────────────────────────────────────────────────────────

def ocr_word_data(img: Image.Image) -> dict:
    """Run Tesseract on img and return word-level bounding box data.

    Uses psm 11 (sparse text, no assumed layout) and oem 3 (LSTM engine).
    Returns pytesseract Output.DICT with keys: text, left, top, width, height, conf.
    """
    return pytesseract.image_to_data(
        img, config="--psm 11 --oem 3", output_type=pytesseract.Output.DICT
    )


# ── Unit conversion ────────────────────────────────────────────────────────────

def px_to_pt(px: int, dpi: int) -> float:
    """Convert pixels (at a given DPI) to PDF points (1 pt = 1/72 inch)."""
    return round(px * 72 / dpi, 2)


# ── Bounding box coordinate transform ─────────────────────────────────────────

def transform_bbox_to_original(
    left: int, top: int, width: int, height: int,
    rotation: int, orig_w: int, orig_h: int,
) -> tuple[int, int, int, int]:
    """Convert a bounding box from rotated-image space back to original-image space.

    Args:
        left, top, width, height: bbox in the rotated image's pixel coords.
        rotation: PIL CCW rotation angle used to produce the rotated image
                  (0, 90, 180, or 270).
        orig_w, orig_h: dimensions of the original (unrotated) image in pixels.

    Returns:
        (left, top, width, height) in original image pixel coordinates.

    Derivation — PIL rotate(angle, expand=True) is CCW:
        90°  CCW: orig(ox,oy) → rot(oy, W-ox)     inverse: ox = W-ry-rh, oy = rx
        180°    : orig(ox,oy) → rot(W-ox, H-oy)   inverse: ox = W-rx-rw, oy = H-ry-rh
        270° CCW: orig(ox,oy) → rot(H-oy, ox)     inverse: ox = ry,      oy = H-rx-rw
    """
    if rotation == 0:
        return left, top, width, height
    elif rotation == 90:
        ox = orig_w - top - height
        oy = left
        return ox, oy, height, width      # width/height swap
    elif rotation == 180:
        ox = orig_w - left - width
        oy = orig_h - top - height
        return ox, oy, width, height
    elif rotation == 270:
        ox = top
        oy = orig_h - left - width
        return ox, oy, height, width      # width/height swap
    return left, top, width, height


# ── Page similarity and revision grouping ──────────────────────────────────────

def page_similarity(doc, idx_a: int, idx_b: int, sample_dpi: int = 36) -> float:
    """Compute pixel similarity between two PDF pages, returning a value 0.0–1.0.

    Renders both pages at a low DPI thumbnail for speed, converts to greyscale,
    and returns the fraction of pixels within a tolerance of 15/255.

    Returns 0.0 if pages have different dimensions (can't be the same sheet).
    """
    def render_gray_samples(page):
        zoom = sample_dpi / 72
        pix  = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
        return bytes(pix.samples), pix.width, pix.height

    sa, wa, ha = render_gray_samples(doc[idx_a])
    sb, wb, hb = render_gray_samples(doc[idx_b])

    if wa != wb or ha != hb:
        return 0.0   # different page sizes → definitely different sheets

    tolerance = 15
    similar   = sum(1 for a, b in zip(sa, sb) if abs(a - b) <= tolerance)
    return similar / len(sa)


def group_pages_by_sheet(doc, similarity_threshold: float = 0.70) -> list[list[int]]:
    """Group 0-based page indices by drawing sheet.

    Consecutive pages above similarity_threshold are considered revisions of the
    same sheet and grouped together. Pages below threshold start a new sheet group.

    Returns a list of groups, e.g. [[0, 1], [2, 3]] for a 4-page PDF with two
    sheets each having two revisions.

    Example outcomes:
        2-page PDF, same drawing, two revisions → [[0, 1]]
        4-page PDF, two sheets, one revision each → [[0], [1], [2], [3]] or [[0,1],[2,3]]
    """
    if doc.page_count == 1:
        return [[0]]

    groups: list[list[int]] = [[0]]
    for i in range(1, doc.page_count):
        sim = page_similarity(doc, i - 1, i)
        if sim >= similarity_threshold:
            groups[-1].append(i)   # same sheet — add to current group
        else:
            groups.append([i])     # new sheet
    return groups
