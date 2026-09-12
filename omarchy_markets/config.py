from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

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
    
    if tomllib is None:
        raise ImportError("tomli package required for Python <3.11. Install with: pip install tomli")
    
    parsed = tomllib.loads(file.read_text())
    for key, value in parsed.items():
        if key not in DEFAULTS:
            continue
        if key in ("crypto", "stocks"):
            if isinstance(value, str):
                value = [value] if value else []
            value = [str(item).strip().upper() for item in value if str(item).strip()]
        cfg[key] = value
    return cfg


def dump(cfg: dict) -> str:
    def _format_value(value):
        if isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, str):
            return repr(value)
        elif isinstance(value, list):
            return "[" + ", ".join(repr(item) for item in value) + "]"
        else:
            return repr(value)
    
    rows = [
        "# Omarchy Markets — thresholds are absolute 24h percent moves.",
        *[f"{key} = {_format_value(value)}" for key, value in cfg.items()],
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
