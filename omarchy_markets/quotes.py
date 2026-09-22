from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

UA = "omarchy-markets/0.1.1"


@dataclass
class Quote:
    symbol: str
    kind: str
    price: float
    change_pct: float
    label: str = ""
    error: str = ""

    @property
    def signed_change(self) -> str:
        sign = "+" if self.change_pct >= 0 else ""
        return f"{sign}{self.change_pct:.2f}%"

    @property
    def display_name(self) -> str:
        if self.kind == "portfolio":
            return "PF"
        return self.label or self.symbol.split("-")[0]

    @property
    def price_text(self) -> str:
        if self.error:
            return "—"
        if self.kind == "portfolio" or self.price >= 1000:
            return f"${self.price:,.0f}"
        if self.price >= 1:
            return f"${self.price:,.2f}"
        return f"${self.price:.4f}"

    @property
    def change_text(self) -> str:
        return "—" if self.error else self.signed_change

    @property
    def tray_text(self) -> str:
        if self.error:
            return f"{self.display_name} —"
        return f"{self.display_name} {self.price_text} {self.signed_change}"


def aligned_rows(items: list[Quote]) -> list[str]:
    if not items:
        return []
    names = [item.display_name for item in items]
    amounts = ["—" if item.error else item.price_text.removeprefix("$") for item in items]
    changes = [item.change_text for item in items]
    name_width = max(len(name) for name in names)
    amount_width = max(len(amount) for amount in amounts)
    change_width = max(len(change) for change in changes)
    return [
        f"{name:<{name_width}}  ${amount:>{amount_width}}  {change:>{change_width}}"
        for name, amount, change in zip(names, amounts, changes)
    ]


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
