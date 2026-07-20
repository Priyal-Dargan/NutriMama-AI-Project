"""
agents/profile_agent.py
User Profile Agent. Loads the user's pregnancy profile, medical history, and diet
preferences from the database into the shared graph state. Never generates meals
or medical advice — pure data-loading responsibility, per the spec.
"""

import json
from datetime import datetime

from sqlalchemy.orm import Session

from models.pregnancy import PregnancyProfile
from models.profile import MedicalHistory, DietPreferences
from agents.state import GraphState
from utils.logger import get_logger

logger = get_logger(__name__)


def _parse_list(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return [v.strip() for v in value.split(",") if v.strip()]


def run_profile_agent(state: GraphState, db: Session) -> GraphState:
    user_id = state["user_id"]

    pregnancy = db.query(PregnancyProfile).filter_by(user_id=user_id).first()
    medical = db.query(MedicalHistory).filter_by(user_id=user_id).first()
    diet = db.query(DietPreferences).filter_by(user_id=user_id).first()

    state["user_profile"] = (
        {
            "age": pregnancy.age,
            "height_cm": pregnancy.height_cm,
            "current_weight_kg": pregnancy.current_weight_kg,
            "bmi": pregnancy.bmi,
            "pregnancy_week": pregnancy.pregnancy_week,
            "trimester": pregnancy.trimester,
            "activity_level": pregnancy.activity_level,
            "pregnancy_type": pregnancy.pregnancy_type,
        }
        if pregnancy
        else None
    )

    state["medical_conditions"] = (
        {
            "diabetes": medical.diabetes,
            "gestational_diabetes": medical.gestational_diabetes,
            "hypertension": medical.hypertension,
            "pcos": medical.pcos,
            "thyroid": medical.thyroid,
            "anemia": medical.anemia,
            "lactose_intolerance": medical.lactose_intolerance,
            "gluten_intolerance": medical.gluten_intolerance,
            "allergies": _parse_list(medical.allergies),
            "other_conditions": medical.other_conditions,
        }
        if medical
        else None
    )

    state["diet_preferences"] = (
        {
            "vegetarian": diet.vegetarian,
            "vegan": diet.vegan,
            "jain": diet.jain,
            "eggetarian": diet.eggetarian,
            "non_vegetarian": diet.non_vegetarian,
            "cuisine": diet.cuisine,
            "budget": diet.budget,
            "favorite_foods": _parse_list(diet.favorite_foods),
            "disliked_foods": _parse_list(diet.disliked_foods),
        }
        if diet
        else None
    )
    state["available_ingredients"] = _parse_list(diet.available_ingredients) if diet else []

    state.setdefault("agent_execution_history", []).append(
        {
            "agent": "profile_agent",
            "status": "completed" if pregnancy else "completed_no_profile",
            "detail": "Loaded profile" if pregnancy else "No pregnancy profile on file yet",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    logger.info(f"Profile agent ran: user_id={user_id} has_profile={bool(pregnancy)}")
    return state
