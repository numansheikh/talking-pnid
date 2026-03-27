# Ingestion Strategy Versions

Each version is defined by the combination of: tiling approach, extraction prompts,
model choices, passes, and validation sources.

The `strategy_version` field is embedded in every graph JSON and validation report,
so test runs are fully traceable.

---

## v0.1.0 — Baseline (2026-03-27)

**Status:** Active

### Tiling
- Source: Native embedded raster image (not re-rendered) — full resolution (~3296×2331px)
- Grid: 3×2 (6 tiles)
- Overlap: 15% on each shared edge
- Legend sheets: Both legend PDFs loaded once, passed to every extraction call

### Extraction (per tile)
- Model: `claude-opus-4-6`
- Passes: 3
  - Pass 1: All components + connections (full extraction)
  - Pass 2: Targeted hunt — setpoints, locked positions, spec breaks, vessel internals, notes
  - Pass 3: Self-verification — model reviews its own output against the tile image
- Context: Legend Sheet 1 (abbreviations) + Legend Sheet 2 (piping symbols)

### Schema Conversion
- Model: `claude-sonnet-4-6`
- Schema: `pid.graph.v0.1.1`

### Validation
- Source 1: `PID Data.xlsx` — structured ground truth (11 reference tags for V001 system)
- Source 2: OCR tag list (`*_tags.json`) — 36 tags for PID-008
- Source 3: Completeness rules (vessel/PSV/valve/loop attribute checks)

### Known Limitations / Hypotheses to Test
- Small-bore connections (1/2", 3/4") may be missed at tile edges
- Vertical text labels may be misread (no rotation-aware tiling yet)
- Pass 3 self-verification prompt may be too generic — could target specific rules

---

## How to Create a New Version

1. Bump `STRATEGY_VERSION` in `config.py` (e.g. `v0.2.0`)
2. Add an entry here describing what changed and why
3. Re-run the pipeline with `--force` to regenerate outputs
4. Compare validation reports between versions

### Versioning convention
- Patch (v0.1.x): Prompt wording tweaks, minor fixes
- Minor (v0.x.0): New pass, changed model, tiling change, new validation source
- Major (vx.0.0): Architecture change (e.g. adding rotation, switching extraction strategy)

---

## Benchmark: 10 Sample Questions (PID-008)

Used to score each strategy version. Target: all 10 correct.

| # | Question | Type |
|---|---------|------|
| Q1 | Design/op pressure+temp for 362-V001 | Attribute lookup |
| Q2 | All isolation valves for 362-V001 | Graph traversal |
| Q3 | EZV-002 closes → upstream pressure effects + safeguards | Traversal + reasoning |
| Q4 | HV0027 inadvertently closed → critical instrumentation | Traversal + reasoning |
| Q5 | All instruments with HH/H/L/LL functions (tabular) | Attribute filter |
| Q6 | All locked open/closed valves | Attribute filter |
| Q7 | Purpose of BDZV0001, stuck open/closed effects | Lookup + reasoning |
| Q8 | Spectacle blinds list with sizes | Type filter |
| Q9 | Note 10 applicable lines | Note reference lookup |
| Q10 | All spec breaks with boundary equipment | Spec break filter |

| Version | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 | Q9 | Q10 | Score |
|---------|----|----|----|----|----|----|----|----|----|----|-------|
| baseline (markdown) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ~5-6/10 |
| v0.1.0 | — | — | — | — | — | — | — | — | — | — | pending |
