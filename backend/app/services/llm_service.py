"""Conversation / dialogue generation service.

Two engines:
  * ``rule``  - an emotion-aware, context-aware rule-based dialogue engine that
                adapts tone to detected emotion, tracks recent turns, avoids
                repetition, asks follow-up questions and offers help.
  * ``openai`` - optional Chat Completions integration (only used when an
                OPENAI_API_KEY is configured in .env).

Selection is automatic: if an API key is set and ``CHAT_ENGINE`` is ``auto``
or ``openai``, the OpenAI engine is used; otherwise the rule engine is used.
Both engines receive the detected emotion so the assistant's tone always
matches the user's state.
"""
from __future__ import annotations

import logging
import random
from typing import Dict, List, Tuple

from ..config import settings

logger = logging.getLogger(__name__)


# ============================================================
# Emotion-aware rule engine
# ============================================================
# Each emotion has a tone descriptor and a pool of opening / acknowledgement
# phrases. The engine combines an acknowledgement with a content reply built
# from intent templates, so outputs vary and stay non-repetitive.

_TONE_ACK: Dict[str, List[str]] = {
    "joy": [
        "That's wonderful to hear — your excitement really comes through!",
        "I love that energy! It sounds like things are going well for you.",
        "That's genuinely great. I'm glad you're feeling good about it.",
        "What a bright moment — thanks for sharing it with me.",
    ],
    "sadness": [
        "I'm really sorry you're going through that. That sounds hard.",
        "I hear you, and it's okay to feel this way. You're not alone in it.",
        "That sounds genuinely painful. Take your time — I'm here to listen.",
        "I appreciate you trusting me with that. It makes sense to feel down.",
    ],
    "anger": [
        "I can tell that really frustrated you. Let's take it step by step.",
        "That sounds genuinely aggravating. I want to understand it properly.",
        "You have every right to be annoyed. Let's look at it together calmly.",
        "I hear the frustration loud and clear. Let me help where I can.",
    ],
    "fear": [
        "It's understandable to feel anxious about that. You're safe here.",
        "That sounds worrying. Let's break it down so it feels less overwhelming.",
        "I can see why that would feel scary. We'll work through it together.",
        "Take a breath — what you're feeling is valid. Let's take it slowly.",
    ],
    "surprise": [
        "Wow, that's quite a turn! Tell me more about what happened.",
        "That really is unexpected — I'm curious to hear the rest.",
        "Oh, I didn't see that coming either! What was your first reaction?",
        "That's a genuine surprise. How are you processing it?",
    ],
    "disgust": [
        "That does sound unpleasant. I get why it left a bad impression.",
        "Ugh, I can see why that bothered you. Let's talk it through.",
        "That's a fair reaction — some things really do unsettle us.",
        "I understand why that felt off. What would you like to do next?",
    ],
    "neutral": [
        "Got it. Let me help with that.",
        "Understood — tell me a bit more so I can give a useful answer.",
        "Okay, I'm following. What would you like to explore?",
        "Thanks for sharing that. Here's what I can offer.",
    ],
}

# Intent templates keyed by simple keyword patterns.
_INTENTS: List[Tuple[List[str], List[str]]] = [
    (["hello", "hi", "hey", "greetings", "good morning", "good evening"],
     [
         "Hi there! I'm your emotion-aware voice assistant. How are you feeling today?",
         "Hello! I'm here to chat or help with whatever's on your mind.",
         "Hey! Great to see you. What would you like to talk about?",
     ]),
    (["how are you", "how do you feel", "how's it going"],
     [
         "I'm doing well, thank you for asking! More importantly — how are you?",
         "Running smoothly and ready to help. How are you holding up today?",
         "All good on my end! Tell me, how has your day been so far?",
     ]),
    (["who are you", "what are you", "your name"],
     [
         "I'm an emotion-aware voice assistant. I listen, detect how you're "
         "feeling from your words, and tailor my replies to your mood.",
         "I'm your AI assistant — built to understand not just what you say "
         "but how you feel when you say it.",
     ]),
    (["what can you do", "help me", "capabilities", "features"],
     [
         "I can hold voice or text conversations, detect your emotion, adapt "
         "my tone accordingly, and show you analytics on our chats. Want a demo?",
         "I support real-time speech, text chat, emotion detection and an "
         "analytics dashboard. Where would you like to start?",
     ]),
    (["thank", "thanks", "appreciate"],
     [
         "You're very welcome! I'm glad I could help.",
         "Anytime — that's what I'm here for.",
         "Happy to help! Is there anything else on your mind?",
     ]),
    (["bye", "goodbye", "see you", "later"],
     [
         "Take care of yourself! I'm here whenever you want to talk again.",
         "Goodbye for now — be well, and come back any time.",
         "See you later! Looking forward to our next conversation.",
     ]),
    (["joke", "funny", "make me laugh"],
     [
         "Here's one: why don't scientists trust atoms? Because they make up "
         "everything! Want another?",
         "I tried to catch fog the other day... I mist. Need a better one?",
     ]),
    (["weather", "temperature", "forecast"],
     [
         "I can't pull live weather data without an internet lookup, but I can "
         "help you plan around any forecast you share. What's it like outside?",
     ]),
    (["time", "what day", "today's date"],
     [
         "I don't have a live clock display handy, but I can help you reason "
         "about scheduling. What did you need to plan?",
     ]),
    (["sad", "depressed", "lonely", "cry"],
     [
         "I'm sorry you're feeling low. Sometimes naming it helps — would you "
         "like to talk about what's weighing on you?",
         "That sounds really heavy. I'm not a substitute for professional "
         "support, but I'm here to listen for as long as you need.",
     ]),
    (["stressed", "anxious", "worried", "nervous"],
     [
         "Anxiety can be exhausting. One small thing that helps is naming the "
         "specific worry — want to walk me through it?",
         "When stress builds up, breaking the problem into steps can lighten "
         "the load. What feels most pressing right now?",
     ]),
    (["love", "relationship", "breakup"],
     [
         "Relationships are complicated and your feelings about them are valid. "
         "Would you like to talk through what happened?",
         "Matters of the heart deserve real care. I'm here to listen — share "
         "as much or as little as you'd like.",
     ]),
    (["work", "job", "boss", "deadline", "meeting"],
     [
         "Work pressures can really pile up. Want help thinking through "
         "priorities or drafting a response?",
         "Sounds like a workplace challenge — I can help you plan next steps "
         "or just vent. What would help most?",
     ]),
    (["study", "exam", "assignment", "homework", "college"],
     [
         "Studying can be intense. I can quiz you, summarise topics, or help "
         "you structure your revision. What subject?",
         "Exams and deadlines are stressful — let's break the work into "
         "manageable pieces. What's coming up first?",
     ]),
    (["yes", "yeah", "sure", "okay", "ok"],
     [
         "Great — let's dig in. What would you like to focus on?",
         "Perfect. Tell me a bit more so I can help precisely.",
     ]),
    (["no", "nope", "not really"],
     [
         "No problem at all. Is there something else I can help with?",
         "That's fine — we can change direction. What's on your mind?",
     ]),
]

# Generic follow-ups to push the conversation forward without looping.
_FOLLOWUPS = [
    "Would you like to explore that a bit more?",
    "What's the next thing on your mind?",
    "Is there anything else I can help you with right now?",
    "How would you like to take this forward?",
    "Want me to go deeper on any part of that?",
]

# Questions explicitly seeking info.
_QUESTION_HINTS = ["what", "why", "how", "when", "where", "who", "can you",
                   "could you", "do you", "is it", "are you", "?"]


def _match_intent(text: str) -> List[str]:
    lowered = text.lower()
    for keywords, templates in _INTENTS:
        if any(kw in lowered for kw in keywords):
            return templates
    return []


def _is_question(text: str) -> bool:
    lowered = text.lower()
    return lowered.endswith("?") or any(h in lowered for h in _QUESTION_HINTS)


def _acknowledgement(emotion: str, recent_replies: List[str]) -> str:
    pool = _TONE_ACK.get(emotion, _TONE_ACK["neutral"])
    # Avoid the last acknowledgement used.
    choices = [p for p in pool if p not in recent_replies[-3:]] or pool
    return random.choice(choices)


def _compose_reply(text: str, emotion: str, history: List[Dict[str, str]]) -> str:
    """Build a non-repetitive, emotion-aware reply."""
    # Collect recent assistant text to avoid verbatim repeats.
    recent_replies = [m["content"] for m in history if m["role"] == "assistant"]

    ack = _acknowledgement(emotion, recent_replies)

    intent_templates = _match_intent(text)
    if intent_templates:
        usable = [t for t in intent_templates if t not in recent_replies] or intent_templates
        body = random.choice(usable)
        # 50% chance to add a follow-up so the exchange keeps flowing.
        if random.random() < 0.5:
            body = body + " " + random.choice(_FOLLOWUPS)
        return ack + " " + body

    if _is_question(text):
        return (
            ack + " That's a thoughtful question. Based on what you've shared, "
            "I'd suggest looking at it from a couple of angles: the practical "
            "trade-offs and how it sits with how you're feeling right now. "
            "Could you tell me a bit more about what's driving the question?"
        )

    # Default reflective reply - acknowledges and gently opens the next turn.
    follow = random.choice(_FOLLOWUPS)
    return ack + " " + follow


# ============================================================
# OpenAI engine
# ============================================================
def _openai_reply(text: str, emotion: str, history: List[Dict[str, str]]) -> str:
    """Use the OpenAI Chat Completions API. Returns None on failure."""
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover
        logger.warning("openai package not available: %s", exc)
        return ""

    if not settings.openai_api_key:
        return ""

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        system = (
            "You are a warm, emotionally intelligent voice assistant. The user's "
            f"current detected emotion is '{emotion}'. Adapt your tone: be "
            "enthusiastic for joy, empathetic for sadness, calm for anger, "
            "reassuring for fear, curious for surprise, understanding for "
            "disgust, and natural for neutral. Keep replies concise (2-4 "
            "sentences), friendly and helpful."
        )
        messages = [{"role": "system", "content": system}]
        for m in history[-10:]:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": text})
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # pragma: no cover
        logger.warning("OpenAI call failed (%s); falling back to rule engine.", exc)
        return ""


# ============================================================
# Public API
# ============================================================
def generate_reply(
    text: str,
    emotion: str,
    history: List[Dict[str, str]],
) -> Tuple[str, str]:
    """Generate a reply. Returns (reply_text, engine_used)."""
    if settings.use_openai:
        reply = _openai_reply(text, emotion, history)
        if reply:
            return reply, "openai"
        # fall through to rule engine on failure
        logger.info("OpenAI unavailable or failed; using rule engine.")
    reply = _compose_reply(text, emotion, history)
    return reply, "rule"


def active_engine() -> str:
    return "openai" if settings.use_openai else "rule"
