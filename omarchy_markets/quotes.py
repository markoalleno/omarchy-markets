from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

UA = "omarchy-markets/0.1"


@dataclass
class Quote:
    symbol: str
    kind: str
    price: float
    change_pct: float
    label: str = ""
    error: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def signed_change(self) -> str:
        sign = "+" if self.change_pct >= 0 else ""
        return f"{sign}{self.change_pct:.2f}%"

    @property
    def tray_text(self) -> str:
        if self.error:
            return f"{self.symbol} —"
        name = self.label or self.symbol.split("-")[0]
        if self.kind == "portfolio":
            return f"PF ${self.price:,.0f} {self.signed_change}"
        if self.price >= 1000:
            price = f"${self.price:,.0f}"
        elif self.price >= 1:
            price = f"${self.price:,.2f}"
        else:
            price = f"${self.price:.4f}"
        return f"{name} {price} {self.signed_change}"


def classify(symbol: str) -> str:
    token = symbol.strip().upper()
    if token in {"PORTFOLIO", "PF", "BAL"}:
        return "portfolio"
    if "-" in token:
        return "crypto"
    return "stock"


def fetch_json(url: str, timeout: int = 10) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def crypto_quote(product_id: str) -> Quote:
    product_id = product_id.strip().upper()
    try:
        payload = fetch_json(f"https://api.coinbase.com/api/v3/brokerage/market/products/{product_id}")
        product = payload.get("product") or payload
        price = float(product.get("price") or 0)
        change = float(str(product.get("price_percentage_change_24h") or "0").replace("%", ""))
        return Quote(
            symbol=product.get("product_id") or product_id,
            kind="crypto",
            price=price,
            change_pct=change,
            label=(product.get("base_display_symbol") or product_id.split("-")[0]),
            extra={"volume_24h": product.get("volume_24h")},
        )
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as error:
        return Quote(symbol=product_id, kind="crypto", price=0, change_pct=0, error=str(error) or "quote failed")


def stock_quote(symbol: str) -> Quote:
    symbol = symbol.strip().upper()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
    try:
        payload = fetch_json(url)
        result = (payload.get("chart") or {}).get("result") or []
        if not result:
            raise ValueError("no chart data")
        meta = result[0].get("meta") or {}
        price = float(meta.get("regularMarketPrice") or 0)
        previous = float(meta.get("chartPreviousClose") or meta.get("previousClose") or 0)
        change = ((price / previous) - 1) * 100 if previous else 0.0
        return Quote(symbol=symbol, kind="stock", price=price, change_pct=change, label=symbol)
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError, IndexError) as error:
        return Quote(symbol=symbol, kind="stock", price=0, change_pct=0, error=str(error) or "quote failed")


def quote(symbol: str) -> Quote:
    kind = classify(symbol)
    if kind == "crypto":
        return crypto_quote(symbol)
    if kind == "stock":
        return stock_quote(symbol)
    return Quote(symbol=symbol, kind=kind, price=0, change_pct=0, error="unknown symbol")
