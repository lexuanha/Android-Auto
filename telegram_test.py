import argparse
from getpass import getpass
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_CHAT_ID = "7528793637"


def send_message(token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(f"Telegram HTTP error {error.code}") from None
    except URLError as error:
        raise RuntimeError(f"Network error: {error.reason}") from None

    if not result.get("ok"):
        raise RuntimeError("Telegram rejected the message")


def get_updates(token: str, offset: int | None, timeout_seconds: int) -> list[dict]:
    params = {"timeout": timeout_seconds, "allowed_updates": '["message"]'}
    if offset is not None:
        params["offset"] = offset
    url = f"https://api.telegram.org/bot{token}/getUpdates?{urlencode(params)}"
    try:
        with urlopen(url, timeout=timeout_seconds + 10) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(f"Telegram HTTP error {error.code} while polling") from None
    except URLError as error:
        raise RuntimeError(f"Polling network error: {error.reason}") from None
    if not result.get("ok"):
        raise RuntimeError("Telegram rejected update polling")
    return result.get("result", [])


def wait_for_stop(token: str, chat_id: str, duration: int, offset: int | None) -> tuple[bool, int | None]:
    deadline = time.monotonic() + duration
    stop_commands = {"/stop"}

    while time.monotonic() < deadline:
        timeout_seconds = min(20, max(1, int(deadline - time.monotonic())))
        try:
            updates = get_updates(token, offset, timeout_seconds)
        except RuntimeError as error:
            print(f"Telegram command polling failed: {error}", flush=True)
            time.sleep(min(5, max(0, deadline - time.monotonic())))
            continue

        for update in updates:
            offset = max(offset or 0, int(update["update_id"]) + 1)
            message = update.get("message", {})
            sender = message.get("from", {})
            chat = message.get("chat", {})
            text = message.get("text", "").strip()
            command = text.split(maxsplit=1)[0].split("@", 1)[0].lower() if text else ""

            if str(sender.get("id")) == chat_id and str(chat.get("id")) == chat_id and command in stop_commands:
                try:
                    send_message(token, chat_id, "Đã nhận lệnh dừng; kết thúc bài thử.")
                except RuntimeError as error:
                    print(f"Could not send stop confirmation: {error}", flush=True)
                print("Stop command received; test ended.", flush=True)
                return True, offset

    return False, offset


def load_config() -> tuple[str, str]:
    config_path = Path.home() / ".config" / "telegram" / "config.json"
    legacy_config_path = Path.home() / ".config" / "telegram-test" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if not config_path.exists() and legacy_config_path.exists():
        config_path.write_bytes(legacy_config_path.read_bytes())
        config_path.chmod(0o600)

    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise RuntimeError("Cannot read Termux config at ~/.config/telegram/config.json") from None
        token = str(config.get("bot_token", "")).strip()
        chat_id = str(config.get("chat_id", DEFAULT_CHAT_ID)).strip()
    else:
        token = ""
        chat_id = DEFAULT_CHAT_ID

    token = os.environ.get("TG_BOT_TOKEN") or token
    chat_id = os.environ.get("TG_CHAT_ID") or chat_id
    if not token:
        token = getpass("New Telegram bot token (input hidden): ").strip()
        if token:
            config_path.write_text(
                json.dumps({"bot_token": token, "chat_id": chat_id}, indent=2) + "\n",
                encoding="utf-8",
            )
            config_path.chmod(0o600)

    if not token or not chat_id:
        raise RuntimeError("Bot token and chat ID are required")
    return token, chat_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a finite Telegram connectivity test.")
    parser.add_argument("--count", type=int, default=10, help="number of messages (default: 10)")
    parser.add_argument("--interval", type=int, default=180, help="seconds between messages (default: 180)")
    args = parser.parse_args()

    try:
        token, chat_id = load_config()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 2
    if args.count < 1 or args.interval < 1:
        parser.error("--count and --interval must be positive")

    try:
        initial_updates = get_updates(token, None, 0)
    except RuntimeError as error:
        print(f"Cannot start command polling: {error}", file=sys.stderr)
        return 1
    offset = max((int(update["update_id"]) for update in initial_updates), default=-1) + 1

    for attempt in range(1, args.count + 1):
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        message = f"Android Termux test {attempt}/{args.count} at {timestamp} UTC"
        try:
            send_message(token, chat_id, message)
        except RuntimeError as error:
            print(f"{timestamp} UTC: send {attempt}/{args.count} failed: {error}", flush=True)
            return 1
        else:
            print(f"{timestamp} UTC: send {attempt}/{args.count} succeeded", flush=True)

        if attempt < args.count:
            should_stop, offset = wait_for_stop(token, chat_id, args.interval, offset)
            if should_stop:
                return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())