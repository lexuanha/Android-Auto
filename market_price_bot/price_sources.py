import json
import math
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import Asset, PriceQuote

REQUEST_TIMEOUT_SECONDS = 15


class PriceSourceError(RuntimeError):
    """A provider response could not be fetched or validated."""


def _parse_price(value: object) -> Decimal:
    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise PriceSourceError("Provider returned a non-numeric price") from None
    if not price.is_finite() or price <= 0:
        raise PriceSourceError("Provider returned a non-positive or non-finite price")
    return price


def _parse_source_time(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                return None
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        text = str(value).strip()
        if not text:
            return None
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (OverflowError, OSError, TypeError, ValueError):
        return None


def parse_gold_response(data: object, asset: Asset, fetched_at: datetime | None = None) -> PriceQuote:
    if not isinstance(data, dict) or "price" not in data:
        raise PriceSourceError("Gold API returned an unexpected response")
    timestamp = data.get("updatedAt", data.get("updated_at"))
    return PriceQuote(
        asset=asset,
        price=_parse_price(data["price"]),
        fetched_at=fetched_at or datetime.now(timezone.utc),
        source_updated_at=_parse_source_time(timestamp),
    )


def parse_binance_response(data: object, asset: Asset, fetched_at: datetime | None = None) -> PriceQuote:
    if not isinstance(data, dict) or data.get("symbol") != asset.symbol or "price" not in data:
        raise PriceSourceError("Binance returned an unexpected ticker response")
    return PriceQuote(
        asset=asset,
        price=_parse_price(data["price"]),
        fetched_at=fetched_at or datetime.now(timezone.utc),
    )


def _get_json(url: str) -> object:
    request = Request(url, headers={"User-Agent": "AndroidAutoMarketPriceBot/0.1"})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read())
    except HTTPError as error:
        raise PriceSourceError(f"Provider HTTP error {error.code}") from None
    except (URLError, TimeoutError, OSError):
        raise PriceSourceError("Provider network request failed") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PriceSourceError("Provider returned invalid JSON") from None


def fetch_gold(asset: Asset) -> PriceQuote:
    data = _get_json(f"https://api.gold-api.com/price/{asset.symbol}")
    return parse_gold_response(data, asset)


def fetch_binance(asset: Asset) -> PriceQuote:
    data = _get_json(f"https://api.binance.com/api/v3/ticker/price?symbol={asset.symbol}")
    return parse_binance_response(data, asset)


PROVIDERS = {
    "gold_api": fetch_gold,
    "binance": fetch_binance,
}