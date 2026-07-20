"""
models/chat.py
AI chat conversation log — stores both sides of the exchange plus orchestration metadata
(which agents ran, what was retrieved from RAG) so the chat UI can render the execution timeline.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)

    agents_used = Column(Text, nullable=True)         # JSON array, e.g. ["supervisor","nutrition_planner"]
    retrieved_documents = Column(Text, nullable=True)  # JSON array of {source, snippet}
    confidence_score = Column(Text, nullable=True)     # stored as text since it may include a reason string

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_history")
