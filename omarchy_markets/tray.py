from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path

from . import alerts, config, portfolio, quotes


def watched_symbols(cfg: dict, quotes_by_symbol: dict | None = None) -> list[str]:
    symbols = [str(item).upper() for item in cfg.get("crypto") or []]
    symbols += [str(item).upper() for item in cfg.get("stocks") or []]
    if quotes_by_symbol is not None and "PORTFOLIO" in quotes_by_symbol and "PORTFOLIO" not in symbols:
        symbols.append("PORTFOLIO")
    return symbols


def ordered_quotes(quotes_by_symbol: dict[str, quotes.Quote], symbols: list[str]) -> list[quotes.Quote]:
    rows = []
    for symbol in symbols:
        quote = quotes_by_symbol.get(symbol)
        if quote is None:
            quote = quotes.Quote(symbol=symbol, kind=quotes.classify(symbol), price=0, change_pct=0, error="no quote")
        rows.append(quote)
    return rows


def price_menu_options(items: list[quotes.Quote], selected: str = "") -> list[str]:
    selected = selected.upper()
    options = []
    for quote, line in zip(items, quotes.aligned_rows(items)):
        glyph = "●" if quote.symbol.upper() == selected else "○"
        options.append(f"{glyph}\t{line}\t{quote.symbol}")
    return options


def pick_symbol(options: list[str]) -> str | None:
    if not options:
        return None
    binary = shutil.which("omarchy-menu-select")
    if not binary:
        return None
    result = subprocess.run(
        [binary, "Markets", *options, "--", "--width", "520"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    choice = result.stdout.strip()
    if "\t" in choice:
        return choice.split("\t")[-1]
    return choice or None


def notify_prices(lines: list[str]) -> None:
    body = "\n".join(lines) if lines else "No quotes yet."
    if shutil.which("omarchy-notification-send"):
        subprocess.Popen(["omarchy-notification-send", "Markets", body], start_new_session=True)


def _icon() -> str:
    svg = Path(__file__).with_name("icons") / "markets.svg"
    return str(svg) if svg.exists() else "utilities-system-monitor"


def _item(menu, label: str, callback=None) -> None:
    from gi.repository import Gtk

    entry = Gtk.MenuItem(label=label)
    if callback:
        entry.connect("activate", lambda _item: callback())
    else:
        entry.set_sensitive(False)
    menu.append(entry)


class MarketsTray:
    def __init__(self) -> None:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3, GLib, Gtk

        self.Gtk = Gtk
        self.GLib = GLib
        self.quotes: dict[str, quotes.Quote] = {}
        self.busy = False
        self.next_refresh = 0.0
        config.ensure()
        config.paths()["state"].mkdir(parents=True, exist_ok=True)
        config.paths()["state"].joinpath("tray.pid").write_text(str(os.getpid()))

        self.indicator = AyatanaAppIndicator3.Indicator.new(
            "omarchy-markets",
            "utilities-system-monitor",
            AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        icon = _icon()
        if icon.endswith(".svg"):
            self.indicator.set_icon_full(icon, "Markets")
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title("Markets")
        self.indicator.set_menu(Gtk.Menu())
        # Omarchy left-clicks call SNI Activate. Ayatana only handles that if a
        # handler is connected; otherwise the click is a no-op.
        self.indicator.connect("activate", lambda *_args: self._show_prices())
        self.refresh()
        GLib.timeout_add_seconds(1, self._tick)

    def _tick(self) -> bool:
        import time

        now = time.monotonic()
        if not self.busy and now >= self.next_refresh:
            self.refresh()
        return True

    def _interval(self) -> int:
        return max(5, int(config.load()["refresh_seconds"]))

    def refresh(self) -> None:
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self) -> None:
        cfg = config.load()
        collected: dict[str, quotes.Quote] = {}
        for symbol in cfg["crypto"]:
            collected[symbol] = quotes.crypto_quote(symbol)
        for symbol in cfg["stocks"]:
            collected[symbol] = quotes.stock_quote(symbol)
        if portfolio.available():
            collected["PORTFOLIO"] = portfolio.portfolio_quote()
        for quote in collected.values():
            alerts.maybe_alert(quote, cfg)
        import time

        self.next_refresh = time.monotonic() + self._interval()
        self.GLib.idle_add(self._apply, collected)

    def _apply(self, collected: dict[str, quotes.Quote]) -> bool:
        self.quotes = collected
        self.busy = False
        self._rebuild_menu()
        self._update_label()
        return False

    def _update_label(self) -> None:
        cfg = config.load()
        symbol = str(cfg.get("tray_symbol") or "BTC-USD").upper()
        quote = self.quotes.get(symbol) or next(iter(self.quotes.values()), None)
        text = quote.tray_text if quote else "Markets"
        self.indicator.set_label(text, "BTC 000000 +00.00%")
        self.indicator.set_title(text)

    def _set_tray(self, symbol: str) -> None:
        config.save({"tray_symbol": symbol})
        self._update_label()
        self._rebuild_menu()

    def _quote_rows(self) -> list[quotes.Quote]:
        cfg = config.load()
        return ordered_quotes(self.quotes, watched_symbols(cfg, self.quotes))

    def _show_prices(self) -> None:
        self.GLib.idle_add(self._pick_from_prices)

    def _pick_from_prices(self) -> bool:
        rows = self._quote_rows()
        if not rows or all(item.error for item in rows):
            self.refresh()
            notify_prices(["Fetching quotes…"])
            return False
        selected = str(config.load().get("tray_symbol") or "").upper()
        picked = pick_symbol(price_menu_options(rows, selected))
        if picked:
            self._set_tray(picked)
        elif shutil.which("omarchy-menu-select") is None:
            notify_prices(quotes.aligned_rows(rows))
        return False

    def _rebuild_menu(self) -> None:
        Gtk = self.Gtk
        menu = Gtk.Menu()
        _item(menu, "Settings…", self._settings)
        _item(menu, "Quit", self._quit)
        menu.show_all()
        self.indicator.set_menu(menu)

    def _settings(self) -> None:
        from . import settings

        settings.show()

    def _quit(self) -> None:
        self.Gtk.main_quit()


def run() -> None:
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import Gtk

    MarketsTray()
    Gtk.main()


if __name__ == "__main__":
    run()
