import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

from market_price_bot.models import ASSETS
from market_price_bot.price_sources import (
    PriceSourceError,
    _get_json,
    parse_binance_response,
    parse_gold_response,
)


class PriceSourceTests(unittest.TestCase):
    def test_parse_gold_price_and_source_timestamp(self):
        quote = parse_gold_response(
            {"symbol": "XAU", "price": "2350.125", "updatedAt": "2026-09-27T12:00:00Z"},
            ASSETS["gold"],
        )
        self.assertEqual(quote.price, Decimal("2350.125"))
        self.assertEqual(quote.source_updated_at, datetime(2026, 9, 27, 12, tzinfo=timezone.utc))

    def test_parse_binance_price(self):
        quote = parse_binance_response(
            {"symbol": "BTCUSDT", "price": "65000.50"},
            ASSETS["bitcoin"],
        )
        self.assertEqual(quote.price, Decimal("65000.50"))
        self.assertEqual(quote.asset.quote_currency, "USDT")

    def test_rejects_bad_prices_and_wrong_symbol(self):
        for value in ("NaN", "Infinity", "0", "-4", "not a price"):
            with self.subTest(value=value), self.assertRaises(PriceSourceError):
                parse_gold_response({"price": value}, ASSETS["gold"])
        with self.assertRaises(PriceSourceError):
            parse_binance_response({"symbol": "ETHUSDT", "price": "1"}, ASSETS["bitcoin"])

    def test_http_json_helper_uses_timeout(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"price": 42}'
        with patch("market_price_bot.price_sources.urlopen", return_value=response) as mocked_urlopen:
            self.assertEqual(_get_json("https://provider.invalid/test"), {"price": 42})
        self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], 15)


if __name__ == "__main__":
    unittest.main()