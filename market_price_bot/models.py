from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Asset:
    asset_id: str
    name: str
    provider: str
    symbol: str
    quote_currency: str
    unit: str


@dataclass(frozen=True)
class PriceQuote:
    asset: Asset
    price: Decimal
    fetched_at: datetime
    source_updated_at: datetime | None = None


ASSETS: dict[str, Asset] = {
    "gold": Asset(
        asset_id="gold",
        name="Gold spot",
        provider="gold_api",
        symbol="XAU",
        quote_currency="USD",
        unit="troy ounce",
    ),
    "bitcoin": Asset(
        asset_id="bitcoin",
        name="Bitcoin",
        provider="binance",
        symbol="BTCUSDT",
        quote_currency="USDT",
        unit="BTC",
    ),
}