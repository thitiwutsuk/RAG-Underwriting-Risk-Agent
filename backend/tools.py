"""Agent tools: risk_calculator (deterministic underwriting score) and
policy_lookup (RAG search over the ingested policy corpus).

Each tool has a plain-function core (calculate_risk / search_policies) that
is unit-testable without any LLM, plus a thin @tool wrapper for the agent.
"""

from functools import lru_cache

import chromadb
import pandas as pd
from fastembed import TextEmbedding
from langchain_core.tools import tool

from ingest import CHROMA_PERSIST_DIR, COLLECTION_NAME, EMBEDDING_MODEL_NAME

EXCEL_PATH = "data/underwriting_criteria.xlsx"


# --------------------------------------------------------------------------
# risk_calculator
# --------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_underwriting_tables() -> dict[str, pd.DataFrame]:
    """Read every sheet of the underwriting criteria workbook once per process."""
    return pd.read_excel(EXCEL_PATH, sheet_name=None)


def _lookup_band(df: pd.DataFrame, value: float, min_col: str, max_col: str) -> int:
    matches = df[(df[min_col] <= value) & (value <= df[max_col])]
    if matches.empty:
        raise ValueError(f"No band in the underwriting table covers value {value} ({min_col}/{max_col})")
    return int(matches.iloc[0]["risk_points"])


def _lookup_exact(df: pd.DataFrame, key_col: str, key_value: str) -> int:
    matches = df[df[key_col] == key_value]
    if matches.empty:
        valid = ", ".join(sorted(df[key_col].astype(str).unique()))
        raise ValueError(f"Unknown value '{key_value}' for {key_col}. Valid values are: {valid}")
    return int(matches.iloc[0]["risk_points"])


def calculate_risk(
    age: int | None,
    bmi: float | None,
    health_conditions: list[str] | None,
    occupation_class: str | None,
    smoker: bool,
    high_risk_hobby: bool = False,
) -> dict:
    """Compute a deterministic underwriting risk score from the criteria workbook.

    Raises ValueError with a clear message when a required field is missing
    or a categorical value (health condition, occupation class) does not
    match any row in the underwriting criteria workbook -- callers (the
    agent) should surface this to the user as a clarifying question rather
    than guessing a value.
    """
    if age is None:
        raise ValueError("age is required to calculate a risk score")
    if bmi is None:
        raise ValueError("bmi is required to calculate a risk score (height_cm and weight_kg, or bmi directly)")
    if occupation_class is None:
        raise ValueError("occupation_class is required to calculate a risk score")

    tables = _load_underwriting_tables()

    age_points = _lookup_band(tables["Age"], age, "age_min", "age_max")
    bmi_points = _lookup_band(tables["BMI"], bmi, "bmi_min", "bmi_max")

    conditions = health_conditions or ["None declared"]
    health_points = max(_lookup_exact(tables["Health History"], "condition", c) for c in conditions)

    occupation_points = _lookup_exact(tables["Occupation Risk"], "occupation_class", occupation_class)

    smoking_factor = "Current smoker" if smoker else "Non-smoker"
    smoker_points = _lookup_exact(tables["Lifestyle"], "factor", smoking_factor)

    hobby_points = 0
    if high_risk_hobby:
        hobby_points = _lookup_exact(
            tables["Lifestyle"], "factor", "High-risk hobby (skydiving, scuba diving, motor racing)"
        )

    total_score = age_points + bmi_points + health_points + occupation_points + smoker_points + hobby_points

    tiers = tables["Risk Tiers"]
    tier_match = tiers[(tiers["score_min"] <= total_score) & (total_score <= tiers["score_max"])]
    tier_row = tier_match.iloc[0]

    return {
        "total_score": total_score,
        "tier": tier_row["tier"],
        "decision": tier_row["decision"],
        "premium_loading": tier_row["premium_loading"],
        "breakdown": {
            "age_points": age_points,
            "bmi_points": bmi_points,
            "health_points": health_points,
            "occupation_points": occupation_points,
            "smoker_points": smoker_points,
            "hobby_points": hobby_points,
        },
    }


@tool
def risk_calculator(
    age: int,
    bmi: float,
    health_conditions: list[str],
    occupation_class: str,
    smoker: bool,
    high_risk_hobby: bool = False,
) -> dict:
    """Compute the applicant's underwriting risk score and tier from the underwriting
    criteria workbook. Always call this instead of estimating a risk score yourself.

    Args:
        age: Applicant age in years.
        bmi: Applicant body mass index.
        health_conditions: List of declared health conditions, matching the
            wording in the underwriting criteria (e.g. "Hypertension (controlled)").
            Use ["None declared"] if the applicant has no relevant history.
        occupation_class: One of the underwriting occupation classes, e.g.
            "Class 1 - Minimal" through "Class 5 - Hazardous".
        smoker: Whether the applicant currently smokes.
        high_risk_hobby: Whether the applicant declared a high-risk hobby
            (skydiving, scuba diving, motor racing).
    """
    try:
        return calculate_risk(age, bmi, health_conditions, occupation_class, smoker, high_risk_hobby)
    except ValueError as exc:
        # A required value is missing or unrecognized (e.g. the model called
        # this with a literal "MISSING" placeholder instead of asking a
        # clarifying question first, as system prompt instructs). Return the
        # error as the tool result instead of raising -- letting a tool
        # exception propagate uncaught crashes the whole agent run into a 502,
        # instead of the graceful clarifying-question path this is meant to
        # trigger. Found via the latency benchmark script (a missing
        # occupation_class case), see PLAN.md.
        return {"error": str(exc)}


# --------------------------------------------------------------------------
# policy_lookup
# --------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_embedding_model() -> TextEmbedding:
    return TextEmbedding(model_name=EMBEDDING_MODEL_NAME)


@lru_cache(maxsize=1)
def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client.get_collection(COLLECTION_NAME)


def search_policies(query: str, k: int = 3) -> list[dict]:
    """Run a semantic search over the ingested policy/underwriting corpus."""
    model = _get_embedding_model()
    collection = _get_collection()

    query_embedding = [vec.tolist() for vec in model.embed([query])]
    results = collection.query(query_embeddings=query_embedding, n_results=k)

    hits = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        hits.append(
            {
                "text": doc,
                "source_file": meta.get("source_file"),
                "page": meta.get("page"),
                "sheet": meta.get("sheet"),
                "distance": dist,
            }
        )
    return hits


@tool
def policy_lookup(query: str, k: int = 3) -> list[dict]:
    """Search the ingested insurance policy documents and underwriting criteria for
    text relevant to the query. Always call this before making a claim about policy
    coverage, exclusions, or waiting periods, and cite the returned source_file/page
    in your answer.

    Args:
        query: A natural-language question or topic to search for.
        k: Number of top matching chunks to return.
    """
    return search_policies(query, k)
