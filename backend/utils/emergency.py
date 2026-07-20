"""
utils/emergency.py
Emergency symptom detection. Runs BEFORE any nutrition/meal-planning agent.
Deterministic keyword matching — intentionally not LLM-based, so this safety
check can never be skipped, hallucinated around, or rate-limited by an API outage.
"""

import re
from typing import Optional, Tuple

# Each tuple: (regex pattern, human-readable reason). Patterns are intentionally
# broad/plain-language since users won't phrase symptoms clinically.
EMERGENCY_PATTERNS = [
    (r"\bheavy (vaginal )?bleeding\b", "Heavy vaginal bleeding"),
    (r"\bsevere (abdominal|stomach|belly) pain\b", "Severe abdominal pain"),
    (r"\bchest pain\b", "Chest pain"),
    (r"\b(can'?t|cannot|difficulty) breath", "Difficulty breathing"),
    (r"\blost? consciousness\b|\bfainted\b|\bpassed out\b", "Loss of consciousness"),
    (r"\bseizure\b|\bconvulsion\b", "Seizures"),
    (r"\b(baby|fetus|fetal).{0,20}(not moving|stopped moving|no movement)\b", "Reduced fetal movement"),
    (r"\breduced fetal movement\b", "Reduced fetal movement"),
    (r"\bhigh fever\b.{0,15}(days|persistent|won'?t go)|\bpersistent (high )?fever\b", "Persistent high fever"),
    (r"\bsevere headache\b.{0,20}(vision|blurry|swelling)", "Severe headache with vision changes (possible preeclampsia)"),
    (r"\bwater broke\b|\bwater has broken\b", "Possible rupture of membranes"),
]

EMERGENCY_MESSAGE = (
    "⚠️ This may describe a medical emergency. I can't assess or diagnose this. "
    "Please contact your healthcare provider immediately or go to the nearest "
    "emergency room. If you believe this is life-threatening, call your local "
    "emergency number right now."
)


def detect_emergency(message: str) -> Tuple[bool, Optional[str]]:
    """Returns (is_emergency, matched_reason)."""
    lowered = message.lower()
    for pattern, reason in EMERGENCY_PATTERNS:
        if re.search(pattern, lowered):
            return True, reason
    return False, None
