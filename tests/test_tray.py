import unittest

from omarchy_markets import quotes
from omarchy_markets.tray import ordered_quotes, price_menu_options, watched_symbols


class TrayListTests(unittest.TestCase):
    def test_watched_symbols_include_portfolio_when_quoted(self):
        cfg = {"crypto": ["BTC-USD"], "stocks": ["AAPL"]}
        self.assertEqual(watched_symbols(cfg), ["BTC-USD", "AAPL"])
        self.assertEqual(
            watched_symbols(cfg, {"PORTFOLIO": object()}),
            ["BTC-USD", "AAPL", "PORTFOLIO"],
        )

    def test_price_menu_options_keep_symbol_as_key(self):
        items = ordered_quotes(
            {
                "BTC-USD": quotes.Quote("BTC-USD", "crypto", 77340, 2.8, label="BTC"),
                "AAPL": quotes.Quote("AAPL", "stock", 201.5, 0.4, label="AAPL"),
            },
            ["BTC-USD", "AAPL"],
        )
        options = price_menu_options(items, selected="BTC-USD")
        self.assertEqual(len(options), 2)
        self.assertTrue(options[0].startswith("●\t"))
        self.assertTrue(options[1].startswith("○\t"))
        self.assertTrue(options[0].endswith("\tBTC-USD"))
        self.assertTrue(options[1].endswith("\tAAPL"))
