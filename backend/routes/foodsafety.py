"""
routes/foodsafety.py
Food safety checker. Checks the curated lookup table first (deterministic,
citable); falls back to the LLM for foods not in the table, clearly marked as
lower-confidence until the RAG pipeline (Phase 3) backs it with retrieved sources.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List

from dependencies import get_current_user
from models.user import User
from agents.food_safety_agent import check_food_safety

router = APIRouter(prefix="/foodsafety", tags=["Food Safety"])


class FoodSafetyRequest(BaseModel):
    food_name: str


class FoodSafetyResponse(BaseModel):
    food: str
    classification: str
    icon: str
    explanation: str
    alternatives: List[str]
    confidence: float
    sources: List[str]
    grounded: bool


@router.post("/check", response_model=FoodSafetyResponse)
def check_food_safety_endpoint(
    payload: FoodSafetyRequest,
    current_user: User = Depends(get_current_user),
):
    result = check_food_safety(payload.food_name)
    return FoodSafetyResponse(**result)
