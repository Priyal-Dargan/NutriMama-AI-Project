"""
utils/nutrition_calc.py
Deterministic nutrient requirement calculations for pregnancy, based on commonly
published guidance (Mifflin-St Jeor for baseline energy needs, ACOG/WHO/ICMR-style
incremental pregnancy RDAs). Kept rule-based (not LLM-generated) so the numbers are
reproducible and auditable — the LLM is used only to explain them in plain language,
never to invent them.

These are general population guidelines for educational purposes, not a personalized
medical prescription. Always paired with the app-wide medical disclaimer.
"""

from typing import Optional

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
}

# Additional kcal/day by trimester (ACOG-style guidance)
TRIMESTER_CALORIE_INCREMENT = {1: 0, 2: 340, 3: 452}


def calculate_nutrition_requirements(
    age: int,
    height_cm: float,
    weight_kg: float,
    trimester: Optional[int],
    activity_level: str = "moderate",
) -> dict:
    # Mifflin-St Jeor BMR for women
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    activity_factor = ACTIVITY_MULTIPLIERS.get(activity_level, ACTIVITY_MULTIPLIERS["moderate"])
    baseline_tdee = bmr * activity_factor

    trimester_increment = TRIMESTER_CALORIE_INCREMENT.get(trimester or 1, 0)
    total_calories = round(baseline_tdee + trimester_increment)

    protein_g = round(max(71, weight_kg * 1.1))  # pregnancy RDA floor of 71g, or 1.1g/kg
    iron_mg = 27
    calcium_mg = 1300 if age < 19 else 1000
    folate_mcg = 600
    vitamin_d_mcg = 15  # ~600 IU
    vitamin_b12_mcg = 2.6
    fiber_g = 28
    water_ml = round(weight_kg * 35 + 300)  # baseline fluid need + pregnancy increment

    return {
        "calories": total_calories,
        "protein_g": protein_g,
        "iron_mg": iron_mg,
        "calcium_mg": calcium_mg,
        "folate_mcg": folate_mcg,
        "vitamin_d_mcg": vitamin_d_mcg,
        "vitamin_b12_mcg": vitamin_b12_mcg,
        "fiber_g": fiber_g,
        "water_ml": water_ml,
        "basis": (
            "Baseline energy need (Mifflin-St Jeor) + ACOG trimester increment; "
            "micronutrients follow commonly published pregnancy RDAs (ACOG/WHO-style). "
            "General guidance, not individualized medical advice."
        ),
    }
