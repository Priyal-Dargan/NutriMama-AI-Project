"""
utils/pregnancy_calc.py
Pure calculation helpers shared by the Profile route and the future User Profile Agent
(Phase 2). Kept dependency-free and easily unit-testable.
"""

from datetime import date
from typing import Optional


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def calculate_pregnancy_week(due_date: Optional[date], reference_date: Optional[date] = None) -> Optional[int]:
    """
    Estimates the current pregnancy week from the due date, assuming a standard
    40-week (280-day) gestation. Returns None if no due date is set.
    """
    if due_date is None:
        return None
    reference_date = reference_date or date.today()
    days_until_due = (due_date - reference_date).days
    days_pregnant = 280 - days_until_due
    week = max(0, min(42, days_pregnant // 7))
    return week


def calculate_trimester(pregnancy_week: Optional[int]) -> Optional[int]:
    if pregnancy_week is None:
        return None
    if pregnancy_week <= 13:
        return 1
    if pregnancy_week <= 27:
        return 2
    return 3


def estimate_recommended_weight_gain_kg(pre_pregnancy_bmi: Optional[float]) -> str:
    """
    Returns an IOM-style recommended total weight gain range as a human-readable string.
    This is general guidance, not a medical prescription — always paired with the
    educational-use disclaimer in the UI.
    """
    if pre_pregnancy_bmi is None:
        return "Unknown (pre-pregnancy BMI not provided)"
    if pre_pregnancy_bmi < 18.5:
        return "12.5–18 kg (underweight)"
    if pre_pregnancy_bmi < 25:
        return "11.5–16 kg (normal weight)"
    if pre_pregnancy_bmi < 30:
        return "7–11.5 kg (overweight)"
    return "5–9 kg (obese)"
