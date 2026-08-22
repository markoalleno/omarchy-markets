from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from . import config
from .quotes import Quote


def _file() -> Path:
    return config.paths()["state"] / "alerts.json"


def _load() -> dict:
    file = _file()
    if not file.exists():
        return {"day": "", "sent": {}}
    try:
        return json.loads(file.read_text())
    except ValueError:
        return {"day": "", "sent": {}}


def _save(payload: dict) -> None:
    config.paths()["state"].mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps(payload))


def threshold(quote: Quote, cfg: dict | None = None) -> float:
    cfg = cfg or config.load()
    return config.threshold_for(quote.kind, cfg)


def is_massive(quote: Quote, cfg: dict | None = None) -> bool:
    if quote.error:
        return False
    return abs(quote.change_pct) >= threshold(quote, cfg)


def notify(title: str, body: str) -> None:
    if shutil.which("omarchy-notification-send"):
        subprocess.Popen(["omarchy-notification-send", "-u", "critical", title, body], start_new_session=True)
        return
    if shutil.which("notify-send"):
        subprocess.Popen(["notify-send", "-u", "critical", title, body], start_new_session=True)


def maybe_alert(quote: Quote, cfg: dict | None = None) -> bool:
    cfg = cfg or config.load()
    if not cfg.get("notify_on_move", True) or not is_massive(quote, cfg):
        return False
    today = datetime.now(UTC).date().isoformat()
    state = _load()
    if state.get("day") != today:
        state = {"day": today, "sent": {}}
    if state["sent"].get(quote.symbol):
        return False
    direction = "up" if quote.change_pct >= 0 else "down"
    notify(
        f"{quote.label or quote.symbol} {direction} {quote.signed_change}",
        f"{quote.tray_text}  (alert ≥ {threshold(quote, cfg):g}%)",
    )
    state["sent"][quote.symbol] = True
    _save(state)
    return True
