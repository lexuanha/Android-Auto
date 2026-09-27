import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .models import Asset, PriceQuote

SCHEMA_VERSION = 1


def default_database_path() -> Path:
    configured_path = os.environ.get("MARKET_PRICE_DB_PATH")
    if configured_path:
        return Path(configured_path).expanduser()
    return Path.home() / ".local" / "share" / "android-auto-market-prices" / "prices.sqlite3"


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class PriceStore:
    def __init__(self, database_path: Path | str | None = None) -> None:
        self.database_path = Path(database_path) if database_path is not None else default_database_path()
        self.database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.database_path.parent.chmod(0o700)
        except OSError:
            pass
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if version > SCHEMA_VERSION:
                    raise RuntimeError("Database schema is newer than this application")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS price_samples (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        asset_id TEXT NOT NULL,
                        asset_name TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        price TEXT NOT NULL,
                        quote_currency TEXT NOT NULL,
                        unit TEXT NOT NULL,
                        fetched_at TEXT NOT NULL,
                        source_updated_at TEXT
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_price_samples_asset_time "
                    "ON price_samples(asset_id, fetched_at DESC, id DESC)"
                )
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        try:
            self.database_path.chmod(0o600)
        except OSError:
            pass

    def insert(self, quote: PriceQuote) -> None:
        asset = quote.asset
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO price_samples (
                        asset_id, asset_name, provider, symbol, price,
                        quote_currency, unit, fetched_at, source_updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        asset.asset_id,
                        asset.name,
                        asset.provider,
                        asset.symbol,
                        str(quote.price),
                        asset.quote_currency,
                        asset.unit,
                        _format_datetime(quote.fetched_at),
                        _format_datetime(quote.source_updated_at),
                    ),
                )

    def latest(self, asset_id: str) -> PriceQuote | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM price_samples WHERE asset_id = ? "
                "ORDER BY fetched_at DESC, id DESC LIMIT 1",
                (asset_id,),
            ).fetchone()
        if row is None:
            return None
        asset = Asset(
            asset_id=row["asset_id"],
            name=row["asset_name"],
            provider=row["provider"],
            symbol=row["symbol"],
            quote_currency=row["quote_currency"],
            unit=row["unit"],
        )
        return PriceQuote(
            asset=asset,
            price=Decimal(row["price"]),
            fetched_at=_parse_datetime(row["fetched_at"]),
            source_updated_at=_parse_datetime(row["source_updated_at"]),
        )