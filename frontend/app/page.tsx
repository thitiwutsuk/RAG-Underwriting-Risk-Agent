"use client";

import { useState } from "react";
import ApplicantForm from "./components/ApplicantForm";
import AssessmentResult from "./components/AssessmentResult";
import ThemeToggle from "./components/ThemeToggle";
import { AssessmentError, submitAssessment } from "./lib/api";
import type { ApplicantForm as ApplicantFormData, AssessResponse } from "./lib/types";

const EMPTY_FORM: ApplicantFormData = {
  name: "",
  age: "",
  gender: "",
  height_cm: "",
  weight_kg: "",
  bmi: "",
  smoker: false,
  occupation: "",
  occupation_class: "",
  health_conditions: [],
  policy_type_requested: "",
  coverage_amount_usd: "",
};

function newId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

export default function Home() {
  const [sessionId] = useState(() => newId("session"));
  const [form, setForm] = useState<ApplicantFormData>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<AssessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const response = await submitAssessment(sessionId, newId("APP"), form);
      setResult(response);
    } catch (err) {
      setError(err instanceof AssessmentError ? err.message : "Unexpected error running the assessment.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-1 justify-center px-4 py-10 sm:px-8">
      <main className="flex w-full max-w-5xl flex-col gap-8">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              Underwriting Risk Assistant
            </h1>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
              Enter applicant details to get an AI-assisted risk assessment grounded in
              underwriting criteria and policy documents. This is not a final underwriting
              decision.
            </p>
          </div>
          <ThemeToggle />
        </header>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <section className="rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              Applicant details
            </h2>
            <ApplicantForm
              form={form}
              onChange={setForm}
              onSubmit={handleSubmit}
              submitting={submitting}
            />
          </section>

          <section className="rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              Assessment
            </h2>
            {submitting && (
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                Running the agent — calling risk_calculator and policy_lookup…
              </p>
            )}
            {error && (
              <p className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
                {error}
              </p>
            )}
            {!submitting && !error && !result && (
              <p className="text-sm text-zinc-400 dark:text-zinc-600">
                Submit the form to see the risk tier, reasoning, and cited policy sources
                here.
              </p>
            )}
            {result && <AssessmentResult result={result} />}
          </section>
        </div>
      </main>
    </div>
  );
}
