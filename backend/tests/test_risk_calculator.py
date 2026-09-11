import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calculate_risk, risk_calculator


def test_clean_low_risk_applicant_lands_in_preferred_tier():
    result = calculate_risk(
        age=30,
        bmi=20.3,
        health_conditions=["None declared"],
        occupation_class="Class 1 - Minimal",
        smoker=False,
    )

    assert result["tier"] == "Preferred"
    assert result["total_score"] == 0


def test_high_risk_composite_applicant_lands_in_high_risk_or_decline_tier():
    result = calculate_risk(
        age=58,
        bmi=39.8,
        health_conditions=["Type 2 Diabetes (uncontrolled)", "Hypertension (uncontrolled)"],
        occupation_class="Class 5 - Hazardous",
        smoker=True,
    )

    assert result["tier"] in ("High Risk", "Decline")
    assert result["total_score"] > 90


def test_health_points_take_the_max_declared_condition_not_the_sum():
    single = calculate_risk(
        age=30, bmi=22.0, health_conditions=["Hypertension (uncontrolled)"],
        occupation_class="Class 1 - Minimal", smoker=False,
    )
    combined = calculate_risk(
        age=30, bmi=22.0,
        health_conditions=["Hypertension (uncontrolled)", "Asthma (mild, intermittent)"],
        occupation_class="Class 1 - Minimal", smoker=False,
    )

    assert single["breakdown"]["health_points"] == combined["breakdown"]["health_points"]


@pytest.mark.parametrize(
    "bmi,expected_points",
    [
        (24.9, 0),   # top of the Normal band
        (25.0, 10),  # bottom of the Overweight band
        (34.9, 25),  # top of Obese Class I
        (35.0, 45),  # bottom of Obese Class II
    ],
)
def test_bmi_band_boundaries_are_applied_consistently(bmi, expected_points):
    result = calculate_risk(
        age=30, bmi=bmi, health_conditions=["None declared"],
        occupation_class="Class 1 - Minimal", smoker=False,
    )
    assert result["breakdown"]["bmi_points"] == expected_points


def test_missing_age_raises_value_error():
    with pytest.raises(ValueError, match="age"):
        calculate_risk(age=None, bmi=22.0, health_conditions=[], occupation_class="Class 1 - Minimal", smoker=False)


def test_missing_bmi_raises_value_error():
    with pytest.raises(ValueError, match="bmi"):
        calculate_risk(age=30, bmi=None, health_conditions=[], occupation_class="Class 1 - Minimal", smoker=False)


def test_missing_occupation_class_raises_value_error():
    with pytest.raises(ValueError, match="occupation_class"):
        calculate_risk(age=30, bmi=22.0, health_conditions=[], occupation_class=None, smoker=False)


def test_unknown_health_condition_raises_helpful_value_error():
    with pytest.raises(ValueError, match="Unknown value"):
        calculate_risk(
            age=30, bmi=22.0, health_conditions=["Made Up Condition"],
            occupation_class="Class 1 - Minimal", smoker=False,
        )


def test_tool_wrapper_returns_error_dict_instead_of_raising():
    # Regression test: the latency benchmark script found that the model
    # sometimes calls this tool with a literal "MISSING" placeholder for a
    # required field instead of asking a clarifying question first. Letting
    # calculate_risk's ValueError propagate out of the @tool wrapper crashed
    # the whole agent run into a 502 instead of letting the agent see the
    # error and ask the user, so the wrapper must catch it and hand the
    # error back as a normal tool result.
    result = risk_calculator.invoke(
        {
            "age": 30,
            "bmi": 22.0,
            "health_conditions": ["None declared"],
            "occupation_class": "MISSING",
            "smoker": False,
        }
    )
    assert "error" in result
    assert "occupation_class" in result["error"]


def test_smoker_adds_more_points_than_non_smoker():
    non_smoker = calculate_risk(age=30, bmi=22.0, health_conditions=[], occupation_class="Class 1 - Minimal", smoker=False)
    smoker = calculate_risk(age=30, bmi=22.0, health_conditions=[], occupation_class="Class 1 - Minimal", smoker=True)

    assert smoker["total_score"] > non_smoker["total_score"]


def test_high_risk_hobby_adds_points():
    without_hobby = calculate_risk(
        age=30, bmi=22.0, health_conditions=[], occupation_class="Class 1 - Minimal",
        smoker=False, high_risk_hobby=False,
    )
    with_hobby = calculate_risk(
        age=30, bmi=22.0, health_conditions=[], occupation_class="Class 1 - Minimal",
        smoker=False, high_risk_hobby=True,
    )

    assert with_hobby["total_score"] > without_hobby["total_score"]
