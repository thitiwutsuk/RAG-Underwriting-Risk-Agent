"""Latency benchmark: manual review time (a documented, bottom-up assumption --
NOT a cited industry statistic, see MANUAL_REVIEW_BREAKDOWN_MINUTES below) vs.
AI-assisted time (measured wall-clock latency of the real agent against a
sample of real applicant cases).

Run: python scripts/benchmark_latency.py
Writes backend/benchmark_results.json.
"""

import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import run_assessment
from main import ApplicantData, _applicant_to_message

APPLICANTS_PATH = Path(__file__).parent.parent / "data" / "applicants.json"
RESULTS_PATH = Path(__file__).parent.parent / "benchmark_results.json"

# A bottom-up task breakdown for what a human underwriter would actually do
# for one case, reviewed manually end-to-end. This is an explicit, documented
# ASSUMPTION -- we could not find a public industry figure for "minutes per
# application" (searched; underwriting-timeline sources report weeks-long
# end-to-end processing time, not the underwriter's own hands-on-case minutes,
# and per-case productivity data is proprietary to insurers). The tasks below
# are what `risk_calculator` and `policy_lookup` mechanize, so they're a
# reasonable stand-in for "what does the AI actually save a human from doing."
# As a loose sanity check: publicly documented underwriting sub-steps like a
# phone interview (15-30 min) or a medical exam (20-30 min) confirm that
# individual human review steps in this process land in the minutes-not-
# seconds range, consistent with the total below.
MANUAL_REVIEW_BREAKDOWN_MINUTES = {
    "read_application_and_history": 3,
    "cross_reference_underwriting_criteria_tables": 5,
    "locate_and_read_relevant_policy_sections": 7,
    "write_up_decision_and_rationale": 5,
}
MANUAL_REVIEW_MINUTES = sum(MANUAL_REVIEW_BREAKDOWN_MINUTES.values())

# A representative sample across risk tiers (see PLAN.md's applicant list):
# clean low-risk, standard, substandard, high-risk, decline, and the two
# missing-required-field edge cases (these should be *faster* for the AI,
# since it asks a clarifying question instead of doing a full assessment --
# recorded separately below rather than averaged in, since they measure a
# different thing).
SAMPLE_APPLICANT_IDS = [
    "APP-EDGE-08",  # Preferred
    "APP-012",  # Standard
    "APP-014",  # Substandard
    "APP-010",  # High Risk
    "APP-EDGE-01",  # Decline
    "APP-016",
    "APP-009",
    "APP-013",
    "APP-EDGE-06",
    "APP-007",
]
EDGE_CASE_APPLICANT_IDS = ["APP-EDGE-04", "APP-EDGE-05"]  # missing required field


def _time_one(applicant_id: str, applicants: dict[str, dict]) -> dict:
    applicant = ApplicantData(**applicants[applicant_id])
    message = _applicant_to_message(applicant)
    session_id = f"benchmark-{applicant_id}-{int(time.time() * 1000)}"

    start = time.perf_counter()
    result = run_assessment(session_id=session_id, message=message)
    elapsed = time.perf_counter() - start

    return {
        "applicant_id": applicant_id,
        "elapsed_seconds": round(elapsed, 2),
        "num_tool_calls": len(result["tool_calls"]),
    }


def main() -> None:
    applicants = {a["applicant_id"]: a for a in json.loads(APPLICANTS_PATH.read_text())}

    # Warm up first (embedding model load, ChromaDB connection, LangGraph agent
    # build) so timed runs reflect steady-state per-request latency in a
    # long-running server, not one-time process startup cost.
    print("Warming up (excluded from stats)...")
    _time_one(SAMPLE_APPLICANT_IDS[0], applicants)

    print("Timing full assessments...")
    full_runs = [_time_one(aid, applicants) for aid in SAMPLE_APPLICANT_IDS]
    for r in full_runs:
        print(f"  {r['applicant_id']}: {r['elapsed_seconds']}s ({r['num_tool_calls']} tool calls)")

    print("Timing missing-field edge cases (clarifying question, no tool calls expected)...")
    edge_runs = [_time_one(aid, applicants) for aid in EDGE_CASE_APPLICANT_IDS]
    for r in edge_runs:
        print(f"  {r['applicant_id']}: {r['elapsed_seconds']}s ({r['num_tool_calls']} tool calls)")

    ai_times = [r["elapsed_seconds"] for r in full_runs]
    ai_mean = statistics.mean(ai_times)
    ai_median = statistics.median(ai_times)
    ai_p95 = sorted(ai_times)[max(0, int(len(ai_times) * 0.95) - 1)]

    manual_seconds = MANUAL_REVIEW_MINUTES * 60
    efficiency_gain_pct = (manual_seconds - ai_mean) / manual_seconds * 100

    summary = {
        "manual_review_minutes_assumed": MANUAL_REVIEW_MINUTES,
        "manual_review_breakdown_minutes": MANUAL_REVIEW_BREAKDOWN_MINUTES,
        "ai_assisted_seconds_mean": round(ai_mean, 2),
        "ai_assisted_seconds_median": round(ai_median, 2),
        "ai_assisted_seconds_p95": round(ai_p95, 2),
        "num_full_assessment_cases": len(full_runs),
        "efficiency_gain_pct": round(efficiency_gain_pct, 1),
    }

    RESULTS_PATH.write_text(
        json.dumps({"summary": summary, "full_runs": full_runs, "edge_case_runs": edge_runs}, indent=2)
    )

    print("\n" + "=" * 70)
    print(f"Manual review time (assumed, see methodology): {MANUAL_REVIEW_MINUTES} min = {manual_seconds}s")
    print(f"AI-assisted time: mean={ai_mean:.2f}s  median={ai_median:.2f}s  p95={ai_p95:.2f}s")
    print(f"Efficiency gain: {efficiency_gain_pct:.1f}%")
    print(f"Full report written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
