import type { AssessResponse } from "../lib/types";

const SECTION_HEADINGS = [
  "Reasoning",
  "Risk Tier",
  "Recommendation",
  "Cited Sources",
  "Disclaimer",
];

function parseSections(assessment: string): { heading: string; body: string }[] {
  // The model sometimes wraps headings in markdown bold (**Reasoning:**) --
  // strip markdown emphasis before matching so stray "**" don't end up in the body.
  const text = assessment.replace(/\*\*/g, "");
  const pattern = new RegExp(`(${SECTION_HEADINGS.join("|")}):`, "g");
  const matches = [...text.matchAll(pattern)];

  // Fall back to the raw text if the model didn't follow the expected headings.
  if (matches.length === 0) {
    return [{ heading: "Assessment", body: text.trim() }];
  }

  return matches.map((match, i) => {
    const start = (match.index ?? 0) + match[0].length;
    const end = i + 1 < matches.length ? matches[i + 1].index : text.length;
    return { heading: match[1], body: text.slice(start, end).trim() };
  });
}

function tierBadgeClasses(riskTierBody: string): string {
  const text = riskTierBody.toLowerCase();
  if (text.includes("decline")) return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
  if (text.includes("high risk"))
    return "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300";
  if (text.includes("substandard"))
    return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300";
  if (text.includes("standard"))
    return "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300";
  if (text.includes("preferred"))
    return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
  return "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300";
}

const MAX_BADGE_LENGTH = 40;

export default function AssessmentResult({ result }: { result: AssessResponse }) {
  const sections = parseSections(result.assessment);
  const tierSection = sections.find((s) => s.heading === "Risk Tier");
  const riskTier =
    tierSection && tierSection.body.length <= MAX_BADGE_LENGTH ? tierSection : undefined;

  return (
    <div className="flex flex-col gap-4">
      {riskTier && (
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Risk Tier</span>
          <span className={`rounded-full px-3 py-1 text-sm font-semibold ${tierBadgeClasses(riskTier.body)}`}>
            {riskTier.body}
          </span>
        </div>
      )}

      {sections
        .filter((s) => s !== riskTier)
        .map((section) => (
          <div key={section.heading}>
            <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              {section.heading}
            </h3>
            <p className="whitespace-pre-wrap text-sm leading-6 text-zinc-800 dark:text-zinc-200">
              {section.body}
            </p>
          </div>
        ))}

      {result.tool_calls.length > 0 && (
        <details className="rounded-md border border-zinc-200 p-3 text-sm dark:border-zinc-800">
          <summary className="cursor-pointer font-medium text-zinc-600 dark:text-zinc-400">
            Tool call trace ({result.tool_calls.length})
          </summary>
          <ul className="mt-2 flex flex-col gap-2 font-mono text-xs">
            {result.tool_calls.map((call, i) => (
              <li key={i} className="rounded bg-zinc-100 p-2 dark:bg-zinc-900">
                <span className="font-semibold text-zinc-700 dark:text-zinc-300">{call.tool}</span>
                <pre className="mt-1 overflow-x-auto whitespace-pre-wrap text-zinc-600 dark:text-zinc-400">
                  {JSON.stringify(call.args, null, 2)}
                </pre>
              </li>
            ))}
          </ul>
        </details>
      )}

      <p className="text-xs text-zinc-400 dark:text-zinc-600">Session: {result.session_id}</p>
    </div>
  );
}
