"""
schemas/profile.py
Pydantic models for pregnancy profile, medical history, and diet preferences —
used by the onboarding wizard and the Settings/Profile pages.
"""

from datetime import date
from typing import Optional, List

from pydantic import BaseModel, Field


class PregnancyProfileIn(BaseModel):
    age: int = Field(..., ge=13, le=60)
    height_cm: float = Field(..., gt=0)
    current_weight_kg: float = Field(..., gt=0)
    pre_pregnancy_weight_kg: Optional[float] = None
    due_date: Optional[date] = None
    pregnancy_type: str = "singleton"
    activity_level: str = "moderate"


class PregnancyProfileOut(PregnancyProfileIn):
    bmi: Optional[float] = None
    pregnancy_week: Optional[int] = None
    trimester: Optional[int] = None

    model_config = {"from_attributes": True}


class MedicalHistoryIn(BaseModel):
    diabetes: bool = False
    gestational_diabetes: bool = False
    hypertension: bool = False
    pcos: bool = False
    thyroid: bool = False
    anemia: bool = False
    lactose_intolerance: bool = False
    gluten_intolerance: bool = False
    allergies: Optional[List[str]] = None
    other_conditions: Optional[str] = None


class DietPreferencesIn(BaseModel):
    vegetarian: bool = False
    vegan: bool = False
    jain: bool = False
    eggetarian: bool = False
    non_vegetarian: bool = False
    cuisine: Optional[str] = None
    budget: Optional[str] = None
    favorite_foods: Optional[List[str]] = None
    disliked_foods: Optional[List[str]] = None
    available_ingredients: Optional[List[str]] = None


class FullProfileOut(BaseModel):
    """Combined view returned by GET /profile."""
    pregnancy: Optional[PregnancyProfileOut] = None
    medical: Optional[MedicalHistoryIn] = None
    diet: Optional[DietPreferencesIn] = None
