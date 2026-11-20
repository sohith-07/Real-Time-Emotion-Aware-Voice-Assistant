"""Conversations router: list, get, delete, clear."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Conversation, Message

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """List conversations newest first."""
    rows = (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"conversations": [c.to_dict() for c in rows], "count": len(rows)}


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db)) -> dict:
    """Get a single conversation with all its messages."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv.to_dict(include_messages=True)


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)) -> dict:
    """Delete a conversation and all of its messages."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"deleted": conversation_id}


@router.post("/clear")
def clear_all(db: Session = Depends(get_db)) -> dict:
    """Delete every conversation and all of its messages (used by 'Clear chat' in the UI)."""
    # Delete messages FIRST so we don't violate the FK from messages -> conversations.
    db.query(Message).delete()
    deleted = db.query(Conversation).delete()
    db.commit()
    return {"deleted_conversations": deleted}


@router.get("/{conversation_id}/messages")
def list_messages(conversation_id: str, db: Session = Depends(get_db)) -> dict:
    """List messages of a conversation in chronological order."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return {"messages": [m.to_dict() for m in msgs], "count": len(msgs)}
