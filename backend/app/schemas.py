"""Pydantic request/response schemas for the API."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- Emotion ----------
class EmotionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class EmotionResult(BaseModel):
    label: str
    confidence: float
    scores: dict[str, float]
    note: str = (
        "Emotion predictions are estimates produced by an ML model and are "
        "not definitive psychological assessments."
    )


# ---------- Chat ----------
class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    mode: str = Field("text", pattern="^(text|voice)$")


class ChatResponse(BaseModel):
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    reply: str
    emotion: str
    emotion_confidence: float
    emotion_scores: dict[str, float]
    engine: str  # rule | openai
    note: str = (
        "Emotion predictions are estimates and not psychological assessments."
    )


# ---------- Conversation / Message ----------
class ConversationOut(BaseModel):
    id: str
    title: str
    mode: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationDetail(ConversationOut):
    messages: List[dict] = []


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    emotion: Optional[str] = None
    emotion_confidence: Optional[float] = None
    emotion_scores: Optional[dict[str, float]] = None
    created_at: Optional[str] = None


# ---------- Analytics ----------
class EmotionDistribution(BaseModel):
    label: str
    count: int
    percentage: float


class AnalyticsOut(BaseModel):
    total_conversations: int
    total_messages: int
    total_user_messages: int
    total_assistant_messages: int
    most_frequent_emotion: Optional[str] = None
    emotion_distribution: List[EmotionDistribution]
    recent_messages: List[dict]
    daily_counts: List[dict]


# ---------- Settings ----------
class SettingIn(BaseModel):
    key: str
    value: str


class SettingOut(BaseModel):
    key: str
    value: str
    updated_at: Optional[str] = None


class SettingsBulkIn(BaseModel):
    settings: List[SettingIn]


# ---------- Health ----------
class HealthOut(BaseModel):
    status: str
    version: str
    emotion_engine: str
    chat_engine: str
    database: str
