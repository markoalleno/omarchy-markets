from __future__ import annotations

import ast
import json
import os
from pathlib import Path

DEFAULTS = {
    "crypto": ["BTC-USD", "ETH-USD"],
    "stocks": ["AAPL"],
    "tray_symbol": "BTC-USD",
    "refresh_seconds": 30,
    "crypto_move_percent": 8.0,
    "stock_move_percent": 5.0,
    "portfolio_move_percent": 4.0,
    "notify_on_move": True,
}


def paths() -> dict[str, Path]:
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "omarchy-markets"
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "omarchy-markets"
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "omarchy-markets"
    secrets = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "coinbase-mcp"
    return {"config": config, "state": state, "cache": cache, "secrets": secrets}


def load() -> dict:
    cfg = {key: (value.copy() if isinstance(value, list) else value) for key, value in DEFAULTS.items()}
    file = paths()["config"] / "config.toml"
    if not file.exists():
        return cfg
    for raw in file.read_text().splitlines():
        row = raw.split("#", 1)[0].strip()
        if not row or "=" not in row:
            continue
        key, raw_value = (part.strip() for part in row.split("=", 1))
        if key not in DEFAULTS:
            continue
        if raw_value.lower() in ("true", "false"):
            value = raw_value.lower() == "true"
        else:
            value = ast.literal_eval(raw_value)
        if key in ("crypto", "stocks"):
            if isinstance(value, str):
                value = [value] if value else []
            value = [str(item).strip().upper() for item in value if str(item).strip()]
        cfg[key] = value
    return cfg


def dump(cfg: dict) -> str:
    rows = [
        "# Omarchy Markets — thresholds are absolute 24h percent moves.",
        *[f"{key} = {str(value).lower() if isinstance(value, bool) else repr(value)}" for key, value in cfg.items()],
        "",
    ]
    return "\n".join(rows)


def ensure() -> Path:
    p = paths()
    for directory in p.values():
        directory.mkdir(parents=True, exist_ok=True)
    file = p["config"] / "config.toml"
    if not file.exists():
        file.write_text(dump(DEFAULTS))
    return file


def save(updates: dict) -> Path:
    cfg = load()
    cfg.update(updates)
    file = ensure()
    file.write_text(dump(cfg))
    return file


def threshold_for(kind: str, cfg: dict | None = None) -> float:
    cfg = cfg or load()
    return float(cfg.get(f"{kind}_move_percent") or cfg["crypto_move_percent"])


def load_state_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except ValueError:
        return default


def save_state_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
