# Project Plan

## Goal

Run a lightweight price collector on Android in Termux. Persist a growing history of supported asset prices every five minutes and make selected latest values available through Telegram commands.

## Scope

- Collect immediately after startup, then every 300 seconds.
- Store every valid successful sample in SQLite without automatic retention deletion.
- Initially support global spot gold (`XAU`, USD/troy ounce) and BTC/USDT (USDT per BTC).
- Answer `/gold-price` and `/bitcoin-price` from the newest stored sample; label samples older than ten minutes as stale.
- Support `/stop`, require the configured private chat and sender IDs, and run one Telegram `getUpdates` consumer.
- Keep the implementation standard-library-only and leave `telegram_test.py` as the finite connectivity smoke test.

## Design

- `models.py`: asset registry and normalized quote data.
- `price_sources.py`: provider adapters and response validation.
- `price_store.py`: versioned SQLite schema and insert/latest operations.
- `telegram_commands.py`: allowlisted command mapping, authorization and reply formatting.
- `price_bot.py`: startup collection, periodic scheduler, Telegram polling and process lifecycle.
- `tests/`: offline unit tests using mocked HTTP, temporary databases and deterministic timestamps.

Adding an asset from an existing provider is a registry and command mapping change. A new provider requires its own adapter and tests. Storage is generic and does not need asset-specific schema changes.

## Implementation Phases

1. **Complete:** establish normalized asset/quote types, two provider adapters, and SQLite history.
2. **Complete:** add authenticated Telegram command routing and one polling/scheduling loop.
3. **Complete:** cover response parsing, invalid data, persistence, command behavior, staleness and provider failure isolation with 13 offline tests.
4. **In progress:** deploy to Termux and validate real API responses and Telegram behavior; still verify repeated collection, locked-screen operation, on-device persistence across restart, live `/stop`, and unauthorized-sender handling.

## Progress Log

- 2026-09-27: copied the package to `~/storage/downloads/market_price_bot` on the Samsung SM-J400F (Android 10, Termux). Started it from `~/storage/downloads` with `python -m market_price_bot`.
- Termux output confirmed successful initial SQLite inserts for XAU and Bitcoin and reported that the bot had started. The user confirmed receiving a price by Telegram message.
- Development-machine verification: all 13 `unittest` tests pass; Pylance reports no errors. SQLite close/reopen persistence is covered by the offline store test, but a stop/restart persistence check on the phone remains outstanding.

## Verification

1. From the repository root: `python -m unittest discover -s market_price_bot/tests -v`.
2. Check syntax/imports: `python -m compileall market_price_bot`.
3. On Termux, confirm one startup collection for XAU and BTC appears in the private database with correct units and timestamps.
4. Verify both price commands, no-data response, stale marker, unauthorized sender behavior and `/stop`.
5. Run for at least 15 minutes, including a screen-locked interval; verify periodic samples, command responsiveness, restart persistence and provider-failure isolation.
6. Keep tokens out of code, tests, logs and documentation.

## Decisions and Risks

- The query commands read stored values instead of making extra API requests.
- `/stop` ends the whole collector process. Ctrl+C remains available in the foreground Termux session.
- Only one active `getUpdates` consumer is supported for each bot token; do not run beside the PC bot.
- Gold-API XAU is international spot gold, not a Vietnamese SJC/retail quote. Binance BTC/USDT is a single venue's market price.
- Android background policies and connectivity can delay or miss a five-minute sample. No hard real-time or uptime guarantee is made.
- Full-history storage grows with time. Retention, export, notifications and more assets/providers remain future work.