"""FastAPI endpoint tests. The agent call itself is monkeypatched so these
tests verify request/response wiring without spending real LLM API calls --
a genuine end-to-end smoke test against a live model is a separate manual
step once an OPENAI_API_KEY is available (see PLAN.md).
"""

import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main

client = TestClient(main.app)


def test_applicant_to_message_flags_missing_required_fields_explicitly():
    # Regression test: a live smoke test found that silently omitting a missing
    # bmi from the message caused the agent to guess bmi=0 instead of asking a
    # clarifying question. Required fields that are missing must show up as an
    # explicit "MISSING" marker so the model can react to them.
    applicant = main.ApplicantData(
        applicant_id="APP-EDGE-04",
        name="Grace Owusu",
        age=29,
        bmi=None,
        occupation_class="Class 2 - Low",
        policy_type_requested="Health & Medical",
    )
    message = main._applicant_to_message(applicant)

    assert "bmi: MISSING" in message
    assert "age: 29" in message


def test_applicant_to_message_omits_non_required_missing_fields():
    applicant = main.ApplicantData(
        applicant_id="APP-1",
        name="Test",
        age=30,
        bmi=22.0,
        occupation_class="Class 1 - Minimal",
        policy_type_requested="Term Life",
        # gender, height_cm, weight_kg, occupation, coverage_amount_usd left unset
    )
    message = main._applicant_to_message(applicant)

    assert "gender" not in message
    assert "height_cm" not in message


def _fake_run_assessment(session_id: str, message: str):
    return {
        "session_id": session_id,
        "answer": "Reasoning: ...\nRisk Tier: Preferred\nRecommendation: Approve\nCited Sources: rbc_term_life.pdf (page 5)\nDisclaimer: Not a final decision.",
        "tool_calls": [
            {"tool": "risk_calculator", "args": {"age": 30}},
            {"tool": "policy_lookup", "args": {"query": "term life eligibility"}},
        ],
    }


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_assess_low_risk_applicant(monkeypatch):
    monkeypatch.setattr(main, "run_assessment", _fake_run_assessment)

    payload = {
        "session_id": "test-session-low",
        "applicant": {
            "applicant_id": "APP-TEST-LOW",
            "name": "Test Low Risk",
            "age": 25,
            "gender": "Female",
            "bmi": 21.0,
            "smoker": False,
            "occupation_class": "Class 1 - Minimal",
            "health_conditions": ["None declared"],
            "policy_type_requested": "Term Life",
            "coverage_amount_usd": 100000,
        },
    }
    response = client.post("/assess", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "test-session-low"
    assert "Risk Tier" in body["assessment"]
    assert len(body["tool_calls"]) == 2


def test_assess_medium_risk_applicant(monkeypatch):
    monkeypatch.setattr(main, "run_assessment", _fake_run_assessment)

    payload = {
        "session_id": "test-session-medium",
        "applicant": {
            "applicant_id": "APP-TEST-MED",
            "name": "Test Medium Risk",
            "age": 45,
            "gender": "Male",
            "bmi": 31.3,
            "smoker": False,
            "occupation_class": "Class 3 - Moderate",
            "health_conditions": ["Hypertension (controlled)"],
            "policy_type_requested": "Whole Life",
            "coverage_amount_usd": 250000,
        },
    }
    response = client.post("/assess", json=payload)

    assert response.status_code == 200
    assert response.json()["session_id"] == "test-session-medium"


def test_assess_high_risk_applicant(monkeypatch):
    monkeypatch.setattr(main, "run_assessment", _fake_run_assessment)

    payload = {
        "session_id": "test-session-high",
        "applicant": {
            "applicant_id": "APP-TEST-HIGH",
            "name": "Test High Risk",
            "age": 58,
            "gender": "Male",
            "bmi": 39.8,
            "smoker": True,
            "occupation_class": "Class 5 - Hazardous",
            "health_conditions": ["Type 2 Diabetes (uncontrolled)", "Hypertension (uncontrolled)"],
            "policy_type_requested": "Term Life",
            "coverage_amount_usd": 500000,
        },
    }
    response = client.post("/assess", json=payload)

    assert response.status_code == 200
    assert response.json()["session_id"] == "test-session-high"


def test_assess_missing_required_field_returns_422():
    response = client.post(
        "/assess",
        json={"session_id": "s1", "applicant": {"applicant_id": "X"}},
    )
    assert response.status_code == 422


def test_assess_surfaces_agent_failure_as_502(monkeypatch):
    def _boom(session_id, message):
        raise RuntimeError("agent exploded")

    monkeypatch.setattr(main, "run_assessment", _boom)

    payload = {
        "session_id": "s2",
        "applicant": {
            "applicant_id": "APP-X",
            "name": "X",
            "policy_type_requested": "Term Life",
        },
    }
    response = client.post("/assess", json=payload)
    assert response.status_code == 502
