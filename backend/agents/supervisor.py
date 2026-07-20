"""
agents/supervisor.py
Supervisor Agent — the central LangGraph orchestrator. Builds a StateGraph where
every user request passes through: emergency check -> intent detection ->
profile loading -> conditional routing to only the specialist agents required ->
response synthesis. The Supervisor itself never generates nutrition advice —
its only job is orchestration, per the spec.

The graph is compiled once at import time and reused across requests (cheap);
each invocation gets a fresh state built from the current user's DB row + message.
"""

from datetime import datetime
from typing import List

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from agents.state import GraphState
from agents.intent import detect_intent, determine_required_agents
from agents.profile_agent import run_profile_agent
from agents.nutrition_agent import run_nutrition_agent
from agents.medical_agent import run_medical_agent
from agents.food_safety_agent import run_food_safety_agent
from agents.meal_optimizer import run_meal_optimizer_agent
from agents.reminder_agent import run_reminder_agent
from agents.monitoring_agent import run_monitoring_agent
from agents.synthesizer import synthesize_response
from utils.emergency import detect_emergency, EMERGENCY_MESSAGE
from utils.logger import get_logger

logger = get_logger(__name__)


# --- Node functions -------------------------------------------------------
# Each node takes and returns a GraphState. DB-dependent agents receive `db`
# via closures built in `build_graph_runner`, since LangGraph nodes only take state.

def make_emergency_check_node():
    def node(state: GraphState) -> GraphState:
        is_emergency, reason = detect_emergency(state["user_message"])
        state["emergency_detected"] = is_emergency
        state["emergency_reason"] = reason
        if is_emergency:
            state["final_response"] = EMERGENCY_MESSAGE
            logger.warning(f"EMERGENCY detected: user_id={state['user_id']} reason={reason}")
        state.setdefault("agent_execution_history", []).append(
            {
                "agent": "supervisor_emergency_check",
                "status": "completed",
                "detail": f"emergency={is_emergency}" + (f" ({reason})" if reason else ""),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        return state
    return node


def make_intent_node():
    def node(state: GraphState) -> GraphState:
        intent = detect_intent(state["user_message"])
        required = determine_required_agents(intent)
        state["detected_intent"] = intent
        state["required_agents"] = required
        state.setdefault("agent_execution_history", []).append(
            {
                "agent": "supervisor_intent_detection",
                "status": "completed",
                "detail": f"intent={intent}, required_agents={required}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        logger.info(f"Intent detected: user_id={state['user_id']} intent={intent}")
        return state
    return node


def make_profile_node(db: Session):
    def node(state: GraphState) -> GraphState:
        return run_profile_agent(state, db)
    return node


def make_monitoring_node(db: Session):
    def node(state: GraphState) -> GraphState:
        return run_monitoring_agent(state, db)
    return node


def make_meal_optimizer_node(db: Session):
    # The Meal Optimization Agent is now agentic (see agents/meal_optimizer.py): it
    # reasons over blood reports, nutrition/weight logs, and meal history, so -- like
    # profile_agent and monitoring_agent above -- it needs a DB session closed over here.
    def node(state: GraphState) -> GraphState:
        return run_meal_optimizer_agent(state, db)
    return node


def make_synthesis_node():
    def node(state: GraphState) -> GraphState:
        if state.get("emergency_detected"):
            return state  # response already set by emergency node
        state["final_response"] = synthesize_response(state)
        state.setdefault("agent_execution_history", []).append(
            {
                "agent": "supervisor_synthesis",
                "status": "completed",
                "detail": "Merged specialist agent outputs into final response",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        return state
    return node


def _skip_node(agent_name: str):
    def node(state: GraphState) -> GraphState:
        state.setdefault("agent_execution_history", []).append(
            {
                "agent": agent_name,
                "status": "skipped",
                "detail": "Not required for detected intent",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        return state
    return node


# --- Conditional routing ---------------------------------------------------

def _route_after_emergency(state: GraphState) -> str:
    return "end" if state.get("emergency_detected") else "intent_detection"


def _make_agent_router(agent_key: str, node_name: str):
    """Returns a router function: runs `node_name` only if agent_key is in required_agents."""
    def router(state: GraphState) -> str:
        return node_name if agent_key in state.get("required_agents", []) else f"skip_{node_name}"
    return router


# --- Graph builder -----------------------------------------------------------

def build_graph(db: Session):
    """
    Builds and compiles the LangGraph StateGraph for one request. Rebuilt per-request
    (cheap — no I/O at build time) so DB-dependent nodes can close over the current
    session cleanly without leaking sessions across requests.
    """
    graph = StateGraph(GraphState)

    graph.add_node("emergency_check", make_emergency_check_node())
    graph.add_node("intent_detection", make_intent_node())
    graph.add_node("profile_agent", make_profile_node(db))

    graph.add_node("nutrition_agent", lambda s: run_nutrition_agent(s))
    graph.add_node("skip_nutrition_agent", _skip_node("nutrition_agent"))

    graph.add_node("medical_agent", lambda s: run_medical_agent(s))
    graph.add_node("skip_medical_agent", _skip_node("medical_agent"))

    graph.add_node("food_safety_agent", lambda s: run_food_safety_agent(s))
    graph.add_node("skip_food_safety_agent", _skip_node("food_safety_agent"))

    graph.add_node("meal_optimizer", make_meal_optimizer_node(db))
    graph.add_node("skip_meal_optimizer", _skip_node("meal_optimizer"))

    graph.add_node("reminder_agent", lambda s: run_reminder_agent(s))
    graph.add_node("skip_reminder_agent", _skip_node("reminder_agent"))

    graph.add_node("monitoring_agent", make_monitoring_node(db))
    graph.add_node("skip_monitoring_agent", _skip_node("monitoring_agent"))

    graph.add_node("synthesis", make_synthesis_node())

    graph.set_entry_point("emergency_check")
    graph.add_conditional_edges("emergency_check", _route_after_emergency, {
        "end": END,
        "intent_detection": "intent_detection",
    })

    graph.add_edge("intent_detection", "profile_agent")

    # After profile loads, fan out through each optional specialist in sequence,
    # each conditionally routed based on required_agents from intent detection.
    graph.add_conditional_edges("profile_agent", _make_agent_router("nutrition_agent", "nutrition_agent"), {
        "nutrition_agent": "nutrition_agent", "skip_nutrition_agent": "skip_nutrition_agent",
    })
    for src in ["nutrition_agent", "skip_nutrition_agent"]:
        graph.add_conditional_edges(src, _make_agent_router("medical_agent", "medical_agent"), {
            "medical_agent": "medical_agent", "skip_medical_agent": "skip_medical_agent",
        })
    for src in ["medical_agent", "skip_medical_agent"]:
        graph.add_conditional_edges(src, _make_agent_router("food_safety_agent", "food_safety_agent"), {
            "food_safety_agent": "food_safety_agent", "skip_food_safety_agent": "skip_food_safety_agent",
        })
    for src in ["food_safety_agent", "skip_food_safety_agent"]:
        graph.add_conditional_edges(src, _make_agent_router("meal_optimizer", "meal_optimizer"), {
            "meal_optimizer": "meal_optimizer", "skip_meal_optimizer": "skip_meal_optimizer",
        })
    for src in ["meal_optimizer", "skip_meal_optimizer"]:
        graph.add_conditional_edges(src, _make_agent_router("reminder_agent", "reminder_agent"), {
            "reminder_agent": "reminder_agent", "skip_reminder_agent": "skip_reminder_agent",
        })
    for src in ["reminder_agent", "skip_reminder_agent"]:
        graph.add_conditional_edges(src, _make_agent_router("monitoring_agent", "monitoring_agent"), {
            "monitoring_agent": "monitoring_agent", "skip_monitoring_agent": "skip_monitoring_agent",
        })

    graph.add_edge("monitoring_agent", "synthesis")
    graph.add_edge("skip_monitoring_agent", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()


def run_supervisor(user_id: int, message: str, chat_history: List[dict], db: Session) -> GraphState:
    """Entry point called by routes/ai_chat.py."""
    initial_state: GraphState = {
        "user_id": user_id,
        "user_message": message,
        "chat_history": chat_history,
        "agent_execution_history": [],
        "confidence_scores": {},
        "retrieved_documents": [],
    }

    compiled_graph = build_graph(db)
    final_state = compiled_graph.invoke(initial_state)
    return final_state