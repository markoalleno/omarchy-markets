from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import alerts, config, portfolio, quotes


def ensure_gi() -> None:
    try:
        import gi  # noqa: F401
        return
    except ImportError:
        pass
    system = "/usr/bin/python3"
    if Path(system).exists() and Path(sys.executable).resolve() != Path(system).resolve():
        env = os.environ.copy()
        site = Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
        env["PYTHONPATH"] = str(site) + os.pathsep + env.get("PYTHONPATH", "")
        os.execvpe(system, [system, "-m", "omarchy_markets", *sys.argv[1:]], env)
    raise RuntimeError("PyGObject is required for the tray. Install python-gobject.")


def cmd_status(_args: argparse.Namespace) -> None:
    cfg = config.load()
    rows = []
    for symbol in [*cfg["crypto"], *cfg["stocks"]]:
        rows.append(quotes.quote(symbol))
    if portfolio.available():
        rows.append(portfolio.portfolio_quote())
    for row in rows:
        flag = "!" if alerts.is_massive(row, cfg) else " "
        print(f"{flag} {row.tray_text}" + (f"  ({row.error})" if row.error else ""))


def cmd_tray(_args: argparse.Namespace) -> None:
    ensure_gi()
    from . import tray

    tray.run()


def cmd_settings(_args: argparse.Namespace) -> None:
    ensure_gi()
    from . import settings

    settings.show()


def cmd_install(_args: argparse.Namespace) -> None:
    file = config.ensure()
    config.paths()["secrets"].mkdir(parents=True, exist_ok=True)
    user_dir = Path.home() / ".config/systemd/user"
    user_dir.mkdir(parents=True, exist_ok=True)
    executable = shutil.which("omarchy-markets") or str(Path(sys.argv[0]).resolve())
    service = user_dir / "omarchy-markets.service"
    service.write_text("\n".join([
        "[Unit]",
        "Description=Omarchy Markets tray",
        "After=graphical-session.target",
        "[Service]",
        f"ExecStart={executable} tray",
        "Restart=on-failure",
        "RestartSec=3",
        "Environment=COINBASE_API_KEY_FILE=%h/.config/coinbase-mcp/api_key",
        "Environment=COINBASE_API_SECRET_FILE=%h/.config/coinbase-mcp/api_secret",
        "Environment=COINBASE_TICKER_CACHE=%h/.cache/coinbase-mcp/equity_tickers.json",
        "[Install]",
        "WantedBy=default.target",
        "",
    ]))
    if shutil.which("systemctl"):
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", "--now", service.name], check=False)
    print(f"Installed. Settings: {file}")
    print("Drop a view-only Coinbase CDP key in ~/.config/coinbase-mcp/ to show portfolio.")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="omarchy-markets", description="Coinbase and stock quotes in the Omarchy tray")
    commands = root.add_subparsers(dest="command", required=True)
    for name, function, help_text in (
        ("status", cmd_status, "print watched quotes"),
        ("tray", cmd_tray, "run the tray icon"),
        ("settings", cmd_settings, "open settings"),
        ("install", cmd_install, "enable the user service"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.set_defaults(func=function)
    return root


def main() -> None:
    os.environ.setdefault("COINBASE_API_KEY_FILE", str(config.paths()["secrets"] / "api_key"))
    os.environ.setdefault("COINBASE_API_SECRET_FILE", str(config.paths()["secrets"] / "api_secret"))
    os.environ.setdefault("COINBASE_TICKER_CACHE", str(Path.home() / ".cache/coinbase-mcp/equity_tickers.json"))
    args = parser().parse_args()
    try:
        args.func(args)
    except (RuntimeError, OSError) as error:
        print(f"omarchy-markets: {error}", file=sys.stderr)
        raise SystemExit(1)
