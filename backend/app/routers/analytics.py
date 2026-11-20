"""Analytics router: aggregate stats for the dashboard."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Conversation, Message
from ..services import emotion_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
def analytics(db: Session = Depends(get_db)) -> dict:
    """Compute conversation + emotion analytics for the dashboard."""
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    total_user = db.query(func.count(Message.id)).filter(Message.role == "user").scalar() or 0
    total_assistant = (
        db.query(func.count(Message.id)).filter(Message.role == "assistant").scalar() or 0
    )

    # Emotion distribution over USER messages only (assistant messages are
    # always tagged 'neutral' and would skew the chart otherwise).
    rows = (
        db.query(Message.emotion, func.count(Message.id))
        .filter(Message.role == "user")
        .filter(Message.emotion.isnot(None))
        .group_by(Message.emotion)
        .all()
    )
    counts = {label: 0 for label in emotion_service.ALL_LABELS}
    for label, n in rows:
        if label in counts:
            counts[label] = n
        else:
            counts[label] = counts.get(label, 0) + n
    total_emotion = sum(counts.values()) or 1
    distribution = [
        {
            "label": label,
            "count": counts[label],
            "percentage": round(counts[label] / total_emotion * 100, 2),
        }
        for label in counts
    ]
    most_frequent = max(counts, key=counts.get) if sum(counts.values()) > 0 else None

    # Recent messages (newest 20).
    recent = (
        db.query(Message)
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )
    recent_messages = [
        {
            "id": m.id,
            "conversation_id": m.conversation_id,
            "role": m.role,
            "content": m.content,
            "emotion": m.emotion,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in recent
    ]

    # Daily message counts for the last 14 days (for a trend chart).
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    daily_rows = (
        db.query(
            func.date(Message.created_at).label("day"),
            func.count(Message.id).label("n"),
        )
        .filter(Message.created_at >= cutoff)
        .group_by("day")
        .order_by("day")
        .all()
    )
    daily_counts = [{"date": str(d), "count": int(n)} for d, n in daily_rows]

    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_user_messages": total_user,
        "total_assistant_messages": total_assistant,
        "most_frequent_emotion": most_frequent,
        "emotion_distribution": distribution,
        "recent_messages": recent_messages,
        "daily_counts": daily_counts,
    }
