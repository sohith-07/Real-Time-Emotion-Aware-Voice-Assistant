"""Emotion detection service.

Primary engine: HuggingFace transformers model
``j-hartmann/emotion-english-distilroberta-base`` which classifies English text
into 7 emotions: joy, sadness, anger, fear, surprise, neutral, disgust.

Fallback: a lightweight keyword + lexical scoring engine that returns the same
7 labels. The fallback is used automatically if transformers / torch are not
installed, if the model cannot be downloaded, or if the model file is missing.

Both engines normalise to the canonical labels required by the UI:
    happy, sad, angry, fear, surprise, neutral, disgust
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Dict, Optional

from ..config import settings

logger = logging.getLogger(__name__)

# Map from model/fallback raw labels -> canonical UI labels.
CANONICAL_LABELS = {
    "joy": "joy",
    "happiness": "joy",
    "happy": "joy",
    "sadness": "sadness",
    "sad": "sadness",
    "anger": "anger",
    "angry": "anger",
    "fear": "fear",
    "surprise": "surprise",
    "neutral": "neutral",
    "disgust": "disgust",
}

ALL_LABELS = ["joy", "sadness", "anger", "fear", "surprise", "neutral", "disgust"]

NOTE = (
    "Emotion predictions are estimates produced by an ML model and are not "
    "definitive psychological assessments."
)


# ============================================================
# Fallback engine (keyword + lexical scoring)
# ============================================================
_LEXICON: Dict[str, Dict[str, int]] = {
    "joy": {
        "happy": 3, "joy": 3, "joyful": 3, "glad": 2, "delighted": 3,
        "excited": 2, "great": 1, "awesome": 2, "wonderful": 2, "love": 2,
        "loved": 2, "loving": 2, "pleased": 2, "fantastic": 3, "amazing": 2,
        "good": 1, "smile": 2, "laugh": 2, "laughing": 2, "fun": 2, "yay": 3,
        "haha": 2, "lol": 2, "cheers": 2, "thanks": 1, "thank": 1,
        "celebrate": 2, "win": 2, "won": 2, "success": 2,
    },
    "sadness": {
        "sad": 3, "unhappy": 3, "depressed": 3, "down": 2, "cry": 3,
        "crying": 3, "tears": 3, "miserable": 3, "lonely": 3, "alone": 2,
        "lost": 2, "hurt": 2, "broken": 2, "heartbroken": 3, "grief": 3,
        "grieving": 3, "sorry": 2, "regret": 2, "miss": 2, "missing": 2,
        "empty": 2, "hopeless": 3, "tired": 1, "exhausted": 2, "sigh": 2,
        "blue": 2, "gloomy": 2, "devastated": 3,
    },
    "anger": {
        "angry": 3, "mad": 3, "furious": 3, "rage": 3, "outraged": 3,
        "annoyed": 2, "irritated": 2, "frustrated": 2, "hate": 3, "hated": 3,
        "stupid": 2, "idiot": 2, "damn": 2, "hell": 1, "crap": 2, "shut": 2,
        "unfair": 2, "ridiculous": 2, "fed up": 3, "fed-up": 3, "pissed": 3,
        "sick of": 2, "enough": 2, "stop": 1, "wrong": 1, "broken": 1,
    },
    "fear": {
        "afraid": 3, "scared": 3, "frightened": 3, "terrified": 3, "fear": 3,
        "fearful": 3, "anxious": 3, "anxiety": 3, "worried": 2, "worry": 2,
        "nervous": 2, "panic": 3, "panic-stricken": 3, "dread": 3,
        "horror": 3, "horrified": 3, "concerned": 2, "uneasy": 2,
        "threat": 2, "danger": 2, "unsafe": 2, "lost": 1, "help": 1,
        "nightmare": 2, "phobia": 3,
    },
    "surprise": {
        "wow": 3, "whoa": 3, "oh": 1, "really": 2, "seriously": 2,
        "surprise": 3, "surprised": 3, "unexpected": 2, "shocked": 3,
        "shock": 3, "amazing": 2, "unbelievable": 3, "incredible": 2,
        "no way": 3, "what": 1, "omg": 3, "gosh": 2, "goodness": 2,
        "didn't expect": 2, "never thought": 2, "sudden": 1, "wait": 1,
        "huh": 2, "ah": 1, "is that": 1,
    },
    "disgust": {
        "disgust": 3, "disgusting": 3, "gross": 3, "yuck": 3, "ew": 3,
        "eww": 3, "nasty": 3, "awful": 2, "terrible": 2, "horrible": 2,
        "revolting": 3, "sickening": 3, "repulsive": 3, "vile": 3,
        "filthy": 2, "stinks": 2, "stink": 2, "ugly": 2, "bad": 1,
        "cringe": 2, "creepy": 2, "bothering": 1,
    },
    "neutral": {
        "okay": 1, "ok": 1, "fine": 1, "alright": 1, "yes": 1, "no": 1,
        "maybe": 1, "perhaps": 1, "so": 1, "the": 1, "a": 1, "i": 1,
        "you": 1, "today": 1, "now": 1, "then": 1, "well": 1,
    },
}

# Negative intensifier boosts anger/sad/fear.
_INTENSIFIERS = {"very": 1.5, "really": 1.3, "so": 1.2, "extremely": 1.7,
                 "totally": 1.3, "absolutely": 1.3, "completely": 1.3}


def _fallback_predict(text: str) -> Dict[str, float]:
    """Lexical scoring fallback. Returns dict of canonical label -> score."""
    if not text or not text.strip():
        return {label: 0.0 for label in ALL_LABELS}

    lowered = text.lower()
    tokens = lowered.split()
    # Build a small list of consecutive token windows for phrase matching.
    windows = tokens + [" ".join(tokens[i:i + 2]) for i in range(len(tokens) - 1)] + \
              [" ".join(tokens[i:i + 3]) for i in range(len(tokens) - 2)]

    scores: Dict[str, float] = {label: 0.0 for label in ALL_LABELS}
    intensifier = 1.0
    for w in _INTENSIFIERS:
        if w in tokens:
            intensifier = max(intensifier, _INTENSIFIERS[w])

    for label, words in _LEXICON.items():
        for w in words:
            for token in windows:
                if token == w or (token.startswith(w) and len(w) >= 4):
                    scores[label] += words[w] * intensifier

    total = sum(scores.values())
    if total == 0:
        # Truly no signal -> neutral.
        scores["neutral"] = 1.0
        total = 1.0

    # Softmax-ish normalisation to probabilities in [0,1].
    normalised = {k: v / total for k, v in scores.items()}
    # Lift the dominant a touch for confidence.
    top = max(normalised.values())
    if top < 0.5 and normalised["neutral"] == max(normalised.values()):
        normalised["neutral"] = max(normalised["neutral"], 0.45)
        s = sum(normalised.values())
        normalised = {k: v / s for k, v in normalised.items()}
    return normalised


# ============================================================
# Transformers engine
# ============================================================
class _TransformersEngine:
    """Lazy singleton wrapper around the HF pipeline."""

    _lock = threading.Lock()
    _pipeline = None
    _load_error: Optional[str] = None

    @classmethod
    def get(cls):
        """Return a working pipeline or None (with reason logged once)."""
        if cls._pipeline is not None:
            return cls._pipeline
        if cls._load_error is not None:
            return None  # already failed once
        with cls._lock:
            if cls._pipeline is not None:
                return cls._pipeline
            try:
                from transformers import pipeline  # type: ignore

                logger.info("Loading emotion model '%s'...", settings.emotion_model)
                cls._pipeline = pipeline(
                    "text-classification",
                    model=settings.emotion_model,
                    top_k=None,  # return all labels
                    tokenizer=settings.emotion_model,
                )
                logger.info("Emotion model loaded successfully.")
                return cls._pipeline
            except Exception as exc:  # pragma: no cover - depends on env
                cls._load_error = str(exc)
                logger.warning(
                    "Could not load HuggingFace emotion model '%s': %s. "
                    "Falling back to lexical engine.",
                    settings.emotion_model,
                    exc,
                )
                return None

    @classmethod
    def status(cls) -> str:
        if cls._pipeline is not None:
            return "transformers"
        if cls._load_error is not None:
            return "fallback"
        return "uninitialised"


def _transformers_predict(text: str) -> Optional[Dict[str, float]]:
    pipe = _TransformersEngine.get()
    if pipe is None:
        return None
    try:
        results = pipe(text[:2000])  # truncate to model's safe range
        # `top_k=None` returns a list of {label, score} dicts.
        if results and isinstance(results, list):
            raw = results[0] if isinstance(results[0], list) else results
            scores: Dict[str, float] = {label: 0.0 for label in ALL_LABELS}
            for item in raw:
                label = CANONICAL_LABELS.get(
                    str(item.get("label", "")).lower(), "neutral"
                )
                scores[label] = scores.get(label, 0.0) + float(item.get("score", 0.0))
            total = sum(scores.values()) or 1.0
            return {k: v / total for k, v in scores.items()}
    except Exception as exc:  # pragma: no cover
        logger.warning("Transformers inference failed: %s. Using fallback.", exc)
    return None


# ============================================================
# Public API
# ============================================================
def predict_emotion(text: str) -> Dict[str, float]:
    """Return canonical-label probability scores for the given text."""
    if not isinstance(text, str) or not text.strip():
        scores = {label: 0.0 for label in ALL_LABELS}
        scores["neutral"] = 1.0
        return scores

    if settings.emotion_fallback_enabled:
        scores = _transformers_predict(text)
        if scores is None:
            scores = _fallback_predict(text)
    else:
        scores = _transformers_predict(text) or {l: 0.0 for l in ALL_LABELS}
        if not any(scores.values()):
            scores = _fallback_predict(text)
    return scores


def detect(text: str) -> Dict[str, object]:
    """Detect emotion and return a structured result dict."""
    scores = predict_emotion(text)
    if not any(scores.values()):
        top_label, confidence = "neutral", 0.0
    else:
        top_label = max(scores, key=scores.get)  # type: ignore[arg-type]
        confidence = scores[top_label]
    return {
        "label": top_label,
        "confidence": round(confidence, 4),
        "scores": {k: round(v, 4) for k, v in scores.items()},
        "engine": _TransformersEngine.status() if settings.emotion_fallback_enabled else "transformers",
        "note": NOTE,
    }


def engine_status() -> str:
    if not settings.emotion_fallback_enabled:
        return "transformers"
    return _TransformersEngine.status()
