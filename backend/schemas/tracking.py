"""
schemas/tracking.py
Pydantic models for nutrition logging and weight logging endpoints.
"""

from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, Field


class NutritionLogIn(BaseModel):
    log_date: Optional[date_type] = None
    calories: float = Field(0, ge=0)
    protein_g: float = Field(0, ge=0)
    iron_mg: float = Field(0, ge=0)
    calcium_mg: float = Field(0, ge=0)
    folate_mcg: float = Field(0, ge=0)
    vitamin_d_mcg: float = Field(0, ge=0)
    vitamin_b12_mcg: float = Field(0, ge=0)
    fiber_g: float = Field(0, ge=0)
    water_ml: float = Field(0, ge=0)


class NutritionLogOut(NutritionLogIn):
    id: int
    meal_score: Optional[float] = None
    nutrition_score: Optional[float] = None

    model_config = {"from_attributes": True}


class WeightLogIn(BaseModel):
    log_date: Optional[date_type] = None
    weight_kg: float = Field(..., gt=0)
    notes: Optional[str] = None


class WeightLogOut(WeightLogIn):
    id: int
    weekly_gain_kg: Optional[float] = None

    model_config = {"from_attributes": True}
