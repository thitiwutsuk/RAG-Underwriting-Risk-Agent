"""Generate synthetic applicant cases for end-to-end agent testing.

Run: python scripts/generate_applicants.py
Output: data/applicants.json

Cases are a mix of randomly generated baseline applicants plus explicitly
authored edge cases (high risk, borderline, missing fields) so coverage of
those scenarios is guaranteed rather than left to chance.
"""

import json
import random

random.seed(42)

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery",
    "Cameron", "Drew", "Skyler", "Reese", "Hayden", "Peyton", "Rowan", "Emerson",
]
LAST_NAMES = [
    "Nguyen", "Smith", "Garcia", "Kim", "Patel", "Johnson", "Lee", "Martinez",
    "Brown", "Wilson", "Anderson", "Thomas", "Chen", "Davis", "Rodriguez", "Walker",
]
OCCUPATIONS = [
    ("Software Engineer", "Class 1 - Minimal"),
    ("Accountant", "Class 1 - Minimal"),
    ("Teacher", "Class 1 - Minimal"),
    ("Retail Sales Associate", "Class 2 - Low"),
    ("Healthcare Administrator", "Class 2 - Low"),
    ("Electrician", "Class 3 - Moderate"),
    ("Mechanic", "Class 3 - Moderate"),
    ("Construction Worker", "Class 4 - High"),
    ("Delivery Rider", "Class 4 - High"),
    ("Commercial Fisherman", "Class 4 - High"),
    ("Offshore Oil Rig Worker", "Class 5 - Hazardous"),
    ("Commercial Diver", "Class 5 - Hazardous"),
]
HEALTH_CONDITIONS = [
    "None declared",
    "Hypertension (controlled)",
    "Hypertension (uncontrolled)",
    "Type 2 Diabetes (controlled)",
    "Type 2 Diabetes (uncontrolled)",
    "Asthma (mild, intermittent)",
    "Asthma (severe, persistent)",
    "Family history - heart disease",
    "Mental health condition (managed)",
]
POLICY_TYPES = [
    "Term Life", "Whole Life", "Critical Illness", "Health & Medical",
    "Accidental Death & Dismemberment", "Disability Income", "Universal Life",
]


def random_applicant(applicant_id: str) -> dict:
    age = random.randint(19, 72)
    height_cm = random.randint(150, 195)
    weight_kg = round(height_cm / 100 * height_cm / 100 * random.uniform(19, 32), 1)
    bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
    occupation, occupation_class = random.choice(OCCUPATIONS)
    return {
        "applicant_id": applicant_id,
        "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "age": age,
        "gender": random.choice(["Male", "Female"]),
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "bmi": bmi,
        "smoker": random.choice([True, False, False, False]),
        "occupation": occupation,
        "occupation_class": occupation_class,
        "health_conditions": random.sample(HEALTH_CONDITIONS, k=random.choice([1, 1, 1, 2])),
        "policy_type_requested": random.choice(POLICY_TYPES),
        "coverage_amount_usd": random.choice([50000, 100000, 250000, 500000, 1000000]),
        "notes": "",
    }


def build_cases() -> list:
    cases = [random_applicant(f"APP-{i:03d}") for i in range(1, 19)]

    edge_cases = [
        {
            "applicant_id": "APP-EDGE-01",
            "name": "Marcus Webb",
            "age": 58,
            "gender": "Male",
            "height_cm": 175,
            "weight_kg": 122.0,
            "bmi": 39.8,
            "smoker": True,
            "occupation": "Offshore Oil Rig Worker",
            "occupation_class": "Class 5 - Hazardous",
            "health_conditions": ["Type 2 Diabetes (uncontrolled)", "Hypertension (uncontrolled)"],
            "policy_type_requested": "Term Life",
            "coverage_amount_usd": 500000,
            "notes": "High-risk composite: obesity, uncontrolled diabetes and hypertension, hazardous occupation, smoker. Expected to land in High Risk or Decline tier.",
        },
        {
            "applicant_id": "APP-EDGE-02",
            "name": "Priya Raman",
            "age": 41,
            "gender": "Female",
            "height_cm": 165,
            "weight_kg": 85.3,
            "bmi": 31.3,
            "smoker": False,
            "occupation": "Accountant",
            "occupation_class": "Class 1 - Minimal",
            "health_conditions": ["Hypertension (controlled)"],
            "policy_type_requested": "Whole Life",
            "coverage_amount_usd": 250000,
            "notes": "Borderline case: BMI just inside Obese Class I band, otherwise low-risk profile. Tests sensitivity of the BMI band boundary.",
        },
        {
            "applicant_id": "APP-EDGE-03",
            "name": "Daniel Ostrowski",
            "age": 34,
            "gender": "Male",
            "height_cm": 180,
            "weight_kg": 80.6,
            "bmi": 24.9,
            "smoker": False,
            "occupation": "Software Engineer",
            "occupation_class": "Class 1 - Minimal",
            "health_conditions": ["None declared"],
            "policy_type_requested": "Term Life",
            "coverage_amount_usd": 750000,
            "notes": "Borderline case: BMI exactly at the Normal/Overweight boundary (24.9). Tests whether the risk_calculator applies band edges inclusively and consistently.",
        },
        {
            "applicant_id": "APP-EDGE-04",
            "name": "Grace Owusu",
            "age": 29,
            "gender": "Female",
            "height_cm": 168,
            "weight_kg": None,
            "bmi": None,
            "smoker": False,
            "occupation": "Retail Sales Associate",
            "occupation_class": "Class 2 - Low",
            "health_conditions": ["None declared"],
            "policy_type_requested": "Health & Medical",
            "coverage_amount_usd": 100000,
            "notes": "Missing field case: weight/BMI not provided. Tests that the agent asks a clarifying question or flags incomplete data rather than guessing.",
        },
        {
            "applicant_id": "APP-EDGE-05",
            "name": "Tom Fischer",
            "age": 47,
            "gender": "Male",
            "height_cm": 178,
            "weight_kg": 82.0,
            "bmi": 25.9,
            "smoker": False,
            "occupation": None,
            "occupation_class": None,
            "health_conditions": ["None declared"],
            "policy_type_requested": "Disability Income",
            "coverage_amount_usd": 300000,
            "notes": "Missing field case: occupation not declared, which is required input for both risk_calculator and Disability Income underwriting (occupation class caps benefit period).",
        },
        {
            "applicant_id": "APP-EDGE-06",
            "name": "Elena Voss",
            "age": 63,
            "gender": "Female",
            "height_cm": 160,
            "weight_kg": 58.0,
            "bmi": 22.7,
            "smoker": False,
            "occupation": "Teacher",
            "occupation_class": "Class 1 - Minimal",
            "health_conditions": ["None declared"],
            "policy_type_requested": "Term Life",
            "coverage_amount_usd": 150000,
            "notes": "Low-risk baseline at the upper end of the eligible age band (63). Tests correct handling of the highest age bracket (56-65) without other risk factors.",
        },
        {
            "applicant_id": "APP-EDGE-07",
            "name": "Ricardo Alves",
            "age": 39,
            "gender": "Male",
            "height_cm": 172,
            "weight_kg": 95.0,
            "bmi": 32.1,
            "smoker": True,
            "occupation": "Commercial Diver",
            "occupation_class": "Class 5 - Hazardous",
            "health_conditions": ["None declared"],
            "policy_type_requested": "Accidental Death & Dismemberment",
            "coverage_amount_usd": 400000,
            "notes": "Hazardous occupation with no declared health conditions, applying for an accident-only policy. Tests that occupation risk is weighed appropriately even when the product type (AD&D) does not medically underwrite.",
        },
        {
            "applicant_id": "APP-EDGE-08",
            "name": "Chloe Bennett",
            "age": 22,
            "gender": "Female",
            "height_cm": 163,
            "weight_kg": 54.0,
            "bmi": 20.3,
            "smoker": False,
            "occupation": "Software Engineer",
            "occupation_class": "Class 1 - Minimal",
            "health_conditions": ["None declared"],
            "policy_type_requested": "Term Life",
            "coverage_amount_usd": 100000,
            "notes": "Clean low-risk baseline case: young, healthy, low-risk occupation. Expected Preferred tier — used as a control case.",
        },
    ]

    return cases + edge_cases


if __name__ == "__main__":
    cases = build_cases()
    with open("data/applicants.json", "w") as f:
        json.dump(cases, f, indent=2)
    print(f"Wrote {len(cases)} applicant cases to data/applicants.json")
