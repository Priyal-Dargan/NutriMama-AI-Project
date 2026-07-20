"""
agents/nutrition_agent.py
Nutrition Planner Agent. Calculates daily nutritional requirements from the
profile loaded by the Profile Agent. Uses deterministic formulas (see
utils/nutrition_calc.py) — never asks the LLM to invent nutrient numbers.
"""

from datetime import datetime

from agents.state import GraphState
from utils.nutrition_calc import calculate_nutrition_requirements
from utils.logger import get_logger

logger = get_logger(__name__)


def run_nutrition_agent(state: GraphState) -> GraphState:
    profile = state.get("user_profile")

    if not profile:
        state["nutrition_requirements"] = None
        state.setdefault("agent_execution_history", []).append(
            {
                "agent": "nutrition_planner",
                "status": "skipped",
                "detail": "No pregnancy profile available — complete onboarding first.",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        return state

    requirements = calculate_nutrition_requirements(
        age=profile["age"],
        height_cm=profile["height_cm"],
        weight_kg=profile["current_weight_kg"],
        trimester=profile.get("trimester"),
        activity_level=profile.get("activity_level", "moderate"),
    )
    state["nutrition_requirements"] = requirements

    state.setdefault("agent_execution_history", []).append(
        {
            "agent": "nutrition_planner",
            "status": "completed",
            "detail": f"Calculated requirements for trimester {profile.get('trimester')}",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    logger.info(f"Nutrition agent ran: user_id={state['user_id']}")
    return state
