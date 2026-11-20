"""Settings router: key/value store backed by SQLite."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import DEFAULT_SETTINGS, AppSetting, get_setting, set_setting
from ..schemas import SettingIn, SettingsBulkIn

router = APIRouter(prefix="/api/settings", tags=["settings"])

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
_ENV_FILE = _BACKEND_DIR / ".env"
SECRET_KEYS = {"openai_api_key"}


def _write_env_key(key: str, value: str) -> None:
    """Append or update a key in backend/.env (used for OPENAI_API_KEY)."""
    if not _ENV_FILE.exists():
        _ENV_FILE.write_text("", encoding="utf-8")
    lines = _ENV_FILE.read_text(encoding="utf-8").splitlines()
    prefix = f"{key}="
    updated = False
    for index, line in enumerate(lines):
        if line.strip().startswith(prefix) or line.strip().startswith(f"{key} ="):
            lines[index] = f"{key}={value}" if value else f"{key}="
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}" if value else f"{key}=")
    _ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value


@router.get("")
def list_settings(db: Session = Depends(get_db)) -> dict:
    """Return settings without exposing secrets."""
    rows = db.query(AppSetting).all()
    stored = {r.key: r.value for r in rows if r.key.lower() not in SECRET_KEYS}
    merged = {**DEFAULT_SETTINGS, **stored}
    return {
        "settings": [{"key": k, "value": v} for k, v in sorted(merged.items())],
        "defaults": DEFAULT_SETTINGS,
        "openai_configured": bool(settings.openai_api_key),
    }


@router.put("/{key}")
def update_setting(key: str, body: SettingIn, db: Session = Depends(get_db)) -> dict:
    """Update a single setting by key.

    For ``openai_api_key`` the value is also written to ``backend/.env`` and
    set in the current process so the LLM service can use it immediately.
    """
    if key != body.key:
        raise HTTPException(status_code=400, detail="Key in path and body must match.")
    if key.lower() in SECRET_KEYS:
        _write_env_key("OPENAI_API_KEY", body.value.strip())
        settings.openai_api_key = body.value.strip()
        return {"key": key, "value": "", "configured": bool(settings.openai_api_key)}
    row = set_setting(db, body.key, body.value)
    return row.to_dict()


@router.post("")
def update_bulk(body: SettingsBulkIn, db: Session = Depends(get_db)) -> dict:
    """Update multiple settings at once."""
    updated = 0
    for item in body.settings:
        if item.key.lower() in SECRET_KEYS:
            continue
        set_setting(db, item.key, item.value)
        updated += 1
    return {"updated": updated}


@router.post("/reset")
def reset_settings(db: Session = Depends(get_db)) -> dict:
    """Reset all settings to defaults."""
    db.query(AppSetting).delete()
    db.commit()
    _write_env_key("OPENAI_API_KEY", "")
    settings.openai_api_key = ""
    return {"reset": True, "defaults": DEFAULT_SETTINGS}


@router.get("/{key}")
def get_one(key: str, db: Session = Depends(get_db)) -> dict:
    """Get a single setting by key."""
    if key.lower() in SECRET_KEYS:
        return {"key": key, "configured": bool(settings.openai_api_key)}
    value = get_setting(db, key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found.")
    return {"key": key, "value": value}
