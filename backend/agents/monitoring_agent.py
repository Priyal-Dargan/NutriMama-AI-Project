"""
agents/monitoring_agent.py
Health Monitoring Agent. Analyzes recent nutrition/weight logs for patterns
(low iron/protein intake, poor hydration, rapid weight gain, insufficient
calories) using simple threshold rules against the targets the Nutrition
Planner Agent calculated. Never diagnoses — only flags patterns and recommends
professional follow-up, per the spec.
"""

from datetime import datetime
from statistics import mean

from sqlalchemy.orm import Session

from agents.state import GraphState
from models.nutrition import NutritionLog
from models.reports import WeightLog
from utils.logger import get_logger

logger = get_logger(__name__)

LOOKBACK_DAYS = 7


def run_monitoring_agent(state: GraphState, db: Session) -> GraphState:
    user_id = state["user_id"]
    requirements = state.get("nutrition_requirements")

    logs = (
        db.query(NutritionLog)
        .filter_by(user_id=user_id)
        .order_by(NutritionLog.log_date.desc())
        .limit(LOOKBACK_DAYS)
        .all()
    )
    weights = (
        db.query(WeightLog)
        .filter_by(user_id=user_id)
        .order_by(WeightLog.log_date.desc())
        .limit(3)
        .all()
    )

    insights = {"flags": [], "summary": None}

    if logs and requirements:
        avg_calories = mean(l.calories for l in logs)
        avg_iron = mean(l.iron_mg for l in logs)
        avg_protein = mean(l.protein_g for l in logs)
        avg_water = mean(l.water_ml for l in logs)

        if avg_calories < requirements["calories"] * 0.85:
            insights["flags"].append("Calorie intake has been consistently below your target — consider adding nutrient-dense snacks.")
        if avg_iron < requirements["iron_mg"] * 0.7:
            insights["flags"].append("Iron intake looks low this week — iron-rich foods or your supplement may need attention. Mention this to your provider, especially if you have anemia.")
        if avg_protein < requirements["protein_g"] * 0.8:
            insights["flags"].append("Protein intake has been below target — consider adding dals, paneer, eggs, or lean meat depending on your diet.")
        if avg_water < requirements["water_ml"] * 0.7:
            insights["flags"].append("Hydration looks low this week — try to increase water intake throughout the day.")

    if len(weights) >= 2:
        # weights[0] is most recent (desc order)
        recent_gain = weights[0].weight_kg - weights[-1].weight_kg
        weeks_span = max(1, (weights[0].log_date - weights[-1].log_date).days / 7)
        weekly_rate = recent_gain / weeks_span
        if weekly_rate > 1.0:
            insights["flags"].append(
                f"Weight has increased by about {weekly_rate:.1f}kg/week recently, which is faster than typically "
                "recommended — worth discussing at your next appointment."
            )

    if insights["flags"]:
        insights["summary"] = "A few patterns worth your attention this week. Always confirm with your healthcare provider before changing anything."
    else:
        insights["summary"] = "No concerning patterns detected in your recent logs." if logs else "Not enough logged data yet to detect patterns."

    state["health_insights"] = insights

    state.setdefault("agent_execution_history", []).append(
        {
            "agent": "health_monitoring",
            "status": "completed",
            "detail": f"{len(insights['flags'])} flag(s) raised",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    logger.info(f"Monitoring agent ran: user_id={user_id} flags={len(insights['flags'])}")
    return state
