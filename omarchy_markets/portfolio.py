from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from . import config, quotes


def secret_files() -> tuple[Path, Path]:
    folder = config.paths()["secrets"]
    return folder / "api_key", folder / "api_secret"


def available() -> bool:
    key, secret = secret_files()
    return key.is_file() and secret.is_file() and key.stat().st_size > 0 and secret.stat().st_size > 0


def _prepare_env() -> None:
    key, secret = secret_files()
    os.environ.setdefault("COINBASE_API_KEY_FILE", str(key))
    os.environ.setdefault("COINBASE_API_SECRET_FILE", str(secret))
    os.environ.setdefault("COINBASE_TICKER_CACHE", str(config.paths()["cache"] / "equity_tickers.json"))


def snapshot() -> dict:
    if not available():
        raise RuntimeError("Add a view-only Coinbase CDP key to ~/.config/coinbase-mcp/")
    _prepare_env()
    from coinbase_mcp.api import CoinbaseAPI
    from coinbase_mcp.config import Settings
    from coinbase_mcp.portfolio import PortfolioService

    settings = Settings.from_env()
    return PortfolioService(CoinbaseAPI(settings), settings).snapshot()


def _day_file() -> Path:
    return config.paths()["state"] / "portfolio-day.json"


def portfolio_quote() -> quotes.Quote:
    try:
        payload = snapshot()
    except Exception as error:
        return quotes.Quote(symbol="PORTFOLIO", kind="portfolio", price=0, change_pct=0, error=str(error), label="Portfolio")
    totals = payload.get("totals") or {}
    total = float(str(totals.get("total_balance") or "0"))
    today = datetime.now(UTC).date().isoformat()
    state_path = _day_file()
    state = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except ValueError:
            state = {}
    if state.get("day") != today:
        state = {"day": today, "open_total": total}
        config.paths()["state"].mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state))
    open_total = float(state.get("open_total") or total)
    change = ((total / open_total) - 1) * 100 if open_total else 0.0
    positions = payload.get("positions") or []
    return quotes.Quote(
        symbol="PORTFOLIO",
        kind="portfolio",
        price=total,
        change_pct=change,
        label="Portfolio",
        extra={
            "crypto": totals.get("total_crypto_balance"),
            "stocks": totals.get("total_equities_balance"),
            "cash": totals.get("total_cash_equivalent_balance"),
            "positions": positions[:12],
        },
    )
