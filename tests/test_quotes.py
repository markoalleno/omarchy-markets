import unittest
from unittest.mock import patch

from omarchy_markets import alerts, config, quotes


class QuoteTests(unittest.TestCase):
    def test_crypto_quote_parses_coinbase_payload(self):
        payload = {"product_id": "BTC-USD", "price": "100", "price_percentage_change_24h": "-9.5", "base_display_symbol": "BTC"}
        with patch("omarchy_markets.quotes.fetch_json", return_value=payload):
            quote = quotes.crypto_quote("btc-usd")
        self.assertEqual(quote.kind, "crypto")
        self.assertEqual(quote.price, 100)
        self.assertEqual(quote.change_pct, -9.5)
        self.assertIn("BTC", quote.tray_text)

    def test_stock_quote_uses_previous_close(self):
        payload = {"chart": {"result": [{"meta": {"regularMarketPrice": 110, "chartPreviousClose": 100, "symbol": "AAPL"}}]}}
        with patch("omarchy_markets.quotes.fetch_json", return_value=payload):
            quote = quotes.stock_quote("aapl")
        self.assertEqual(quote.kind, "stock")
        self.assertEqual(quote.price, 110)
        self.assertAlmostEqual(quote.change_pct, 10)

    def test_massive_move_uses_kind_threshold(self):
        cfg = {**config.DEFAULTS, "crypto_move_percent": 8, "stock_move_percent": 5}
        crypto = quotes.Quote("BTC-USD", "crypto", 1, 8.1)
        stock = quotes.Quote("AAPL", "stock", 1, 4.9)
        self.assertTrue(alerts.is_massive(crypto, cfg))
        self.assertFalse(alerts.is_massive(stock, cfg))


if __name__ == "__main__":
    unittest.main()
