import type { ApplicantForm, AssessResponse } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class AssessmentError extends Error {}

function toNumber(value: string): number | undefined {
  if (value.trim() === "") return undefined;
  const n = Number(value);
  return Number.isNaN(n) ? undefined : n;
}

export async function submitAssessment(
  sessionId: string,
  applicantId: string,
  form: ApplicantForm
): Promise<AssessResponse> {
  const payload = {
    session_id: sessionId,
    applicant: {
      applicant_id: applicantId,
      name: form.name,
      age: toNumber(form.age),
      gender: form.gender || undefined,
      height_cm: toNumber(form.height_cm),
      weight_kg: toNumber(form.weight_kg),
      bmi: toNumber(form.bmi),
      smoker: form.smoker,
      occupation: form.occupation || undefined,
      occupation_class: form.occupation_class || undefined,
      health_conditions: form.health_conditions,
      policy_type_requested: form.policy_type_requested,
      coverage_amount_usd: toNumber(form.coverage_amount_usd),
    },
  };

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/assess`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new AssessmentError(
      `Could not reach the backend at ${API_BASE_URL}. Is it running?`
    );
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? `HTTP ${response.status}`;
    throw new AssessmentError(detail);
  }

  return response.json();
}
