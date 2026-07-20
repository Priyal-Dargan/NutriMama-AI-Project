"""
routes/ai_chat.py
AI Chat endpoint. Every message is routed through the Supervisor Agent
(agents/supervisor.py), which runs the full LangGraph workflow: emergency
check -> intent detection -> profile load -> conditional specialist agents ->
response synthesis. The full agent execution timeline, confidence scores, and
retrieved sources are returned so the frontend can render transparency UI.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.user import User
from models.chat import ChatHistory
from agents.supervisor import run_supervisor
from utils.logger import get_logger

router = APIRouter(prefix="/chat", tags=["AI Chat"])
logger = get_logger(__name__)

CHAT_HISTORY_TURNS = 6  # how many prior turns to load as context


class ChatRequest(BaseModel):
    message: str


class RetrievedSource(BaseModel):
    source: str
    snippet: str


class AgentTimelineEntry(BaseModel):
    agent: str
    status: str
    detail: Optional[str] = None
    timestamp: str


class ChatResponse(BaseModel):
    response: str
    agents_used: List[str]
    agent_timeline: List[AgentTimelineEntry]
    confidence_scores: dict
    retrieved_sources: List[RetrievedSource] = []
    emergency_detected: bool = False
    disclaimer: str = (
        "This assistant provides educational information only and is not a substitute "
        "for professional medical advice. Always consult a qualified healthcare professional "
        "before making medical decisions."
    )


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Load recent chat history for conversational context.
    recent = (
        db.query(ChatHistory)
        .filter_by(user_id=current_user.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(CHAT_HISTORY_TURNS)
        .all()
    )
    history = []
    for turn in reversed(recent):
        history.append({"role": "user", "content": turn.user_message})
        history.append({"role": "assistant", "content": turn.ai_response})

    final_state = run_supervisor(
        user_id=current_user.id,
        message=payload.message,
        chat_history=history,
        db=db,
    )

    agents_used = [
        entry["agent"] for entry in final_state.get("agent_execution_history", [])
        if entry["status"] == "completed"
    ]
    retrieved_sources = [
        RetrievedSource(source=d.get("source", "unknown"), snippet=d.get("snippet", ""))
        for d in final_state.get("retrieved_documents", [])
    ]
    confidence_scores = final_state.get("confidence_scores", {})
    overall_confidence = (
        round(sum(confidence_scores.values()) / len(confidence_scores), 2)
        if confidence_scores else None
    )

    response_text = final_state.get("final_response", "I wasn't able to generate a response.")

    # Persist the exchange.
    chat_record = ChatHistory(
        user_id=current_user.id,
        user_message=payload.message,
        ai_response=response_text,
        agents_used=json.dumps(agents_used),
        retrieved_documents=json.dumps([s.model_dump() for s in retrieved_sources]),
        confidence_score=json.dumps(confidence_scores),
    )
    db.add(chat_record)
    db.commit()

    logger.info(
        f"Chat processed: user_id={current_user.id} intent={final_state.get('detected_intent')} "
        f"agents_used={agents_used} emergency={final_state.get('emergency_detected')}"
    )

    return ChatResponse(
        response=response_text,
        agents_used=agents_used,
        agent_timeline=[AgentTimelineEntry(**entry) for entry in final_state.get("agent_execution_history", [])],
        confidence_scores=confidence_scores,
        retrieved_sources=retrieved_sources,
        emergency_detected=final_state.get("emergency_detected", False),
    )


@router.get("/history")
def chat_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = (
        db.query(ChatHistory)
        .filter_by(user_id=current_user.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "user_message": r.user_message,
            "ai_response": r.ai_response,
            "agents_used": json.loads(r.agents_used) if r.agents_used else [],
            "created_at": r.created_at,
        }
        for r in reversed(records)
    ]
