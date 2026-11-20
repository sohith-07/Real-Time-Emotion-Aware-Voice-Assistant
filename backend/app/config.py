"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed settings with sensible defaults.

    Every option has a working default so the app runs without any .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # --- Server ---
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_name: str = "Emotion-Aware Voice Assistant"
    cors_origins: str = (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:3000,http://127.0.0.1:3000,file://"
    )

    # --- Database ---
    database_url: str = "sqlite:///./assistant.db"

    # --- Emotion ---
    emotion_model: str = "j-hartmann/emotion-english-distilroberta-base"
    emotion_lazy_load: bool = True
    emotion_fallback_enabled: bool = True

    # --- Chat / LLM ---
    chat_engine: str = "auto"  # auto | rule | openai
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"

    # --- Misc ---
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def use_openai(self) -> bool:
        """Resolve the 'auto' chat-engine choice based on whether a key is set."""
        if self.chat_engine == "openai":
            return bool(self.openai_api_key)
        if self.chat_engine == "auto":
            return bool(self.openai_api_key)
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
