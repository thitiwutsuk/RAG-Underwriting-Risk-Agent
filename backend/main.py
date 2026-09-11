"""FastAPI app exposing POST /assess."""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import run_assessment
from guardrails import INJECTION_CHECKED_FIELDS, ensure_disclaimer, find_prompt_injection

app = FastAPI(title="RAG-Powered Decision Assistant")

# Comma-separated list of allowed frontend origins, e.g.
# "https://my-app.vercel.app,http://localhost:3000". Defaults to the local
# Next.js dev server so local dev needs no configuration.
_frontend_origins = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
ALLOWED_ORIGINS = [origin.strip() for origin in _frontend_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApplicantData(BaseModel):
    applicant_id: str
    name: str
    age: int | None = None
    gender: str | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    bmi: float | None = None
    smoker: bool = False
    occupation: str | None = None
    occupation_class: str | None = None
    health_conditions: list[str] = Field(default_factory=list)
    policy_type_requested: str
    coverage_amount_usd: float | None = None


class AssessRequest(BaseModel):
    session_id: str
    applicant: ApplicantData


class ToolCall(BaseModel):
    tool: str
    args: dict


class AssessResponse(BaseModel):
    session_id: str
    assessment: str
    tool_calls: list[ToolCall]


REQUIRED_FOR_RISK_SCORE = {"age", "bmi", "occupation_class"}


def _applicant_to_message(applicant: ApplicantData) -> str:
    fields = applicant.model_dump()
    lines = []
    for key, value in fields.items():
        if value in (None, [], ""):
            if key in REQUIRED_FOR_RISK_SCORE:
                lines.append(f"- {key}: MISSING (not provided by the applicant)")
            continue
        lines.append(f"- {key}: {value}")
    return (
        "Assess the following insurance applicant. Determine their underwriting "
        "risk tier and whether the requested policy is likely to cover their "
        "situation, citing the relevant policy documents.\n\n" + "\n".join(lines)
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/assess", response_model=AssessResponse)
def assess(request: AssessRequest) -> AssessResponse:
    for field in INJECTION_CHECKED_FIELDS:
        match = find_prompt_injection(getattr(request.applicant, field))
        if match:
            raise HTTPException(
                status_code=422,
                detail=f"Input rejected: '{field}' contains a disallowed instruction-like phrase ({match!r}).",
            )

    message = _applicant_to_message(request.applicant)
    try:
        result = run_assessment(session_id=request.session_id, message=message)
    except Exception as exc:  # noqa: BLE001 - surface agent/tool failures as a 502
        raise HTTPException(status_code=502, detail=f"Assessment failed: {exc}") from exc

    return AssessResponse(
        session_id=result["session_id"],
        assessment=ensure_disclaimer(result["answer"]),
        tool_calls=[ToolCall(**call) for call in result["tool_calls"]],
    )
