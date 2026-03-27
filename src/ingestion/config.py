"""
Paths, constants, and legend context loader for the ingestion pipeline.
All paths are resolved relative to the repo root.
"""

import json
import os
from pathlib import Path
import base64
import fitz  # PyMuPDF

# ── Repo layout ─────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]

def _load_key(filename: str, env_var: str) -> str | None:
    """Load API key from repo-root key file if env var not already set."""
    if os.environ.get(env_var):
        return os.environ[env_var]
    key_file = REPO_ROOT / filename
    if key_file.exists():
        key = key_file.read_text().strip()
        if key:
            os.environ[env_var] = key
            return key
    return None

# Auto-load keys from repo-root files (gitignored)
_load_key("apikey-claude-talking-pnid", "ANTHROPIC_API_KEY")
_load_key("apikey-openai-talking-pnid",  "OPENAI_API_KEY")

DATA_DIR          = REPO_ROOT / "data"
DATASET_DIR       = DATA_DIR / "datasets" / "rumaila-pp01"   # canonical dataset
PDFS_DIR          = DATASET_DIR / "pdfs"                      # A3 originals with title block
LEGENDS_DIR       = DATASET_DIR / "legends" / "format-specific"
OCR_DIR           = DATA_DIR / "outputs" / "ocr"
INGESTION_OUT_DIR = DATA_DIR / "outputs" / "ingestion"
GRAPHS_DIR        = REPO_ROOT / "src" / "talking-pnids-py" / "data" / "graphs"

# ── Strategy version ─────────────────────────────────────────────────────────
# Bump this whenever extraction prompts, models, tiling, or passes change.
# Embedded in every graph JSON and validation report so test runs are traceable.
#
# v0.1.0 — baseline: 3-pass Opus 4.6 vision, 3×2 tiles, native res, legend context,
#           Claude Sonnet schema conversion, Excel+OCR+completeness validation
STRATEGY_VERSION = "v0.1.0"

# ── Models ───────────────────────────────────────────────────────────────────
MODEL_VISION   = "claude-opus-4-6"      # tile extraction (vision quality critical)
MODEL_SCHEMA   = "claude-sonnet-4-6"    # schema conversion + self-verify + supergraph
MAX_TOKENS_EXTRACT = 8192
MAX_TOKENS_SCHEMA  = 16384

# ── Tiling ───────────────────────────────────────────────────────────────────
TILE_ROWS    = 2
TILE_COLS    = 3
TILE_OVERLAP = 0.15   # 15% overlap on each shared edge
TILE_DPI     = 200    # render resolution for Claude vision

# ── POC P&IDs ────────────────────────────────────────────────────────────────
POC_PIDS = {
    "pid-006": "100478CP-N-PG-PP01-PR-PID-0006-001-C02.pdf",
    "pid-007": "100478CP-N-PG-PP01-PR-PID-0007-001-C02.pdf",
    "pid-008": "100478CP-N-PG-PP01-PR-PID-0008-001-C02.pdf",
}

# ── Legend filenames ──────────────────────────────────────────────────────────
LEGEND_FILE_1 = "100478CP-N-PG-PP01-PR-PID-0001-001-C01 (1).pdf"   # abbreviations
LEGEND_FILE_2 = "100478CP-N-PG-PP01-PR-PID-0001-002-C01 (2).pdf"   # piping symbols

# ── Ground truth reference data ───────────────────────────────────────────────
PID_DATA_XLSX     = DATASET_DIR / "reference" / "PID Data.xlsx"   # structured ground truth for PID-008
NARRATIVES_DIR    = DATASET_DIR / "narratives"


# ── Helpers ───────────────────────────────────────────────────────────────────

def pid_id_from_pdf(pdf_path: Path) -> str:
    """Derive a short id like 'pid-008' from a PDF filename."""
    name = pdf_path.stem
    for pid_id, fname in POC_PIDS.items():
        if fname.startswith(name[:30]):
            return pid_id
    # Fallback: extract 4-digit number from filename
    import re
    m = re.search(r"PID-(\d{4})", name, re.IGNORECASE)
    if m:
        return f"pid-{m.group(1)}"
    return name


def pid_work_dir(pid_id: str) -> Path:
    """Returns the work directory for a P&ID, creating it if needed."""
    d = INGESTION_OUT_DIR / pid_id
    for sub in ("tiles", "raw", ""):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def graphs_dir() -> Path:
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    return GRAPHS_DIR


def _pdf_page_to_b64_images(pdf_path: Path, page_index: int = 0, dpi: int = TILE_DPI) -> list[str]:
    """Render every page of a PDF at dpi, return list of base64 PNG strings."""
    doc = fitz.open(str(pdf_path))
    images = []
    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        images.append(base64.b64encode(pix.tobytes("png")).decode())
    doc.close()
    return images


def load_legend_context() -> dict:
    """
    Load both legend sheets as base64 PNG images and return a dict:
      { "sheet1_images": [...], "sheet2_images": [...] }
    Uses a simple file-level cache (_LEGEND_CACHE) so it's loaded once per process.
    """
    global _LEGEND_CACHE
    if _LEGEND_CACHE:
        return _LEGEND_CACHE

    sheet1_path = LEGENDS_DIR / LEGEND_FILE_1
    sheet2_path = LEGENDS_DIR / LEGEND_FILE_2

    cache = {}
    for key, path in [("sheet1_images", sheet1_path), ("sheet2_images", sheet2_path)]:
        if path.exists():
            cache[key] = _pdf_page_to_b64_images(path)
        else:
            print(f"[config] WARNING: legend sheet not found: {path}")
            cache[key] = []

    _LEGEND_CACHE = cache
    return _LEGEND_CACHE


_LEGEND_CACHE: dict = {}


def load_ocr_tags(pid_id: str) -> list[str]:
    """
    Load OCR tag list for a P&ID. Returns list of tag strings like ['HV-0092', ...].
    The OCR JSON format: {"tags": [{"tag": "HV-0092", ...}, ...], ...}
    """
    for fname in os.listdir(OCR_DIR) if OCR_DIR.exists() else []:
        if pid_id.replace("-", "").replace("pid", "PID") in fname or \
           pid_id[-3:] in fname:
            path = OCR_DIR / fname
            if path.suffix == ".json":
                data = json.loads(path.read_text())
                if isinstance(data, list):
                    # Plain list — extract .tag if dict, else str
                    return [t["tag"] if isinstance(t, dict) and "tag" in t else str(t)
                            for t in data]
                if isinstance(data, dict):
                    for key in ("tags", "text", "labels", "items"):
                        if key in data and isinstance(data[key], list):
                            items = data[key]
                            return [t["tag"] if isinstance(t, dict) and "tag" in t else str(t)
                                    for t in items]
    return []


def save_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text())
