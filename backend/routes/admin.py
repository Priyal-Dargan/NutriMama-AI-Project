"""
routes/admin.py
Admin panel endpoints: RAG document management (upload new PDFs, rebuild the
ChromaDB index), basic usage analytics, and feedback review — per the spec's
Admin Panel requirements. All routes require is_admin=True (see dependencies.py).
"""

import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from dependencies import get_current_admin
from models.user import User
from models.chat import ChatHistory
from models.reports import Feedback
from rag.chromadb import rebuild_index, index_stats, DOCUMENTS_DIR
from rag.embedding import get_embedder_type
from utils.logger import get_logger

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = get_logger(__name__)


@router.get("/dashboard")
def admin_dashboard(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    total_users = db.query(func.count(User.id)).scalar()
    total_chats = db.query(func.count(ChatHistory.id)).scalar()
    avg_feedback_rating = db.query(func.avg(Feedback.rating)).scalar()

    return {
        "total_users": total_users,
        "total_ai_chat_messages": total_chats,
        "average_feedback_rating": round(avg_feedback_rating, 2) if avg_feedback_rating else None,
        "rag_index": index_stats(),
    }


@router.get("/feedback")
def list_feedback(
    limit: int = 50,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    entries = db.query(Feedback).order_by(Feedback.created_at.desc()).limit(limit).all()
    return [
        {
            "id": f.id,
            "user_id": f.user_id,
            "rating": f.rating,
            "feedback_text": f.feedback_text,
            "feature_request": f.feature_request,
            "bug_report": f.bug_report,
            "created_at": f.created_at,
        }
        for f in entries
    ]


# --- RAG document management ------------------------------------------------

@router.get("/rag/status")
def rag_status(admin: User = Depends(get_current_admin)):
    stats = index_stats()
    stats["embedder_type"] = get_embedder_type()
    stats["documents_on_disk"] = [
        f for f in sorted(os.listdir(DOCUMENTS_DIR)) if f.lower().endswith(".pdf")
    ] if os.path.isdir(DOCUMENTS_DIR) else []
    return stats


@router.post("/rag/upload-document", status_code=status.HTTP_201_CREATED)
async def upload_rag_document(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_admin),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted for the RAG knowledge base.",
        )

    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    dest_path = os.path.join(DOCUMENTS_DIR, file.filename)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    logger.info(f"RAG document uploaded by admin_id={admin.id}: {file.filename}")
    return {
        "message": f"Uploaded {file.filename}. Call POST /admin/rag/rebuild-index to index it.",
        "filename": file.filename,
    }


@router.post("/rag/rebuild-index")
def rebuild_rag_index(admin: User = Depends(get_current_admin)):
    stats = rebuild_index()
    logger.info(f"RAG index rebuilt by admin_id={admin.id}: {stats}")
    return {
        "message": "RAG index rebuilt successfully.",
        **stats,
        "embedder_type": get_embedder_type(),
    }
