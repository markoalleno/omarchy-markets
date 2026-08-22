import os
import tempfile
import unittest
from unittest.mock import patch

from omarchy_markets import alerts
from omarchy_markets.quotes import Quote


class AlertTests(unittest.TestCase):
    def test_maybe_alert_once_per_day(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
            "XDG_CONFIG_HOME": folder + "/config",
            "XDG_CACHE_HOME": folder + "/cache",
            "XDG_STATE_HOME": folder + "/state",
        }), patch("omarchy_markets.alerts.notify") as notify:
            quote = Quote("BTC-USD", "crypto", 100, 12, label="BTC")
            cfg = {"notify_on_move": True, "crypto_move_percent": 8, "stock_move_percent": 5, "portfolio_move_percent": 4}
            self.assertTrue(alerts.maybe_alert(quote, cfg))
            self.assertFalse(alerts.maybe_alert(quote, cfg))
            notify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
