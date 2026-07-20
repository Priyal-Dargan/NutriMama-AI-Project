"""
agents/reminder_agent.py
Reminder Agent. Suggests sensible default reminders based on the user's profile
(e.g. iron/calcium supplements once anemia is on file, prenatal vitamin daily,
water reminders). Writes suggestions to state; the route layer persists any the
user accepts. Deterministic — no LLM needed for scheduling logic.
"""

from datetime import datetime, time

from agents.state import GraphState
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_TIMES = {
    "water": [time(9, 0), time(13, 0), time(17, 0)],
    "vitamin": [time(8, 0)],
    "iron": [time(21, 0)],  # commonly advised away from calcium-rich meals
    "calcium": [time(13, 30)],
    "exercise": [time(7, 30)],
    "sleep": [time(22, 0)],
}


def run_reminder_agent(state: GraphState) -> GraphState:
    medical = state.get("medical_conditions") or {}
    suggestions = []

    for t in DEFAULT_TIMES["water"]:
        suggestions.append({"reminder_type": "water", "title": "Drink water", "reminder_time": t.isoformat(), "frequency": "daily"})

    suggestions.append({"reminder_type": "vitamin", "title": "Take prenatal vitamin", "reminder_time": DEFAULT_TIMES["vitamin"][0].isoformat(), "frequency": "daily"})

    if medical.get("anemia"):
        suggestions.append({"reminder_type": "iron", "title": "Take iron supplement", "reminder_time": DEFAULT_TIMES["iron"][0].isoformat(), "frequency": "daily"})

    suggestions.append({"reminder_type": "calcium", "title": "Calcium-rich meal/supplement", "reminder_time": DEFAULT_TIMES["calcium"][0].isoformat(), "frequency": "daily"})
    suggestions.append({"reminder_type": "sleep", "title": "Wind down for sleep", "reminder_time": DEFAULT_TIMES["sleep"][0].isoformat(), "frequency": "daily"})

    state["suggested_reminders"] = suggestions

    state.setdefault("agent_execution_history", []).append(
        {
            "agent": "reminder_agent",
            "status": "completed",
            "detail": f"Suggested {len(suggestions)} reminder(s)",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    logger.info(f"Reminder agent ran: user_id={state['user_id']}")
    return state
