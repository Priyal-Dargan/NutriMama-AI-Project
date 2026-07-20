"""
agents/intent.py
Lightweight intent detection used by the Supervisor Agent to decide which
specialist agents to invoke. Deterministic keyword-based routing — fast, free,
and predictable. This is a routing decision, not a medical judgment, so a
keyword heuristic is appropriate; contrast with utils/emergency.py which is
safety-critical and always runs regardless of detected intent.
"""

import re
from typing import List

INTENT_KEYWORDS = {
    "food_safety": [
    r"\bsafe\b", r"\beat\b.*\bpregnan", r"\bcan i (eat|have|drink)\b",
    r"\bavoid(ed|s|ing)?\b", r"\bokay\b", r"\bok\b", r"\ballowed\b", r"\bharmful\b",
],
    "meal_plan": [r"\bmeal plan\b", r"\bwhat should i eat\b", r"\brecipe\b", r"\bdiet plan\b", r"\bmenu\b"],
    "medical_guidance": [r"\bshould i\b", r"\bguideline\b", r"\brecommend", r"\brisk\b", r"\bsymptom\b"],
    "reminder": [r"\bremind\b", r"\breminder\b", r"\bschedule\b"],
    "health_check": [r"\bhow am i doing\b", r"\bprogress\b", r"\btrend\b", r"\bdeficien"],
}


def detect_intent(message: str) -> str:
    lowered = message.lower()
    for intent, patterns in INTENT_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, lowered):
                return intent
    return "general_nutrition"


def determine_required_agents(intent: str) -> List[str]:
    """
    Maps a detected intent to the minimal set of specialist agents needed —
    this is the Supervisor's conditional routing table.
    """
    base = ["profile_agent"]  # always load profile context first

    routing_table = {
        "food_safety": base + ["food_safety_agent"],
        "meal_plan": base + ["nutrition_agent", "medical_agent", "meal_optimizer"],
        "medical_guidance": base + ["medical_agent"],
        "reminder": base + ["reminder_agent"],
        "health_check": base + ["nutrition_agent", "monitoring_agent"],
        "general_nutrition": base + ["nutrition_agent", "medical_agent"],
    }
    return routing_table.get(intent, base + ["medical_agent"])
