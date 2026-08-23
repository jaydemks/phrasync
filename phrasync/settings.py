from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import WORKSPACE

SETTINGS_PATH = WORKSPACE / "settings.json"
_STARTUP_HF_TOKEN = os.environ.get("HF_TOKEN")


def _read(path: Path = SETTINGS_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _write(payload: dict[str, Any], path: Path = SETTINGS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    temporary.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _masked(token: str) -> str:
    if len(token) <= 8:
        return "••••••••"
    prefix = "hf_" if token.startswith("hf_") else ""
    return f"{prefix}••••••••{token[-4:]}"


def saved_hf_token(path: Path = SETTINGS_PATH) -> str | None:
    token = _read(path).get("huggingFaceToken")
    return token if isinstance(token, str) and token else None


def apply_saved_settings(path: Path = SETTINGS_PATH) -> None:
    token = saved_hf_token(path)
    if token and not os.environ.get("HF_TOKEN"):
        os.environ["HF_TOKEN"] = token


def hf_token_status(path: Path = SETTINGS_PATH) -> dict[str, Any]:
    saved = saved_hf_token(path)
    active = os.environ.get("HF_TOKEN")
    if not active:
        return {"configured": False, "masked": None, "source": None, "canRemove": bool(saved)}
    source = "saved" if saved == active else "environment"
    return {
        "configured": True,
        "masked": _masked(active),
        "source": source,
        "canRemove": bool(saved),
    }


def save_hf_token(token: str, path: Path = SETTINGS_PATH) -> dict[str, Any]:
    token = token.strip()
    if not token.startswith("hf_") or len(token) < 12 or len(token) > 512 or any(char.isspace() for char in token):
        raise ValueError("Enter a valid Hugging Face token without spaces")
    payload = _read(path)
    payload["huggingFaceToken"] = token
    _write(payload, path)
    os.environ["HF_TOKEN"] = token
    return hf_token_status(path)


def remove_hf_token(path: Path = SETTINGS_PATH) -> dict[str, Any]:
    payload = _read(path)
    saved = payload.pop("huggingFaceToken", None)
    if payload:
        _write(payload, path)
    else:
        path.unlink(missing_ok=True)
    if saved and os.environ.get("HF_TOKEN") == saved:
        if _STARTUP_HF_TOKEN:
            os.environ["HF_TOKEN"] = _STARTUP_HF_TOKEN
        else:
            os.environ.pop("HF_TOKEN", None)
    return hf_token_status(path)
