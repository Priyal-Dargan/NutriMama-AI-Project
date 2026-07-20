"""
agents/state.py
Shared LangGraph state passed between every agent. Each agent reads what it needs
and writes only the fields it owns (documented per-field below) — this is what
lets agents stay decoupled while still sharing context within one request.
"""

from typing import TypedDict, List, Dict, Optional, Any


class AgentLogEntry(TypedDict):
    agent: str
    status: str          # "completed" | "skipped" | "error"
    detail: Optional[str]
    timestamp: str


class GraphState(TypedDict, total=False):
    # --- Input (set by the /chat route before invoking the graph) ---
    user_id: int
    user_message: str

    # --- Loaded by Profile Agent ---
    user_profile: Optional[Dict[str, Any]]          # pregnancy profile fields + bmi/week/trimester
    medical_conditions: Optional[Dict[str, Any]]      # medical_history fields
    diet_preferences: Optional[Dict[str, Any]]        # diet_preferences fields
    available_ingredients: Optional[List[str]]

    # --- Set by Supervisor during routing ---
    detected_intent: Optional[str]                    # e.g. "meal_plan", "food_safety", "general_nutrition"
    required_agents: List[str]
    emergency_detected: bool
    emergency_reason: Optional[str]

    # --- Written by Nutrition Planner Agent ---
    nutrition_requirements: Optional[Dict[str, Any]]   # calories, protein, iron, calcium, folate, etc.

    # --- Written by Medical Guidelines Agent ---
    retrieved_documents: List[Dict[str, str]]          # [{"source": ..., "snippet": ...}]
    medical_guidance: Optional[str]

    # --- Written by Food Safety Agent ---
    food_safety_results: Optional[Dict[str, Any]]      # {"food": ..., "classification": ..., "reason": ...}

    # --- Written by Meal Optimization Agent ---
    meal_plan: Optional[Dict[str, Any]]

    # --- Written by Reminder Agent ---
    suggested_reminders: Optional[List[Dict[str, Any]]]

    # --- Written by Health Monitoring Agent ---
    health_insights: Optional[Dict[str, Any]]

    # --- Shared context ---
    chat_history: List[Dict[str, str]]                 # recent turns: [{"role": "user"/"assistant", "content": ...}]
    health_logs: Optional[Dict[str, Any]]
    weight_logs: Optional[List[Dict[str, Any]]]
    blood_report_analysis: Optional[Dict[str, Any]]
    reminders: Optional[List[Dict[str, Any]]]

    # --- Execution metadata ---
    agent_execution_history: List[AgentLogEntry]
    confidence_scores: Dict[str, float]

    # --- Final output ---
    final_response: Optional[str]
