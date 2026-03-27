# Benchmark — Talking P&IDs Evaluation

10 engineering questions against PID-008. Used to track quality improvements as the ingestion
pipeline and query layer evolve.

## How to Run

```bash
cd src/talking-pnids-py

# Start the backend first (port 8050 default)
uvicorn backend.main:app --port 8050

# Run all 10 questions
python tests/run_benchmark.py

# Run specific questions
python tests/run_benchmark.py --questions Q1 Q6 Q8

# Run against deployed backend
python tests/run_benchmark.py --url https://decent-lilli-cogit-0d306da3.koyeb.app

# Save as a named baseline snapshot
python tests/run_benchmark.py --save-baseline
```

Results are written to `tests/reports/latest.json`. Each run also auto-saves a timestamped
snapshot in `tests/baselines/`.

## Scoring

Each answer is evaluated by GPT-4o against pre-defined criteria in `benchmark_questions.json`:
- **must_contain** — keyword/tag IDs that must appear in the answer
- **must_not_contain** — things that would indicate hallucination

| Verdict | Score range | Meaning |
|---------|-------------|---------|
| PASS | 80–100 | All required content present, no hallucinations |
| PARTIAL | 50–79 | Some keywords missing or minor gaps |
| FAIL | 0–49 | Critical content missing or significant hallucination |

**Note:** GPT-4o judge is non-deterministic. Expect ±5–10 point swings between runs on the
same graph. Trends across multiple runs are meaningful; single-point differences are noise.

## The 10 Questions

| ID | Question | What it tests |
|----|----------|--------------|
| Q1 | Design/operating pressure and temperature for vessel 362-V001 | Data box extraction |
| Q2 | All isolation valves for 362-V001 | Topology traversal |
| Q3 | EZV-002 closes — upstream pressure effects and safeguards | Impact region + safety |
| Q4 | HV0027 inadvertently closed — critical instrumentation affected | Impact region |
| Q5 | All instruments with HH/H/L/LL alarm functions (tabular) | Alarm level listing |
| Q6 | All locked open/closed valves | `props.normal_position` LO/LC lookup |
| Q7 | Purpose of BDZV0001; effects if stuck open vs stuck closed | Single tag deep-dive |
| Q8 | List of spectacle blinds with sizes | Subtype: valve.spectacle |
| Q9 | Which line numbers does Note 10 apply to | Note reference lookup |
| Q10 | All spec breaks with boundary equipment | Spec break node traversal |

## Score History

| Date | Strategy | Avg | PASS | PARTIAL | FAIL | Notes |
|------|----------|-----|------|---------|------|-------|
| 2026-03-27 | v0.1.0 | 74 | 2 | 5 | 3 | Initial graph query layer live |
| 2026-03-27 | v0.1.1 | 73 | 3 | 5 | 2 | Adaptive sub-tiling; dense tile fix; judge variance |
| 2026-03-28 | v0.1.1+pass2 | **79** | **5** | **4** | **1** | Pass2 re-run (captured 15 locked positions); agent prompt LO/LC guidance |

## Remaining Failures (as of 2026-03-28)

| Q | Score | Root cause |
|---|-------|-----------|
| Q8 | 40 | HV0027/HV0050 extracted as gate/needle valves, not spectacle blinds — extraction gap |
| Q6 | 70 | Locked position data in `props.normal_position` not top-level; agent sometimes misses valves |
| Q2 | 65 | Some isolation valve tags missing from graph |
| Q10 | 60 | Missing one spec break: CO1N9→B01M8 at HV0004/HV0031 boundary |

## File Structure

```
tests/
├── BENCHMARK.md              ← this file
├── benchmark_questions.json  ← 10 questions with evaluation criteria
├── run_benchmark.py          ← test runner
├── reports/
│   └── latest.json           ← most recent run (overwritten each run)
└── baselines/
    └── YYYY-MM-DDTHH-MM.json ← archived snapshots
```
