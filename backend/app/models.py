"""SQLAlchemy ORM models for conversations, messages and settings."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Session, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=_new_id)
    title = Column(String(255), default="Untitled conversation")
    mode = Column(String(16), default="text")  # 'voice' | 'text'
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    def to_dict(self, include_messages: bool = False) -> dict:
        data = {
            "id": self.id,
            "title": self.title,
            "mode": self.mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=_new_id)
    conversation_id = Column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role = Column(String(16))  # 'user' | 'assistant'
    content = Column(Text)
    emotion = Column(String(32), nullable=True)  # predicted emotion label
    emotion_confidence = Column(Float, nullable=True)
    emotion_scores = Column(Text, nullable=True)  # JSON of all emotion scores
    audio_url = Column(String(512), nullable=True)  # optional TTS link
    created_at = Column(DateTime, default=_utcnow, index=True)

    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self) -> dict:
        try:
            scores = json.loads(self.emotion_scores) if self.emotion_scores else None
        except json.JSONDecodeError:
            scores = None
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "emotion": self.emotion,
            "emotion_confidence": self.emotion_confidence,
            "emotion_scores": scores,
            "audio_url": self.audio_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AppSetting(Base):
    """Key/value store for user-tunable settings."""

    __tablename__ = "app_settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Default settings seeded on first run.
DEFAULT_SETTINGS: dict[str, str] = {
    "auto_play_tts": "true",
    "voice_name": "",
    "speech_rate": "1.0",
    "speech_pitch": "1.0",
    "microphone_enabled": "true",
    "emotion_detection_enabled": "true",
    "theme": "light",
    "language": "en-US",
    "interrupt_enabled": "true",
    "sound_wave_visualizer": "true",
}


def get_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        return row.value
    return DEFAULT_SETTINGS.get(key, default)


def set_setting(db: Session, key: str, value: str) -> AppSetting:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        row = AppSetting(key=key, value=value)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def seed_defaults(db: Session) -> None:
    """Insert any missing default settings on startup."""
    for k, v in DEFAULT_SETTINGS.items():
        if not db.query(AppSetting).filter(AppSetting.key == k).first():
            db.add(AppSetting(key=k, value=v))
    db.commit()
