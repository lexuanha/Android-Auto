import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock

from market_price_bot.models import ASSETS, PriceQuote
from market_price_bot.telegram_commands import handle_message


def message(text, sender_id=12345, chat_id=12345):
    return {"text": text, "from": {"id": sender_id}, "chat": {"id": chat_id}}


class TelegramCommandTests(unittest.TestCase):
    def setUp(self):
        self.store = Mock()
        self.now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)

    def test_price_command_uses_latest_value_and_accepts_bot_suffix(self):
        self.store.latest.return_value = PriceQuote(
            ASSETS["gold"], Decimal("2350.50"), self.now - timedelta(minutes=2)
        )
        response = handle_message(message("/gold-price@my_test_bot"), self.store, "12345", self.now)
        self.assertIn("2,350.5 USD / troy ounce", response.text)
        self.assertIn("2026-09-27 11:58:00 UTC", response.text)
        self.assertFalse(response.should_stop)

    def test_missing_and_stale_data(self):
        self.store.latest.return_value = None
        missing = handle_message(message("/bitcoin-price"), self.store, "12345", self.now)
        self.assertIn("Chưa có dữ liệu", missing.text)

        self.store.latest.return_value = PriceQuote(
            ASSETS["bitcoin"], Decimal("65000"), self.now - timedelta(minutes=11)
        )
        stale = handle_message(message("/bitcoin-price"), self.store, "12345", self.now)
        self.assertIn("DỮ LIỆU CŨ", stale.text)

    def test_unauthorized_sender_cannot_query_or_stop(self):
        query = handle_message(message("/gold-price", sender_id=999), self.store, "12345", self.now)
        stop = handle_message(message("/stop", chat_id=999), self.store, "12345", self.now)
        self.assertIsNone(query.text)
        self.assertFalse(stop.should_stop)
        self.store.latest.assert_not_called()

    def test_stop_requires_authorized_private_chat(self):
        response = handle_message(message("/stop@my_test_bot"), self.store, "12345", self.now)
        self.assertTrue(response.should_stop)
        self.assertIn("dừng", response.text)


if __name__ == "__main__":
    unittest.main()