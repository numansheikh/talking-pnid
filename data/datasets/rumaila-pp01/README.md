# Dataset: rumaila-pp01

**Rumaila Oil Field — Early Power Plant (PP01)**
Contract 100478 | Scanned A3 P&IDs | Rev C01/C02, 2016

## Active Subset (set-1.1)

PID-006, PID-007, PID-008 — three connected P&IDs for the fuel gas and scraper system.

```
PID-006  Scraper Launcher DS-3 (System 361)
   ↓ feeds into
PID-008  Fuel Gas KO Drum PP01-362-V001 (System 362)
   ↑ also from
PID-007  System 361 related
```

## Quick reference

| Item | Value |
|------|-------|
| Main equipment (PID-008) | PP01-362-V001, Fuel Gas KO Drum, 14 barg design, -20~100°C |
| Key control loop | LIT001 → LIC001 → LV001 (level control) |
| Key safety loop | LZT002A/B/C → PP01-I-007 → EZV001 (ESD) |
| OCR validated tags | 36 tags for PID-008 (see `data/outputs/ocr/`) |
| Ground truth | `reference/PID Data.xlsx` — 11 reference tags with specs |

## Narratives

All narrative documents are audio transcriptions by process engineers walking through the P&IDs.

| File | Content |
|------|---------|
| `pid-006-narrative.docx` | PID-006 walkthrough |
| `pid-007-narrative.docx` | PID-007 walkthrough |
| `pid-008-narrative-a.docx` | PID-008 part A walkthrough |
| `pid-008-narrative-b.docx` | PID-008 part B walkthrough |
| `pid-008-detail-full.docx` | Detailed breakdown of PID-008 (120KB, most complete) |
| `scraper-receiver-details.docx` | Scraper receiver nozzle and connection details |
| `detailed-doc-specification.docx` | Document specification |
| `technical-spec-line-designation.docx` | Line designation and technical spec |

## Previous extraction attempts

`extractions/attempt-1/` — JSON graphs extracted manually from narratives before the automated pipeline existed. Useful as a quality baseline / comparison.
