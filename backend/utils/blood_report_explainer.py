"""
utils/blood_report_explainer.py
Generates a plain-language explanation of extracted blood report values.
Explicitly instructed to explain, not diagnose, per the spec's requirement that
the Medical Agent "explain hemoglobin, ferritin, vitamin D, blood sugar" and
"never diagnose diseases."
"""

from typing import Optional

from utils.ai_client import generate_text

SYSTEM_PROMPT = (
    "You are explaining blood test values to a pregnant user of NutriMama AI. "
    "For each provided value, briefly explain what it measures, whether it looks "
    "low/normal/high relative to common pregnancy reference ranges, and general "
    "nutritional context (e.g. low hemoglobin often relates to iron intake). "
    "Do NOT diagnose any condition. Do NOT tell the user they 'have' a disease. "
    "Always end by recommending they discuss the full report with their "
    "healthcare provider, since reference ranges vary by lab and trimester."
)

# Commonly cited general pregnancy reference ranges — for context only, not diagnostic thresholds.
REFERENCE_CONTEXT = (
    "Commonly cited general reference context (varies by lab/trimester — not a diagnostic cutoff): "
    "Hemoglobin: often ~11-14 g/dL in pregnancy. "
    "Ferritin: often ~10-150 ng/mL, with lower levels sometimes indicating reduced iron stores. "
    "Vitamin D (25-OH): often ~20-50 ng/mL considered sufficient by many labs. "
    "Fasting blood sugar: often under ~95 mg/dL commonly cited as a general fasting reference."
)


def explain_blood_report(
    hemoglobin: Optional[float],
    ferritin: Optional[float],
    vitamin_d: Optional[float],
    blood_sugar: Optional[float],
) -> str:
    values_provided = {
        "hemoglobin (g/dL)": hemoglobin,
        "ferritin (ng/mL)": ferritin,
        "vitamin D / 25-OH (ng/mL)": vitamin_d,
        "fasting blood sugar (mg/dL)": blood_sugar,
    }
    provided = {k: v for k, v in values_provided.items() if v is not None}

    if not provided:
        return (
            "No values were available to explain. Please enter your lab values manually "
            "if automatic extraction didn't pick them up correctly."
        )

    values_text = "\n".join(f"- {k}: {v}" for k, v in provided.items())
    user_prompt = f"{REFERENCE_CONTEXT}\n\nUser's values:\n{values_text}"

    return generate_text(SYSTEM_PROMPT, user_prompt, max_tokens=600)
