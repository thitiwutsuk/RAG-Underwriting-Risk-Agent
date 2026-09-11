"""DeepEval benchmarking against the golden dataset (faithfulness, answer relevancy).

Runs the real agent (real LLM calls) against every case in
data/golden_dataset.json, builds a DeepEval LLMTestCase per case using the
actual retrieval context the agent's policy_lookup call returned, scores each
case with FaithfulnessMetric and AnswerRelevancyMetric, and writes a report
to eval_results.json plus a stdout summary.

Run: python eval.py
"""

import json
import time
from pathlib import Path

from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

from agent import run_assessment
from main import ApplicantData, _applicant_to_message
from tools import search_policies

THRESHOLD = 0.8
GOLDEN_DATASET_PATH = Path(__file__).parent / "data" / "golden_dataset.json"
APPLICANTS_PATH = Path(__file__).parent / "data" / "applicants.json"
RESULTS_PATH = Path(__file__).parent / "eval_results.json"


def _load_applicants() -> dict[str, dict]:
    return {a["applicant_id"]: a for a in json.loads(APPLICANTS_PATH.read_text())}


def _build_test_case(entry: dict, applicants: dict[str, dict]) -> tuple[LLMTestCase, dict]:
    """Run the real agent for one golden-dataset entry and build its LLMTestCase.
    Returns (test_case, debug_info) where debug_info records what was actually
    sent/retrieved, for the saved report.
    """
    session_id = f"eval-{entry['id']}-{int(time.time() * 1000)}"

    if entry["category"] == "policy_qa":
        message = entry["question"]
        result = run_assessment(session_id=session_id, message=message)
        fallback_query = entry["retrieval_query"]
    elif entry["category"] == "applicant_assessment":
        applicant = ApplicantData(**applicants[entry["applicant_id"]])
        message = _applicant_to_message(applicant)
        result = run_assessment(session_id=session_id, message=message)
        fallback_query = f"{applicant.policy_type_requested} coverage eligibility"
    else:
        raise ValueError(f"Unknown category: {entry['category']}")

    # Score faithfulness against what the agent's own policy_lookup call actually
    # retrieved (not a query we picked by hand), so the metric reflects real RAG
    # behavior. Fall back to a hand-picked query only if the agent called no tool
    # (e.g. it asked a clarifying question instead).
    policy_lookup_calls = [c for c in result["tool_calls"] if c["tool"] == "policy_lookup"]
    query = policy_lookup_calls[0]["args"].get("query", fallback_query) if policy_lookup_calls else fallback_query
    retrieval_context = [hit["text"] for hit in search_policies(query, k=3)]

    test_case = LLMTestCase(
        input=message,
        actual_output=result["answer"],
        expected_output=entry["expected_output"],
        retrieval_context=retrieval_context,
    )
    debug_info = {
        "id": entry["id"],
        "category": entry["category"],
        "actual_output": result["answer"],
        "tool_calls": result["tool_calls"],
        "retrieval_context": retrieval_context,
    }
    return test_case, debug_info


def main() -> None:
    golden_dataset = json.loads(GOLDEN_DATASET_PATH.read_text())
    applicants = _load_applicants()

    faithfulness_metric = FaithfulnessMetric(threshold=THRESHOLD)
    relevancy_metric = AnswerRelevancyMetric(threshold=THRESHOLD)

    report_cases = []
    for entry in golden_dataset:
        print(f"Running {entry['id']} ({entry['category']})...")
        test_case, debug_info = _build_test_case(entry, applicants)

        faithfulness_metric.measure(test_case)
        relevancy_metric.measure(test_case)

        report_cases.append(
            {
                **debug_info,
                "faithfulness_score": faithfulness_metric.score,
                "faithfulness_reason": faithfulness_metric.reason,
                "faithfulness_passed": faithfulness_metric.score >= THRESHOLD,
                "answer_relevancy_score": relevancy_metric.score,
                "answer_relevancy_reason": relevancy_metric.reason,
                "answer_relevancy_passed": relevancy_metric.score >= THRESHOLD,
            }
        )

    n = len(report_cases)
    avg_faithfulness = sum(c["faithfulness_score"] for c in report_cases) / n
    avg_relevancy = sum(c["answer_relevancy_score"] for c in report_cases) / n
    faithfulness_pass_rate = sum(c["faithfulness_passed"] for c in report_cases) / n
    relevancy_pass_rate = sum(c["answer_relevancy_passed"] for c in report_cases) / n

    summary = {
        "threshold": THRESHOLD,
        "num_cases": n,
        "avg_faithfulness": round(avg_faithfulness, 4),
        "avg_answer_relevancy": round(avg_relevancy, 4),
        "faithfulness_pass_rate": round(faithfulness_pass_rate, 4),
        "answer_relevancy_pass_rate": round(relevancy_pass_rate, 4),
    }

    RESULTS_PATH.write_text(json.dumps({"summary": summary, "cases": report_cases}, indent=2))

    print("\n" + "=" * 70)
    print(f"Cases run: {n}")
    print(f"Average faithfulness:      {avg_faithfulness:.3f}  (pass rate: {faithfulness_pass_rate:.0%})")
    print(f"Average answer relevancy:  {avg_relevancy:.3f}  (pass rate: {relevancy_pass_rate:.0%})")
    print(f"Threshold: {THRESHOLD}")
    print(f"Full report written to {RESULTS_PATH}")
    print("=" * 70)
    for c in report_cases:
        status_f = "PASS" if c["faithfulness_passed"] else "FAIL"
        status_r = "PASS" if c["answer_relevancy_passed"] else "FAIL"
        print(
            f"  [{c['id']:<28}] faithfulness={c['faithfulness_score']:.2f} ({status_f})  "
            f"relevancy={c['answer_relevancy_score']:.2f} ({status_r})"
        )


if __name__ == "__main__":
    main()
