#!/usr/bin/env python3
"""
run_benchmark.py — Talking P&IDs automated test runner.

Usage:
  python run_benchmark.py                        # Run all questions, judge, print report
  python run_benchmark.py --save-baseline        # Run + save as new baseline JSON
  python run_benchmark.py --compare baselines/2024-01-01T12-00.json  # Compare two runs
  python run_benchmark.py --questions Q1 Q3 Q6  # Run specific questions only
  python run_benchmark.py --url http://localhost:8050  # Override API URL
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ── Paths ─────────────────────────────────────────────────────────────────────
TESTS_DIR    = Path(__file__).parent
QUESTIONS    = json.loads((TESTS_DIR / "benchmark_questions.json").read_text())
BASELINES_DIR = TESTS_DIR / "baselines"
REPORTS_DIR   = TESTS_DIR / "reports"
BASELINES_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8050")


# ── API helpers ───────────────────────────────────────────────────────────────

def start_session(api_url: str) -> str:
    r = requests.post(f"{api_url}/api/session", json={}, timeout=60)
    r.raise_for_status()
    return r.json()["sessionId"]


def ask_question(api_url: str, session_id: str, q: dict) -> dict:
    payload = {
        "query":          q["question"],
        "sessionStarted": True,
        "selectedMapping": {
            "id":  q["pid_id"],
            "pdf": None,
            "md":  None,
        },
        "sessionId": session_id,
        "sources":   q.get("sources", ["graph", "rag"]),
    }
    t0 = time.time()
    r = requests.post(f"{api_url}/api/query", json=payload, timeout=120)
    elapsed = round(time.time() - t0, 1)
    r.raise_for_status()
    data = r.json()
    return {
        "answer":  data.get("answer", ""),
        "sources": data.get("sources", {}),
        "elapsed": elapsed,
    }


# ── LLM judge ─────────────────────────────────────────────────────────────────

def judge_answer(question: dict, answer: str, openai_api_key: str) -> dict:
    """Ask GPT to evaluate the answer against the evaluation criteria."""
    from openai import OpenAI
    client = OpenAI(api_key=openai_api_key)

    criteria   = question["evaluation_criteria"]
    must_have  = criteria.get("must_contain", [])
    must_avoid = criteria.get("must_not_contain", [])
    notes      = criteria.get("notes", "")

    # Quick pre-checks (keyword level) before calling LLM
    keyword_gaps      = [t for t in must_have  if t.lower() not in answer.lower()]
    keyword_hallucinated = [t for t in must_avoid if t.lower() in answer.lower()]

    prompt = f"""You are evaluating an AI assistant's answer to an engineering question about a P&ID diagram.

QUESTION:
{question['question']}

ANSWER TO EVALUATE:
{answer}

EVALUATION CRITERIA:
- Must mention these tags/terms: {must_have}
- Must NOT mention these (hallucinated/wrong): {must_avoid}
- Examiner notes: {notes}

KEYWORD PRE-CHECK RESULTS:
- Missing from answer: {keyword_gaps}
- Hallucinated terms present: {keyword_hallucinated}

Evaluate the answer and respond with ONLY valid JSON in this exact format:
{{
  "verdict": "PASS" | "PARTIAL" | "FAIL",
  "score": 0-100,
  "gaps": ["list of specific information missing from the answer"],
  "hallucinations": ["list of incorrect/fabricated information present"],
  "positives": ["list of things the answer got right"],
  "summary": "one sentence verdict"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    result["keyword_gaps"]         = keyword_gaps
    result["keyword_hallucinated"] = keyword_hallucinated
    return result


# ── Report generation ─────────────────────────────────────────────────────────

def print_report(results: list[dict], elapsed_total: float):
    verdicts = [r["judgment"]["verdict"] for r in results]
    passes   = verdicts.count("PASS")
    partials = verdicts.count("PARTIAL")
    fails    = verdicts.count("FAIL")
    avg_score = round(sum(r["judgment"]["score"] for r in results) / len(results))

    print("\n" + "=" * 70)
    print(f"  BENCHMARK REPORT  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    print(f"  Questions: {len(results)}  |  PASS: {passes}  PARTIAL: {partials}  FAIL: {fails}")
    print(f"  Average score: {avg_score}/100  |  Total time: {elapsed_total:.0f}s")
    print("=" * 70)

    for r in results:
        j = r["judgment"]
        icon = "✓" if j["verdict"] == "PASS" else ("~" if j["verdict"] == "PARTIAL" else "✗")
        print(f"\n  {icon} {r['id']} [{j['verdict']} {j['score']}/100]  ({r['elapsed']}s)")
        print(f"     {j['summary']}")
        if j.get("gaps"):
            print(f"     GAPS: {'; '.join(j['gaps'][:3])}")
        if j.get("hallucinations"):
            print(f"     HALLUCINATIONS: {'; '.join(j['hallucinations'][:2])}")
        if j.get("keyword_gaps"):
            print(f"     MISSING TAGS: {', '.join(j['keyword_gaps'])}")
        if j.get("keyword_hallucinated"):
            print(f"     WRONG TAGS: {', '.join(j['keyword_hallucinated'])}")

    print("\n" + "=" * 70)


def compare_runs(baseline_path: str, current_results: list[dict]):
    baseline = json.loads(Path(baseline_path).read_text())
    baseline_by_id = {r["id"]: r for r in baseline["results"]}

    print("\n" + "=" * 70)
    print(f"  REGRESSION COMPARISON")
    print(f"  Baseline: {baseline_path}")
    print("=" * 70)

    for r in current_results:
        old = baseline_by_id.get(r["id"])
        if not old:
            continue
        old_score = old["judgment"]["score"]
        new_score = r["judgment"]["score"]
        delta = new_score - old_score
        arrow = "↑" if delta > 5 else ("↓" if delta < -5 else "→")
        print(f"  {r['id']}: {old_score} → {new_score}  {arrow}{delta:+d}  ({old['judgment']['verdict']} → {r['judgment']['verdict']})")

    print("=" * 70)


def save_baseline(results: list[dict], api_url: str) -> Path:
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M")
    path = BASELINES_DIR / f"{ts}.json"
    path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "api_url":   api_url,
        "results":   results,
    }, indent=2))
    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Talking P&IDs benchmark runner")
    parser.add_argument("--url",            default=DEFAULT_API_URL, help="Backend API URL")
    parser.add_argument("--questions",      nargs="*", help="Run specific questions e.g. Q1 Q3")
    parser.add_argument("--save-baseline",  action="store_true",  help="Save run as a new baseline")
    parser.add_argument("--compare",        metavar="BASELINE",   help="Compare with baseline JSON")
    parser.add_argument("--no-judge",       action="store_true",  help="Skip LLM judge, just collect answers")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key and not args.no_judge:
        # Try loading from backend .env
        env_file = Path(__file__).parents[1] / "backend" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key and not args.no_judge:
        print("ERROR: OPENAI_API_KEY not found. Set it or use --no-judge.")
        sys.exit(1)

    # Filter questions
    qs = QUESTIONS
    if args.questions:
        ids = [q.upper() for q in args.questions]
        qs  = [q for q in QUESTIONS if q["id"] in ids]
    if not qs:
        print("No matching questions found."); sys.exit(1)

    print(f"\nTalking P&IDs Benchmark — {len(qs)} question(s) against {args.url}")
    print("Starting session...", end=" ", flush=True)
    session_id = start_session(args.url)
    print(f"session {session_id}\n")

    results = []
    t_start = time.time()

    for q in qs:
        print(f"  {q['id']}: {q['question'][:70]}...", end=" ", flush=True)
        try:
            resp = ask_question(args.url, session_id, q)
            print(f"({resp['elapsed']}s)", end=" ", flush=True)

            if args.no_judge:
                judgment = {"verdict": "UNCHECKED", "score": 0, "gaps": [], "hallucinations": [], "positives": [], "summary": "Judge skipped"}
            else:
                judgment = judge_answer(q, resp["answer"], api_key)

            icon = "✓" if judgment["verdict"] == "PASS" else ("~" if judgment["verdict"] == "PARTIAL" else "✗")
            print(f"→ {icon} {judgment['verdict']} ({judgment['score']}/100)")

            results.append({
                "id":       q["id"],
                "question": q["question"],
                "pid_id":   q["pid_id"],
                "answer":   resp["answer"],
                "elapsed":  resp["elapsed"],
                "sources":  resp["sources"],
                "judgment": judgment,
            })
        except Exception as e:
            print(f"→ ERROR: {e}")
            results.append({
                "id": q["id"], "question": q["question"], "pid_id": q["pid_id"],
                "answer": f"ERROR: {e}", "elapsed": 0, "sources": {},
                "judgment": {"verdict": "FAIL", "score": 0, "gaps": [str(e)], "hallucinations": [], "positives": [], "summary": "Request failed"},
            })

    elapsed_total = time.time() - t_start
    print_report(results, elapsed_total)

    if args.compare:
        compare_runs(args.compare, results)

    if args.save_baseline:
        path = save_baseline(results, args.url)
        print(f"\n  Baseline saved → {path}")

    # Save latest report
    report_path = REPORTS_DIR / f"latest.json"
    report_path.write_text(json.dumps({"timestamp": datetime.now().isoformat(), "results": results}, indent=2))
    print(f"  Full results → {report_path}\n")


if __name__ == "__main__":
    main()
