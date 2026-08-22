# Omarchy Markets

System tray for **BTC**, **stocks**, and **Coinbase portfolio** balance. Hover or open the menu to switch what you are watching. Settings control which symbols you track and how large a one-day move has to be before you get a desktop notification.

Prices come from Coinbase's public market API (crypto) and Yahoo Finance (stocks). Portfolio totals use your local [coinbase-portfolio-mcp](https://github.com/markoalleno/coinbase-portfolio-mcp) credentials.

## Install

```bash
cd ~/Projects/omarchy-markets
./install.sh
```

Put a view-only Coinbase CDP key in `~/.config/coinbase-mcp/`:

```text
~/.config/coinbase-mcp/api_key
~/.config/coinbase-mcp/api_secret
```

Crypto and stock quotes work without those files. Portfolio does not.

## Use

| | |
|---|---|
| **Tray** | Label shows the selected quote. Click the menu to pick BTC, a stock, or portfolio. |
| **Settings** | Tray → Settings, or `omarchy-markets settings` |
| **Alerts** | Notify when a watched symbol's 24h move (or portfolio's day change) exceeds the threshold |

```bash
omarchy-markets status
omarchy-markets settings
omarchy-markets tray
```

Config: `~/.config/omarchy-markets/config.toml`
