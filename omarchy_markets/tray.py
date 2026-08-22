from __future__ import annotations

import os
import threading
from pathlib import Path

from . import alerts, config, portfolio, quotes


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

    def _rebuild_menu(self) -> None:
        Gtk = self.Gtk
        menu = Gtk.Menu()
        cfg = config.load()
        selected = str(cfg.get("tray_symbol") or "").upper()
        groups = (
            ("Crypto", cfg["crypto"]),
            ("Stocks", cfg["stocks"]),
            ("Portfolio", ["PORTFOLIO"] if "PORTFOLIO" in self.quotes else []),
        )
        for title, symbols in groups:
            if not symbols:
                continue
            header = Gtk.MenuItem(label=title)
            header.set_sensitive(False)
            menu.append(header)
            for symbol in symbols:
                quote = self.quotes.get(symbol)
                mark = "● " if symbol == selected else "    "
                label = quote.tray_text if quote else symbol
                if quote and alerts.is_massive(quote, cfg):
                    label = f"! {label}"
                _item(menu, mark + label, lambda s=symbol: self._set_tray(s))
            menu.append(Gtk.SeparatorMenuItem())
        _item(menu, "Refresh now", self.refresh)
        _item(menu, "Settings…", self._settings)
        menu.show_all()
        self.indicator.set_menu(menu)

    def _settings(self) -> None:
        from . import settings

        settings.show()


def run() -> None:
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import Gtk

    MarketsTray()
    Gtk.main()


if __name__ == "__main__":
    run()
