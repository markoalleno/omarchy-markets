import os
import tempfile
import unittest
from unittest.mock import patch

from omarchy_markets import config


class ConfigTests(unittest.TestCase):
    def test_roundtrip_watchlists_and_thresholds(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
            "XDG_CONFIG_HOME": folder + "/config",
            "XDG_CACHE_HOME": folder + "/cache",
            "XDG_STATE_HOME": folder + "/state",
        }):
            config.ensure()
            config.save({
                "crypto": ["btc-usd"],
                "stocks": ["NVDA", "aapl"],
                "crypto_move_percent": 12.5,
                "notify_on_move": False,
            })
            loaded = config.load()
            self.assertEqual(loaded["crypto"], ["BTC-USD"])
            self.assertEqual(loaded["stocks"], ["NVDA", "AAPL"])
            self.assertEqual(loaded["crypto_move_percent"], 12.5)
            self.assertFalse(loaded["notify_on_move"])
            self.assertEqual(config.threshold_for("crypto", loaded), 12.5)


if __name__ == "__main__":
    unittest.main()
