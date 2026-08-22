from __future__ import annotations

from pathlib import Path

from . import config

_window = None
_owns_loop = False


def show() -> None:
    global _window, _owns_loop
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    if _window is not None:
        _window.present()
        return
    _owns_loop = Gtk.main_level() == 0
    _window = SettingsWindow()
    _window.connect("destroy", _closed)
    _window.show_all()
    if _owns_loop:
        Gtk.main()


def _closed(*_args) -> None:
    global _window, _owns_loop
    from gi.repository import Gtk

    _window = None
    if _owns_loop and Gtk.main_level():
        Gtk.main_quit()
    _owns_loop = False


def _lines(text: str) -> list[str]:
    return [row.strip().upper() for row in text.splitlines() if row.strip()]


class SettingsWindow:
    def __init__(self) -> None:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk

        self.Gtk = Gtk
        self.cfg = config.load()
        self.window = Gtk.Window(title="Markets settings")
        self.window.set_default_size(520, 560)
        self.window.set_border_width(12)
        icon = Path(__file__).with_name("icons") / "markets.svg"
        if icon.exists():
            try:
                self.window.set_icon_from_file(str(icon))
            except Exception:
                pass

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.window.add(root)
        root.pack_start(Gtk.Label(label="Watchlists (one symbol per line)", xalign=0), False, False, 0)

        columns = Gtk.Box(spacing=10)
        self.crypto = self._text("\n".join(self.cfg["crypto"]))
        self.stocks = self._text("\n".join(self.cfg["stocks"]))
        columns.pack_start(self._framed("Crypto (BTC-USD)", self.crypto), True, True, 0)
        columns.pack_start(self._framed("Stocks (AAPL)", self.stocks), True, True, 0)
        root.pack_start(columns, True, True, 0)

        grid = Gtk.Grid(column_spacing=10, row_spacing=8)
        self.crypto_move = self._spin(0, 100, 0.5, float(self.cfg["crypto_move_percent"]))
        self.stock_move = self._spin(0, 100, 0.5, float(self.cfg["stock_move_percent"]))
        self.portfolio_move = self._spin(0, 100, 0.5, float(self.cfg["portfolio_move_percent"]))
        self.refresh = self._spin(5, 3600, 5, int(self.cfg["refresh_seconds"]))
        self.refresh.set_digits(0)
        self.notify = Gtk.CheckButton(label="Notify on massive day moves")
        self.notify.set_active(bool(self.cfg["notify_on_move"]))
        self.tray_symbol = Gtk.Entry()
        self.tray_symbol.set_text(str(self.cfg["tray_symbol"]))
        self.tray_symbol.set_placeholder_text("BTC-USD, AAPL, or PORTFOLIO")

        def row(index: int, title: str, widget) -> None:
            grid.attach(Gtk.Label(label=title, xalign=0), 0, index, 1, 1)
            grid.attach(widget, 1, index, 1, 1)

        row(0, "Crypto alert %", self.crypto_move)
        row(1, "Stock alert %", self.stock_move)
        row(2, "Portfolio alert %", self.portfolio_move)
        row(3, "Refresh seconds", self.refresh)
        row(4, "Tray symbol", self.tray_symbol)
        grid.attach(self.notify, 0, 5, 2, 1)
        root.pack_start(grid, False, False, 0)

        hint = Gtk.Label(
            label="Alerts fire at most once per symbol per day. Portfolio % is vs the first total seen today.",
            xalign=0,
        )
        hint.set_line_wrap(True)
        root.pack_start(hint, False, False, 0)

        buttons = Gtk.Box(spacing=8)
        save = Gtk.Button(label="Save")
        save.get_style_context().add_class("suggested-action")
        save.connect("clicked", lambda *_a: self._save())
        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda *_a: self.window.destroy())
        buttons.pack_end(close, False, False, 0)
        buttons.pack_end(save, False, False, 0)
        root.pack_start(buttons, False, False, 0)
        self.window.connect("key-press-event", self._on_key)
        self.status = Gtk.Label(xalign=0)
        root.pack_start(self.status, False, False, 0)

    def present(self) -> None:
        self.window.present()

    def show_all(self) -> None:
        self.window.show_all()

    def connect(self, signal, callback):
        return self.window.connect(signal, callback)

    def _text(self, value: str):
        view = self.Gtk.TextView()
        view.set_wrap_mode(self.Gtk.WrapMode.WORD_CHAR)
        view.get_buffer().set_text(value)
        view.set_hexpand(True)
        view.set_vexpand(True)
        return view

    def _framed(self, title: str, view):
        Gtk = self.Gtk
        frame = Gtk.Frame(label=title)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(view)
        scroll.set_min_content_height(180)
        frame.add(scroll)
        return frame

    def _spin(self, lo: float, hi: float, step: float, value: float):
        widget = self.Gtk.SpinButton.new_with_range(lo, hi, step)
        widget.set_digits(1)
        widget.set_value(value)
        return widget

    def _buffer_text(self, view) -> str:
        buf = view.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)

    def _save(self) -> None:
        tray = self.tray_symbol.get_text().strip().upper() or "BTC-USD"
        config.save({
            "crypto": _lines(self._buffer_text(self.crypto)),
            "stocks": _lines(self._buffer_text(self.stocks)),
            "crypto_move_percent": float(self.crypto_move.get_value()),
            "stock_move_percent": float(self.stock_move.get_value()),
            "portfolio_move_percent": float(self.portfolio_move.get_value()),
            "refresh_seconds": int(self.refresh.get_value()),
            "notify_on_move": self.notify.get_active(),
            "tray_symbol": tray,
        })
        self.status.set_text("Saved. The tray picks this up on the next refresh.")

    def _on_key(self, _widget, event) -> bool:
        from gi.repository import Gdk

        if event.keyval == Gdk.KEY_Escape:
            self.window.destroy()
            return True
        return False
