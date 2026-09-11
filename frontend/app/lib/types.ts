export const OCCUPATION_CLASSES = [
  "Class 1 - Minimal",
  "Class 2 - Low",
  "Class 3 - Moderate",
  "Class 4 - High",
  "Class 5 - Hazardous",
] as const;

export const HEALTH_CONDITIONS = [
  "None declared",
  "Hypertension (controlled)",
  "Hypertension (uncontrolled)",
  "Type 2 Diabetes (controlled)",
  "Type 2 Diabetes (uncontrolled)",
  "Type 1 Diabetes",
  "Asthma (mild, intermittent)",
  "Asthma (severe, persistent)",
  "Coronary heart disease (history)",
  "Cancer (in remission > 5 years)",
  "Cancer (active treatment)",
  "Chronic kidney disease",
  "Mental health condition (managed)",
  "Family history - heart disease",
  "Family history - cancer",
] as const;

export const POLICY_TYPES = [
  "Term Life",
  "Whole Life",
  "Universal Life",
  "Critical Illness",
  "Disability Income",
  "Accidental Death & Dismemberment",
  "Health & Medical",
] as const;

export interface ApplicantForm {
  name: string;
  age: string;
  gender: string;
  height_cm: string;
  weight_kg: string;
  bmi: string;
  smoker: boolean;
  occupation: string;
  occupation_class: string;
  health_conditions: string[];
  policy_type_requested: string;
  coverage_amount_usd: string;
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
}

export interface AssessResponse {
  session_id: string;
  assessment: string;
  tool_calls: ToolCall[];
}
