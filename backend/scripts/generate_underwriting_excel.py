"""Generate the mock underwriting criteria workbook that risk_calculator reads at runtime.

Run: python scripts/generate_underwriting_excel.py
Output: data/underwriting_criteria.xlsx
"""

import pandas as pd

OUTPUT_PATH = "data/underwriting_criteria.xlsx"

age_bands = pd.DataFrame(
    [
        {"age_min": 18, "age_max": 25, "risk_points": 5},
        {"age_min": 26, "age_max": 35, "risk_points": 0},
        {"age_min": 36, "age_max": 45, "risk_points": 5},
        {"age_min": 46, "age_max": 55, "risk_points": 15},
        {"age_min": 56, "age_max": 65, "risk_points": 30},
        {"age_min": 66, "age_max": 75, "risk_points": 50},
    ]
)

bmi_bands = pd.DataFrame(
    [
        {"bmi_min": 0.0, "bmi_max": 18.4, "category": "Underweight", "risk_points": 10},
        {"bmi_min": 18.5, "bmi_max": 24.9, "category": "Normal", "risk_points": 0},
        {"bmi_min": 25.0, "bmi_max": 29.9, "category": "Overweight", "risk_points": 10},
        {"bmi_min": 30.0, "bmi_max": 34.9, "category": "Obese Class I", "risk_points": 25},
        {"bmi_min": 35.0, "bmi_max": 39.9, "category": "Obese Class II", "risk_points": 45},
        {"bmi_min": 40.0, "bmi_max": 99.0, "category": "Obese Class III", "risk_points": 70},
    ]
)

health_history = pd.DataFrame(
    [
        {"condition": "None declared", "risk_points": 0, "notes": "No significant medical history"},
        {"condition": "Hypertension (controlled)", "risk_points": 10, "notes": "On medication, BP within target range"},
        {"condition": "Hypertension (uncontrolled)", "risk_points": 30, "notes": "BP consistently above target range"},
        {"condition": "Type 2 Diabetes (controlled)", "risk_points": 20, "notes": "HbA1c within target on treatment"},
        {"condition": "Type 2 Diabetes (uncontrolled)", "risk_points": 45, "notes": "HbA1c above target"},
        {"condition": "Type 1 Diabetes", "risk_points": 35, "notes": "Insulin-dependent"},
        {"condition": "Asthma (mild, intermittent)", "risk_points": 5, "notes": "Rescue inhaler only"},
        {"condition": "Asthma (severe, persistent)", "risk_points": 20, "notes": "Daily controller medication required"},
        {"condition": "Coronary heart disease (history)", "risk_points": 60, "notes": "Prior MI, angioplasty, or bypass"},
        {"condition": "Cancer (in remission > 5 years)", "risk_points": 30, "notes": "No recurrence, confirmed by oncologist"},
        {"condition": "Cancer (active treatment)", "risk_points": 999, "notes": "Refer to manual underwriting / decline"},
        {"condition": "Chronic kidney disease", "risk_points": 50, "notes": "Stage 3 or higher"},
        {"condition": "Mental health condition (managed)", "risk_points": 10, "notes": "Stable on treatment, no hospitalization in 2 years"},
        {"condition": "Family history - heart disease", "risk_points": 10, "notes": "First-degree relative diagnosed before age 60"},
        {"condition": "Family history - cancer", "risk_points": 8, "notes": "First-degree relative diagnosed before age 60"},
    ]
)

occupation_risk = pd.DataFrame(
    [
        {"occupation_class": "Class 1 - Minimal", "examples": "Office worker, accountant, teacher, software engineer", "risk_points": 0},
        {"occupation_class": "Class 2 - Low", "examples": "Retail worker, sales representative, healthcare admin", "risk_points": 5},
        {"occupation_class": "Class 3 - Moderate", "examples": "Electrician, mechanic, warehouse supervisor", "risk_points": 15},
        {"occupation_class": "Class 4 - High", "examples": "Construction worker, commercial fisherman, delivery rider", "risk_points": 30},
        {"occupation_class": "Class 5 - Hazardous", "examples": "Offshore oil rig worker, commercial diver, private pilot, demolition crew", "risk_points": 60},
    ]
)

lifestyle = pd.DataFrame(
    [
        {"factor": "Non-smoker", "risk_points": 0},
        {"factor": "Former smoker (quit > 5 years)", "risk_points": 10},
        {"factor": "Current smoker", "risk_points": 40},
        {"factor": "Heavy alcohol use (self-reported)", "risk_points": 20},
        {"factor": "High-risk hobby (skydiving, scuba diving, motor racing)", "risk_points": 25},
    ]
)

risk_formula = pd.DataFrame(
    [
        {
            "component": "total_risk_score",
            "formula": "age_points + bmi_points + max(health_condition_points) + occupation_points + smoker_points + hobby_points",
            "notes": "health_condition_points takes the single highest-scoring declared condition, not a sum, to avoid double-penalizing related conditions",
        }
    ]
)

risk_tiers = pd.DataFrame(
    [
        {"tier": "Preferred", "score_min": 0, "score_max": 20, "decision": "Approve", "premium_loading": "0%"},
        {"tier": "Standard", "score_min": 21, "score_max": 50, "decision": "Approve", "premium_loading": "+10%"},
        {"tier": "Substandard", "score_min": 51, "score_max": 90, "decision": "Approve with rating", "premium_loading": "+50% to +100%"},
        {"tier": "High Risk", "score_min": 91, "score_max": 130, "decision": "Approve with exclusions", "premium_loading": "+150%"},
        {"tier": "Decline", "score_min": 131, "score_max": 9999, "decision": "Decline", "premium_loading": "N/A"},
    ]
)

with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
    age_bands.to_excel(writer, sheet_name="Age", index=False)
    bmi_bands.to_excel(writer, sheet_name="BMI", index=False)
    health_history.to_excel(writer, sheet_name="Health History", index=False)
    occupation_risk.to_excel(writer, sheet_name="Occupation Risk", index=False)
    lifestyle.to_excel(writer, sheet_name="Lifestyle", index=False)
    risk_formula.to_excel(writer, sheet_name="Risk Formula", index=False)
    risk_tiers.to_excel(writer, sheet_name="Risk Tiers", index=False)

print(f"Wrote {OUTPUT_PATH}")
