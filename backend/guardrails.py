"""Guardrails: input validation (prompt-injection detection on free-text
applicant fields) and output validation (ensuring every response carries the
required disclaimer).

Both checks are plain deterministic string/regex matching, not another LLM
call -- a check built out of the same kind of model that's supposed to be
guarded against can be talked out of its own job by the same prompt it's
meant to catch. Deterministic checks can be wrong (see README/PLAN for the
documented false-negative/false-positive trade-off) but they can't be
persuaded.
"""

import re

# Patterns that indicate an attempt to hijack the agent's instructions rather
# than describe a real applicant. Matched case-insensitively against any
# free-text applicant field before it reaches the LLM.
_INJECTION_PATTERNS = [
    r"ignore (all|any|every|the)?\s*(previous|prior|above)?\s*instructions",
    r"disregard (all|any|every|the)?\s*(previous|prior|above)?\s*instructions",
    r"you are now\b",
    r"new instructions\s*:",
    r"system prompt",
    r"reveal (your|the) (system )?prompt",
    r"act as (a|an|the)\b",
    r"pretend (you are|to be)\b",
    r"\bjailbreak\b",
    r"\bDAN\b",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# Free-text fields on ApplicantData that a caller fully controls and that
# flow into the agent's prompt -- the only realistic injection surface, since
# every other field is numeric/boolean or drawn from a fixed set of values.
INJECTION_CHECKED_FIELDS = ("name", "occupation")


def find_prompt_injection(text: str | None) -> str | None:
    """Return the matched phrase if `text` looks like a prompt-injection
    attempt, else None."""
    if not text:
        return None
    match = _INJECTION_RE.search(text)
    return match.group(0) if match else None


# Phrases that count as "this response carries the required disclaimer".
# Matched loosely (any one is enough) since the agent's exact wording varies
# between a full applicant assessment and a general policy question.
_DISCLAIMER_MARKERS = (
    "licensed underwriter",
    "not a final",
    "not legal or financial advice",
    "not financial advice",
    "not legal advice",
    "professional advice",
    "general policy information",
)


def has_disclaimer(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _DISCLAIMER_MARKERS)


FALLBACK_DISCLAIMER = (
    "\n\nDisclaimer: This is not a final underwriting decision and is not "
    "legal or financial advice. A licensed underwriter must review and "
    "approve any final decision."
)


def ensure_disclaimer(answer: str) -> str:
    """Guarantee every response the API returns carries a disclaimer, even if
    the model forgot one. A deterministic backstop, not a replacement for the
    system prompt's instruction to include one."""
    if has_disclaimer(answer):
        return answer
    return answer + FALLBACK_DISCLAIMER
