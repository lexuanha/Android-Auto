# Android Market Price Bot

A small Python service for Termux that samples market prices every five minutes, stores successful samples in SQLite, and answers selected Telegram commands from the stored history. The project uses only the Python standard library and is isolated from the root-level Telegram connectivity test.

## Initial Assets

| Command | Asset | Source | Quote and unit |
| --- | --- | --- | --- |
| `/gold-price` | International spot gold (`XAU`) | Gold-API | USD per troy ounce |
| `/bitcoin-price` | Bitcoin (`BTCUSDT`) | Binance public ticker | USDT per BTC |

The gold quote is not a Vietnamese SJC or retail price. The Bitcoin quote is from Binance's BTC/USDT market, not a market-wide index. Price commands return the newest sample in the database, with its UTC collection time; samples older than ten minutes are marked stale.

## Current Status

The package has been copied to the test phone's Termux Downloads directory. On 2026-09-27, `python -m market_price_bot` was run from `~/storage/downloads`; the Termux output confirmed that an XAU sample and a Bitcoin sample were stored, and the bot started. The user also confirmed receiving a price through Telegram.

All 13 offline `unittest` tests pass on the development machine, including SQLite insert/latest-read/reopen behavior. The phone has not yet been observed through multiple five-minute cycles, a locked-screen interval, a stop/restart persistence check, or a live `/stop` and unauthorized-sender test.

## Requirements

- Termux and Python 3.10 or newer.
- The existing Telegram bot config at `~/.config/telegram/config.json`:

```json
{
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_PRIVATE_CHAT_ID"
}
```

Protect this file with `chmod 600 ~/.config/telegram/config.json`. The configured chat must be a private chat where the sender ID and chat ID match. Never commit the token or paste it into commands that may be logged.

Install Python in Termux if needed:

```sh
pkg update
pkg install python
```

Copy this `market_price_bot` directory to a location Termux can access. From its parent directory, run:

```sh
python -m market_price_bot
```

The bot collects one sample from each provider at startup and then starts its five-minute cadence. It responds to `/gold-price` and `/bitcoin-price`; send `/stop` to stop it. Only one process may poll `getUpdates` for a bot at a time, so stop the PC bot or any other poller first.

## Storage and Configuration

By default, history is stored at:

```text
~/.local/share/android-auto-market-prices/prices.sqlite3
```

The directory and database are created with private permissions where the platform supports them. Set `MARKET_PRICE_DB_PATH` to choose a different database path. Set `TELEGRAM_CONFIG_PATH` to use a different config file; `TG_BOT_TOKEN` and `TG_CHAT_ID` override the matching config values for that process.

Each successful sample records asset/provider identifiers, price, quote currency, unit, UTC fetch time, and a provider timestamp if returned. History is retained indefinitely; back up the SQLite file while the bot is stopped for a consistent copy. No failed/invalid response is recorded as a price sample. Failure from one provider does not prevent trying the other.

## Adding Assets

Add an `Asset` entry to `ASSETS` in `models.py` with a unique `asset_id`, display name, provider key, market symbol, quote currency, and unit. If the provider is already registered in `price_sources.py`, no new storage or command logic is needed. Add an explicit command-to-asset mapping in `COMMAND_ASSETS` in `telegram_commands.py` for any new Telegram query. For a new provider, implement and test an adapter in `price_sources.py`, then register it in `PROVIDERS`.

## Tests

Run the offline test suite from the Android-Auto repository root; no token or network access is needed:

```sh
python -m unittest discover -s market_price_bot/tests -v
python -m compileall market_price_bot
```

## Operational Limits

Android Doze, network outages, battery management, or force-stop may delay or prevent collection. The five-minute interval is best-effort, and timestamps show when the sample was actually fetched. Do not run the app simultaneously with another `getUpdates` consumer for this bot.