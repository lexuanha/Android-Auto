import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from market_price_bot.models import ASSETS, PriceQuote
from market_price_bot.price_store import PriceStore


class PriceStoreTests(unittest.TestCase):
    def test_insert_latest_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.sqlite3"
            store = PriceStore(path)
            first = PriceQuote(ASSETS["bitcoin"], Decimal("60000"), datetime(2026, 9, 27, 12, tzinfo=timezone.utc))
            latest = PriceQuote(ASSETS["bitcoin"], Decimal("60123.45"), datetime(2026, 9, 27, 12, 5, tzinfo=timezone.utc))
            store.insert(first)
            store.insert(latest)

            reopened = PriceStore(path)
            found = reopened.latest("bitcoin")
            self.assertIsNotNone(found)
            self.assertEqual(found.price, Decimal("60123.45"))
            self.assertEqual(found.fetched_at, latest.fetched_at)
            self.assertEqual(found.asset.unit, "BTC")

    def test_latest_is_none_when_asset_has_no_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PriceStore(Path(directory) / "history.sqlite3")
            self.assertIsNone(store.latest("gold"))


if __name__ == "__main__":
    unittest.main()