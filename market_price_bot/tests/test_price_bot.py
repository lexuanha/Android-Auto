import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from market_price_bot.models import ASSETS, PriceQuote
from market_price_bot.price_bot import collect_once, load_telegram_config, run_bot
from market_price_bot.price_sources import PriceSourceError


class PriceBotTests(unittest.TestCase):
    def test_complete_environment_config_does_not_require_json_file(self):
        with patch("market_price_bot.price_bot.DEFAULT_CONFIG_PATH", Path("missing-config.json")):
            with patch.dict("os.environ", {"TG_BOT_TOKEN": "test-token", "TG_CHAT_ID": "12345"}, clear=True):
                self.assertEqual(load_telegram_config(), ("test-token", "12345"))

    def test_one_provider_failure_does_not_block_other_asset(self):
        store = Mock()
        quote = PriceQuote(ASSETS["bitcoin"], Decimal("65000"), datetime.now(timezone.utc))
        with patch("market_price_bot.price_bot.PROVIDERS", {
            "gold_api": Mock(side_effect=PriceSourceError("offline")),
            "binance": Mock(return_value=quote),
        }):
            self.assertEqual(collect_once(store), 1)
        store.insert.assert_called_once_with(quote)

    def test_authorized_stop_update_exits_polling_loop(self):
        stop_update = {
            "update_id": 42,
            "message": {
                "text": "/stop",
                "from": {"id": 12345},
                "chat": {"id": 12345},
            },
        }
        with patch("market_price_bot.price_bot.collect_once"):
            with patch("market_price_bot.price_bot.get_updates", side_effect=[[], [stop_update]]):
                with patch("market_price_bot.price_bot.send_message") as send_message:
                    run_bot("test-token", "12345", store=Mock())
        send_message.assert_called_once()
        self.assertIn("dừng", send_message.call_args.args[2])


if __name__ == "__main__":
    unittest.main()