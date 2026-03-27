"""
extract.py — Step 2 of the ingestion pipeline.

For each tile: 3-pass Claude Opus vision extraction.
  Pass 1: All components + connections (full extraction)
  Pass 2: Targeted hunt — setpoints, locked positions, spec breaks, vessel internals, notes
  Pass 3: Self-verification — model reviews its own output against the image

Legend sheets are loaded once and passed as context to every call.
Resume: skips any tile/pass where the output JSON already exists.
"""

import base64
import io
import json
import time
from pathlib import Path

import anthropic
from PIL import Image

from config import (
    MODEL_VISION, MODEL_VERIFY, MAX_TOKENS_EXTRACT, calc_cost,
    load_legend_context, pid_work_dir, save_json, load_json,
)

# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior process engineer and P&ID expert.
You extract structured data from Piping & Instrumentation Diagrams (P&IDs).

You have been given two legend sheets as reference context:
- Sheet 1: Abbreviations and valve state codes (LO=locked open, LC=locked closed,
  NO=normally open, NC=normally closed, FC=fail closed, FO=fail open, FL=fail last,
  ILO=interlocked open, HHL/HH/H/L/LL/LLL/LLLL = alarm levels, etc.)
- Sheet 2: Piping symbols (valve types, fitting types, line types, off-drawing connectors)

Use the legend definitions to correctly interpret every symbol, abbreviation, and state code you see.
Return ONLY valid JSON — no commentary, no markdown fences."""

PASS1_PROMPT = """Analyze this P&ID tile image and extract ALL components and connections.

Return a JSON object with this structure:
{
  "tile": "<tile_name>",
  "pass": 1,
  "components": [
    {
      "id": "<unique_id_within_tile>",
      "type": "<equipment|valve|instrument|junction|nozzle|terminator|annotation>",
      "subtype": "<e.g. valve.ball, valve.gate, valve.control, instrument.pressure_transmitter, equipment.vessel>",
      "tag": "<engineering tag if visible>",
      "label": "<any visible label text>",
      "props": {
        "size": "<pipe size if visible>",
        "normal_position": "<LO|LC|NO|NC|FO|FC|FL if visible>",
        "fail_position": "<FO|FC|FL if applicable>",
        "service": "<service description if labeled>",
        "notes": []
      }
    }
  ],
  "connections": [
    {
      "id": "<unique_id>",
      "from": "<component_id or 'EDGE_LEFT|EDGE_RIGHT|EDGE_TOP|EDGE_BOTTOM'>",
      "to": "<component_id or 'EDGE_LEFT|EDGE_RIGHT|EDGE_TOP|EDGE_BOTTOM'>",
      "kind": "<process|signal|impulse|association>",
      "line_tag": "<line number if visible>",
      "pipe_class": "<pipe spec e.g. B03E7, AP15L>",
      "diameter": "<e.g. 8in, DN200>",
      "fluid_code": "<fluid code if visible>"
    }
  ],
  "off_page_refs": [
    {
      "id": "<component_id>",
      "ref_label": "<visible reference label>",
      "direction": "<in|out>",
      "connects_to_doc": "<doc id if mentioned>"
    }
  ],
  "spec_breaks": [
    {
      "id": "<component_id or junction_id>",
      "from_spec": "<pipe class before>",
      "to_spec": "<pipe class after>",
      "location_description": "<what component or where>"
    }
  ],
  "extraction_notes": "<any uncertainty, ambiguity, or partial visibility notes>"
}

Be exhaustive. Every visible valve, instrument, nozzle, junction, and equipment item must appear.
EDGE references mark connections that continue onto an adjacent tile."""

PASS2_PROMPT = """This is a TARGETED extraction pass. You have already extracted the main components.
Now carefully re-examine the same tile image for items that are commonly missed:

1. **Setpoints and alarm levels** — HH, H, L, LL, LLL, LLLL values with their numeric values
2. **Locked positions** — LO (locked open), LC (locked closed), ILO (interlocked locked open)
3. **Spec breaks** — piping specification changes (look for the spec-break symbol, different line weights, or label changes like B03E7→AP15L)
4. **Vessel internals** — internals listed on vessel body (demisters, trays, nozzle schedules)
5. **Note references** — circled numbers or letters pointing to drawing notes
6. **Design conditions** — design pressure, design temperature (often in data boxes on vessels)
7. **Operating conditions** — operating pressure, operating temperature
8. **Small-bore connections** — 1/2", 3/4", 1" instrument take-offs that may have been missed
9. **Electrical/signal details** — IS (intrinsically safe) loops, DCS/FCS/SIS designations
10. **Chemical injection or utility connections** — labelled but small connections

Return JSON:
{
  "tile": "<tile_name>",
  "pass": 2,
  "additions": {
    "components": [ <any missed components — same schema as pass 1> ],
    "connections": [ <any missed connections> ],
    "setpoints": [
      { "tag": "<instrument tag>", "level": "<HH|H|L|LL|LLL|LLLL>", "value": "<numeric value with units>" }
    ],
    "locked_positions": [
      { "tag": "<valve tag>", "position": "<LO|LC|ILO>", "interlock_ref": "<if ILO, what interlock>" }
    ],
    "design_conditions": [
      { "equipment_tag": "<tag>", "design_pressure": "<value>", "design_temp": "<value>",
        "op_pressure": "<value>", "op_temp": "<value>" }
    ],
    "spec_breaks": [
      { "location": "<description>", "from_spec": "<spec>", "to_spec": "<spec>" }
    ],
    "notes": [
      { "ref": "<note number or letter>", "text": "<note text if visible>" }
    ]
  },
  "extraction_notes": "<what was found or confirmed missing>"
}"""

PASS3_PROMPT_TEMPLATE = """This is a SELF-VERIFICATION pass.

Below is the combined extraction from passes 1 and 2 for this tile:
<previous_extraction>
{prev_json}
</previous_extraction>

Now re-examine the tile image carefully and:
1. Identify anything in the image that is NOT captured in the extraction above
2. Identify any tags or labels that look wrong or misread
3. Identify any connections that seem wrong (directionality, missing links)
4. Confirm or correct the pipe specifications and line tags
5. Flag any component whose type or subtype seems incorrect

Return JSON:
{
  "tile": "<tile_name>",
  "pass": 3,
  "verified": true,
  "corrections": [
    { "component_id": "<id>", "field": "<field name>", "was": "<old value>", "now": "<corrected value>", "reason": "<why>" }
  ],
  "additions": {
    "components": [ <any newly spotted components> ],
    "connections": [ <any newly spotted connections> ]
  },
  "confirmed_missing": [
    "<description of something visible in image that couldn't be tagged or typed>"
  ],
  "quality_flags": [
    { "severity": "<low|medium|high>", "issue": "<description>" }
  ],
  "extraction_notes": "<overall assessment>"
}"""

# ─────────────────────────────────────────────────────────────────────────────

def _compress_b64_png(b64_png: str, quality: int = 88) -> str:
    """Re-encode a base64 PNG as a smaller grayscale JPEG.
    P&ID legend sheets are B&W line drawings — grayscale cuts size ~3x vs RGB JPEG.
    """
    raw = base64.b64decode(b64_png)
    buf = io.BytesIO()
    Image.open(io.BytesIO(raw)).convert("L").save(buf, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


_LEGEND_BLOCKS_CACHE: list | None = None


def _make_legend_blocks(legend: dict) -> list:
    """Build Anthropic image content blocks from legend images.
    - Compresses each page to grayscale JPEG (well under 5MB API limit).
    - Marks the final block with cache_control so the Anthropic API caches
      the entire legend context across all 18 extraction calls (~90% cheaper
      on cache-hit input tokens after the first call).
    - Result is module-level cached so JPEG compression only runs once per process.
    """
    global _LEGEND_BLOCKS_CACHE
    if _LEGEND_BLOCKS_CACHE is not None:
        return _LEGEND_BLOCKS_CACHE

    blocks = []
    all_sheets = [
        ("sheet1_images", "Legend Sheet 1 — Abbreviations"),
        ("sheet2_images", "Legend Sheet 2 — Piping Symbols"),
    ]
    for key, label in all_sheets:
        images = legend.get(key, [])
        if images:
            blocks.append({"type": "text", "text": f"\n--- {label} ---"})
            for b64 in images:
                blocks.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg",
                               "data": _compress_b64_png(b64)},
                })

    # Mark the last block as the cache boundary — Anthropic caches everything
    # up to and including this block. Requires ≥1024 tokens (legend easily qualifies).
    if blocks:
        blocks[-1]["cache_control"] = {"type": "ephemeral"}

    _LEGEND_BLOCKS_CACHE = blocks
    return blocks


def _tile_image_block(tile_path: Path, quality: int = 88) -> dict:
    """Load tile PNG, convert to grayscale JPEG in memory, return API image block.
    P&ID tiles are B&W line drawings — grayscale JPEG is ~3x smaller than RGB JPEG
    and well under the 5MB API per-image limit.
    """
    buf = io.BytesIO()
    Image.open(tile_path).convert("L").save(buf, format="JPEG", quality=quality, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
    }


_RETRYABLE = (
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.InternalServerError,
    anthropic.APIStatusError,   # catches 529 OverloadedError and other transient 5xx
)
_RETRY_DELAYS = [10, 30, 90]   # seconds — longer gaps for overloaded API


def _call_claude(
    client: anthropic.Anthropic,
    content: list,
    prompt: str,
    model: str = MODEL_VISION,
) -> tuple[dict, dict]:
    """Call Claude with vision content + text prompt, with retry + exponential backoff.

    Returns (parsed_json, usage) where usage includes cache hit/miss breakdown:
      {"input_tokens": N, "output_tokens": N,
       "cache_read_input_tokens": N, "cache_creation_input_tokens": N}
    """
    last_exc = None
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            print(f"[extract]   ↻ retry {attempt}/{len(_RETRY_DELAYS)} in {delay}s "
                  f"({type(last_exc).__name__})")
            time.sleep(delay)
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS_EXTRACT,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": content + [{"type": "text", "text": prompt}],
                }],
            )
            usage = {
                "input_tokens":               msg.usage.input_tokens,
                "output_tokens":              msg.usage.output_tokens,
                "cache_read_input_tokens":    getattr(msg.usage, "cache_read_input_tokens",    0) or 0,
                "cache_creation_input_tokens": getattr(msg.usage, "cache_creation_input_tokens", 0) or 0,
            }
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            try:
                return json.loads(raw), usage
            except json.JSONDecodeError:
                # Last-ditch: strip trailing commas before closing braces/brackets
                # (common Claude output quirk)
                import re
                cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
                try:
                    return json.loads(cleaned), usage
                except json.JSONDecodeError:
                    return {"raw_text": raw, "parse_error": True}, usage
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt == len(_RETRY_DELAYS):
                raise
    raise last_exc  # unreachable but satisfies type checkers


def extract_tile(
    client: anthropic.Anthropic,
    tile_meta: dict,
    legend: dict,
    raw_dir: Path,
    force: bool = False,
) -> dict:
    """
    Run 3-pass extraction on a single tile.
    Returns merged result dict.
    Resume: each pass file is checked individually.
    """
    tile_name = tile_meta["name"].replace(".png", "")
    tile_path = Path(tile_meta["path"])

    p1_path = raw_dir / f"{tile_name}_pass1.json"
    p2_path = raw_dir / f"{tile_name}_pass2.json"
    p3_path = raw_dir / f"{tile_name}_pass3.json"

    legend_blocks = _make_legend_blocks(legend)
    tile_block = _tile_image_block(tile_path)

    tile_tokens = {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
        "calls": 0,
    }

    def _fmt_usage(u: dict, model: str = MODEL_VISION) -> str:
        cost = calc_cost(model, u["input_tokens"], u["output_tokens"])
        cache_read = u.get("cache_read_input_tokens", 0)
        cache_create = u.get("cache_creation_input_tokens", 0)
        cache_str = ""
        if cache_read:
            cache_str = f" [cache ✓ {cache_read:,} read]"
        elif cache_create:
            cache_str = f" [cache ↑ {cache_create:,} written]"
        return f"{u['input_tokens']:,} in / {u['output_tokens']:,} out / ${cost:.3f}{cache_str}"

    def _accum(u: dict):
        tile_tokens["input_tokens"]               += u["input_tokens"]
        tile_tokens["output_tokens"]              += u["output_tokens"]
        tile_tokens["cache_read_input_tokens"]    += u.get("cache_read_input_tokens",    0)
        tile_tokens["cache_creation_input_tokens"] += u.get("cache_creation_input_tokens", 0)
        tile_tokens["calls"] += 1

    # Pass 1
    _p1_needs_run = force or not p1_path.exists()
    if not _p1_needs_run:
        _p1_candidate = json.loads(p1_path.read_text())
        if _p1_candidate.get("parse_error") and not _p1_candidate.get("_retry_attempted"):
            # Retry once — but only once (guard against infinite retry loop)
            print(f"[extract]   Pass 1 RETRY: {p1_path.name} had parse_error — re-running once")
            _p1_needs_run = True
        else:
            if _p1_candidate.get("parse_error"):
                print(f"[extract]   Pass 1 resume (parse_error, already retried): {p1_path.name}")
            else:
                print(f"[extract]   Pass 1 resume: {p1_path.name}")
            p1 = _p1_candidate

    if _p1_needs_run:
        t0 = time.time()
        content = legend_blocks + [tile_block]
        p1, u1 = _call_claude(client, content, PASS1_PROMPT)
        _accum(u1)
        p1.setdefault("tile", tile_name)
        p1["_retry_attempted"] = True  # mark so we never retry this more than once
        save_json(p1_path, p1)
        if p1.get("parse_error"):
            print(f"[extract]   Pass 1 → {tile_name}  [{_fmt_usage(u1)}  {time.time()-t0:.0f}s]  ⚠ parse_error after retry")
        else:
            print(f"[extract]   Pass 1 → {tile_name}  [{_fmt_usage(u1)}  {time.time()-t0:.0f}s]")

    # Pass 2
    if p2_path.exists() and not force:
        print(f"[extract]   Pass 2 resume: {p2_path.name}")
        p2 = json.loads(p2_path.read_text())
    else:
        t0 = time.time()
        content = legend_blocks + [tile_block]
        p2, u2 = _call_claude(client, content, PASS2_PROMPT)
        _accum(u2)
        p2.setdefault("tile", tile_name)
        save_json(p2_path, p2)
        print(f"[extract]   Pass 2 → {tile_name}  [{_fmt_usage(u2)}  {time.time()-t0:.0f}s]")

    # Pass 3 — self-verification with Sonnet (review/reasoning, not raw extraction)
    if p3_path.exists() and not force:
        print(f"[extract]   Pass 3 resume: {p3_path.name}")
        p3 = json.loads(p3_path.read_text())
    else:
        t0 = time.time()
        # Smart truncation: always keep all components (tags are critical),
        # trim connections if the payload is too large.
        prev_slim = {
            "components": p1.get("components", []),
            "off_page_refs": p1.get("off_page_refs", []),
            "spec_breaks": p1.get("spec_breaks", []),
            "pass2_additions": p2.get("additions", {}),
        }
        connections = p1.get("connections", [])
        prev_json = json.dumps(prev_slim, indent=2)
        if len(prev_json) + len(json.dumps(connections)) < 12_000:
            prev_slim["connections"] = connections
        else:
            prev_slim["connections"] = connections[:40]
            prev_slim["_connections_truncated"] = True
        prev_json = json.dumps(prev_slim, indent=2)
        prompt3 = PASS3_PROMPT_TEMPLATE.replace("{prev_json}", prev_json)
        content = legend_blocks + [tile_block]
        p3, u3 = _call_claude(client, content, prompt3, model=MODEL_VERIFY)
        _accum(u3)
        p3.setdefault("tile", tile_name)
        save_json(p3_path, p3)
        print(f"[extract]   Pass 3 → {tile_name}  [{_fmt_usage(u3, MODEL_VERIFY)}  {time.time()-t0:.0f}s]  [{MODEL_VERIFY}]")

    if tile_tokens["calls"] > 0:
        tile_cost = calc_cost(MODEL_VISION, tile_tokens["input_tokens"], tile_tokens["output_tokens"])
        print(f"[extract]   Tile subtotal ({tile_tokens['calls']} new calls): "
              f"{tile_tokens['input_tokens']:,} in / {tile_tokens['output_tokens']:,} out / ${tile_cost:.3f}")

    return {"tile": tile_name, "pass1": p1, "pass2": p2, "pass3": p3, "tokens": tile_tokens}


def extract_all_tiles(
    pid_id: str,
    tile_metadata: dict,
    force: bool = False,
) -> list[dict]:
    """
    Extract all tiles for a P&ID.
    Returns list of per-tile merged results.
    """
    api_key = __import__("os").environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    legend = load_legend_context()

    work_dir = pid_work_dir(pid_id)
    raw_dir  = work_dir / "raw"

    tiles = tile_metadata.get("tiles", [])
    print(f"[extract] {pid_id}: extracting {len(tiles)} tiles (3 passes each)")

    results = []
    total_in = total_out = total_calls = 0
    total_cache_read = total_cache_create = 0
    t_extract_start = time.time()

    for i, tile_meta in enumerate(tiles):
        print(f"[extract] Tile {i+1}/{len(tiles)}: {tile_meta['name']}")
        result = extract_tile(client, tile_meta, legend, raw_dir, force=force)
        results.append(result)

        tok = result.get("tokens", {})
        total_in           += tok.get("input_tokens",               0)
        total_out          += tok.get("output_tokens",              0)
        total_calls        += tok.get("calls",                      0)
        total_cache_read   += tok.get("cache_read_input_tokens",    0)
        total_cache_create += tok.get("cache_creation_input_tokens", 0)

        running_cost = calc_cost(MODEL_VISION, total_in, total_out)
        cache_note = (f"  cache: {total_cache_read:,} read / {total_cache_create:,} written"
                      if (total_cache_read or total_cache_create) else "")
        print(f"[extract] Running total after tile {i+1}: "
              f"{total_in:,} in / {total_out:,} out / ${running_cost:.3f}{cache_note}")

        if i < len(tiles) - 1:
            time.sleep(1)

    # Save combined extraction results
    combined_path = work_dir / "all_tile_extractions.json"
    save_json(combined_path, results)

    # Token report
    elapsed = time.time() - t_extract_start
    total_cost = calc_cost(MODEL_VISION, total_in, total_out)
    token_report = {
        "step": "extract",
        "model": MODEL_VISION,
        "tiles": len(tiles),
        "api_calls": total_calls,
        "input_tokens":               total_in,
        "output_tokens":              total_out,
        "cache_read_input_tokens":    total_cache_read,
        "cache_creation_input_tokens": total_cache_create,
        "cost_usd": round(total_cost, 4),
        "elapsed_s": round(elapsed, 1),
    }
    save_json(work_dir / "extract_token_report.json", token_report)

    cache_savings_note = ""
    if total_cache_read:
        # cache reads cost 10% of normal input price
        saved = calc_cost(MODEL_VISION, total_cache_read, 0) * 0.90
        cache_savings_note = f"  |  cache saved ~${saved:.3f}"

    print(f"[extract] ── TOTAL: {total_calls} API calls  |  "
          f"{total_in:,} in / {total_out:,} out  |  "
          f"${total_cost:.3f}{cache_savings_note}  |  {elapsed/60:.1f} min")
    print(f"[extract] Done: all tile extractions → {combined_path}")
    return results


if __name__ == "__main__":
    import sys
    from config import PDFS_DIR, pid_id_from_pdf, load_json
    from tile import tile_pdf

    if len(sys.argv) < 2:
        print("Usage: python extract.py <path/to/pid.pdf> [--force]")
        sys.exit(1)

    pdf = Path(sys.argv[1])
    force = "--force" in sys.argv
    pid = pid_id_from_pdf(pdf)

    work_dir = pid_work_dir(pid)
    meta = load_json(work_dir / "tiles" / "tile_metadata.json")
    extract_all_tiles(pid, meta, force=force)
