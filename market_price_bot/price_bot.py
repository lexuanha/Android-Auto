import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import ASSETS
from .price_sources import PROVIDERS, PriceSourceError
from .price_store import PriceStore
from .telegram_commands import handle_message

COLLECTION_INTERVAL_SECONDS = 300
TELEGRAM_POLL_SECONDS = 20
TELEGRAM_TIMEOUT_SECONDS = 30
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "telegram" / "config.json"


def load_telegram_config() -> tuple[str, str]:
    config_path = Path(os.environ.get("TELEGRAM_CONFIG_PATH", DEFAULT_CONFIG_PATH)).expanduser()
    config = {}
    if config_path.exists():
        try:
            loaded_config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise RuntimeError("Cannot read Telegram config at ~/.config/telegram/config.json") from None
        if not isinstance(loaded_config, dict):
            raise RuntimeError("Telegram config must be a JSON object")
        config = loaded_config
    token = os.environ.get("TG_BOT_TOKEN") or str(config.get("bot_token", "")).strip()
    chat_id = os.environ.get("TG_CHAT_ID") or str(config.get("chat_id", "")).strip()
    if not token or not chat_id:
        raise RuntimeError("Telegram bot_token and chat_id are required")
    return token, chat_id


def _telegram_call(token: str, method: str, payload: dict | None = None, timeout: int = TELEGRAM_TIMEOUT_SECONDS) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(f"Telegram HTTP error {error.code}") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("Telegram network request failed") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("Telegram returned invalid JSON") from None
    if not isinstance(result, dict) or not result.get("ok"):
        raise RuntimeError("Telegram rejected the request")
    return result


def get_updates(token: str, offset: int | None, timeout_seconds: int) -> list[dict]:
    params = {"timeout": timeout_seconds, "allowed_updates": json.dumps(["message"])}
    if offset is not None:
        params["offset"] = offset
    url = f"https://api.telegram.org/bot{token}/getUpdates?{urlencode(params)}"
    result = _telegram_call_url(url, timeout_seconds + 10)
    updates = result.get("result", [])
    return updates if isinstance(updates, list) else []


def _telegram_call_url(url: str, timeout: int) -> dict:
    request = Request(url)
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(f"Telegram HTTP error {error.code}") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("Telegram network request failed") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("Telegram returned invalid JSON") from None
    if not isinstance(result, dict) or not result.get("ok"):
        raise RuntimeError("Telegram rejected the request")
    return result


def send_message(token: str, chat_id: str, text: str) -> None:
    _telegram_call(token, "sendMessage", {"chat_id": chat_id, "text": text})


def collect_once(store: PriceStore) -> int:
    successes = 0
    for asset in ASSETS.values():
        provider = PROVIDERS.get(asset.provider)
        if provider is None:
            print(f"No provider registered for asset {asset.asset_id}", file=sys.stderr, flush=True)
            continue
        try:
            quote = provider(asset)
            store.insert(quote)
        except (PriceSourceError, OSError, ValueError) as error:
            print(
                f"Price collection failed for {asset.asset_id}: {type(error).__name__}",
                file=sys.stderr,
                flush=True,
            )
            continue
        successes += 1
        print(f"Stored {asset.asset_id} sample at {quote.fetched_at.isoformat()}", flush=True)
    return successes


def run_bot(
    token: str,
    chat_id: str,
    store: PriceStore | None = None,
    collection_interval: int = COLLECTION_INTERVAL_SECONDS,
) -> None:
    price_store = store or PriceStore()
    collect_once(price_store)
    try:
        initial_updates = get_updates(token, None, 0)
    except RuntimeError as error:
        raise RuntimeError(f"Cannot start Telegram polling: {error}") from None
    offset = max((int(update["update_id"]) for update in initial_updates), default=-1) + 1
    next_collection = time.monotonic() + collection_interval
    print("Market price bot started. Send /stop to end it.", flush=True)

    while True:
        remaining = max(0, int(next_collection - time.monotonic()))
        timeout_seconds = min(TELEGRAM_POLL_SECONDS, remaining)
        try:
            updates = get_updates(token, offset if offset > 0 else None, timeout_seconds)
        except RuntimeError as error:
            print(f"Telegram polling failed: {error}", file=sys.stderr, flush=True)
            time.sleep(min(5, max(0, next_collection - time.monotonic())))
            updates = []

        for update in updates:
            offset = max(offset, int(update.get("update_id", -1)) + 1)
            response = handle_message(update.get("message"), price_store, chat_id)
            if response.text:
                try:
                    send_message(token, chat_id, response.text)
                except RuntimeError as error:
                    print(f"Telegram reply failed: {error}", file=sys.stderr, flush=True)
            if response.should_stop:
                print("Stop command received; exiting.", flush=True)
                return

        if time.monotonic() >= next_collection:
            collect_once(price_store)
            next_collection = time.monotonic() + collection_interval


def main() -> int:
    try:
        token, chat_id = load_telegram_config()
        run_bot(token, chat_id)
    except KeyboardInterrupt:
        print("Interrupted; exiting.", flush=True)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())