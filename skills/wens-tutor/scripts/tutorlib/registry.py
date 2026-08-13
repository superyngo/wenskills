# skills/wens-tutor/scripts/tutorlib/registry.py
"""Device-local registry: roots, default root, port, token (ADR 0003)."""

import json
import os
import secrets
from pathlib import Path

PATH = Path(os.environ.get("WENS_TUTOR_CONFIG", "~/.config/wens-tutor/roots.json")).expanduser()


def load() -> dict:
    if PATH.exists():
        return json.loads(PATH.read_text(encoding="utf-8"))
    return {"roots": [], "default": None, "port": 8765, "token": None}


def save(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_root(path) -> dict:
    data = load()
    p = str(Path(path).expanduser().resolve())
    if p not in data["roots"]:
        data["roots"].append(p)
    data["default"] = data["default"] or p
    data["token"] = data.get("token") or secrets.token_urlsafe(16)
    save(data)
    return data


def default_root():
    d = load().get("default")
    return Path(d) if d else None


def token():
    return load().get("token")
