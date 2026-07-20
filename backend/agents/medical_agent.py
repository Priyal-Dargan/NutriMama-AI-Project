"""
agents/medical_agent.py
Medical Guidelines Agent. Retrieves trusted medical documents BEFORE generating
a response (RAG). The retrieval backend is a placeholder until Phase 3 builds
the ChromaDB index (see rag/retriever.py) — this agent already refuses to imply
evidence it doesn't have: if nothing is retrieved, the response and confidence
score say so explicitly instead of quietly falling back to ungrounded LLM output.
"""

from datetime import datetime

from agents.state import GraphState
from rag.retriever import retrieve_relevant_documents, is_rag_index_ready
from utils.ai_client import generate_text
from utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are the Medical Guidelines Agent inside NutriMama AI, a pregnancy nutrition "
    "assistant. Answer ONLY using the retrieved context provided below if any is given. "
    "If no context is provided, give general, well-established pregnancy nutrition "
    "guidance and clearly state that this answer is not grounded in a specific cited "
    "source. Always be conservative — when in doubt, recommend the user confirm with "
    "their healthcare provider. Never diagnose."
)


def run_medical_agent(state: GraphState) -> GraphState:
    query = state["user_message"]
    documents = retrieve_relevant_documents(query)
    state["retrieved_documents"] = documents

    if documents:
        context = "\n\n".join(f"[{d['source']}]: {d['snippet']}" for d in documents)
        user_prompt = f"Retrieved context:\n{context}\n\nUser question: {query}"
        confidence = 0.85
    elif is_rag_index_ready():
        context_note = "No relevant documents were found for this query in the indexed knowledge base."
        user_prompt = f"{context_note}\n\nUser question: {query}"
        confidence = 0.4
    else:
        context_note = (
            "The medical document knowledge base has not been indexed yet (Phase 3). "
            "No retrieval was performed."
        )
        user_prompt = f"{context_note}\n\nUser question: {query}"
        confidence = 0.3

    response_text = generate_text(SYSTEM_PROMPT, user_prompt)
    state["medical_guidance"] = response_text

    state.setdefault("confidence_scores", {})["medical_guidelines"] = confidence
    state.setdefault("agent_execution_history", []).append(
        {
            "agent": "medical_guidelines",
            "status": "completed",
            "detail": f"Retrieved {len(documents)} document(s); confidence={confidence}",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    logger.info(f"Medical agent ran: user_id={state['user_id']} docs_retrieved={len(documents)}")
    return state
