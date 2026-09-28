import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .camera import capture_photo
from .telegram_commands import PHOTO_COMMAND_FACING, handle_message

TELEGRAM_POLL_SECONDS = 20
TELEGRAM_TIMEOUT_SECONDS = 30
MEDIA_TIMEOUT_SECONDS = 120
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


def _read_api_response(request: Request, timeout: int) -> dict:
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


def _telegram_call(token: str, method: str, payload: dict | None = None, timeout: int = TELEGRAM_TIMEOUT_SECONDS) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    return _read_api_response(request, timeout)


def get_updates(token: str, offset: int | None, timeout_seconds: int) -> list[dict]:
    params = {"timeout": timeout_seconds, "allowed_updates": json.dumps(["message"])}
    if offset is not None:
        params["offset"] = offset
    url = f"https://api.telegram.org/bot{token}/getUpdates?{urlencode(params)}"
    result = _read_api_response(Request(url), timeout_seconds + 10)
    updates = result.get("result", [])
    return updates if isinstance(updates, list) else []


def send_message(token: str, chat_id: str, text: str) -> None:
    _telegram_call(token, "sendMessage", {"chat_id": chat_id, "text": text})


def send_photo(token: str, chat_id: str, photo_path: Path) -> None:
    boundary = f"CameraBot{uuid.uuid4().hex}"
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode()
    ]
    parts.extend(
        [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"photo.jpg\"\r\n".encode(),
            b"Content-Type: image/jpeg\r\n\r\n",
            Path(photo_path).read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    request = Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    _read_api_response(request, MEDIA_TIMEOUT_SECONDS)


def _send_message_safely(token: str, chat_id: str, text: str) -> None:
    try:
        send_message(token, chat_id, text)
    except RuntimeError as error:
        print(f"Telegram reply failed: {error}", file=sys.stderr, flush=True)


def _capture_and_send_photo(token: str, chat_id: str, facing: str) -> None:
    try:
        with tempfile.TemporaryDirectory(prefix="camera-bot-") as directory:
            photo_path = capture_photo(Path(directory) / "photo.jpg", facing)
            send_photo(token, chat_id, photo_path)
    except (OSError, RuntimeError) as error:
        print(f"Photo command failed: {error}", file=sys.stderr, flush=True)
        _send_message_safely(token, chat_id, f"Không thể chụp/gửi ảnh: {error}")
        return
    camera_name = "trước" if facing == "front" else "sau"
    _send_message_safely(token, chat_id, f"Đã chụp và gửi ảnh từ camera {camera_name}.")


def run_bot(token: str, chat_id: str) -> None:
    try:
        initial_updates = get_updates(token, None, 0)
    except RuntimeError as error:
        raise RuntimeError(f"Cannot start Telegram polling: {error}") from None
    offset = max((int(update.get("update_id", -1)) for update in initial_updates), default=-1) + 1
    print("Camera bot started. Send /photo, /photo-front, /photo-back, or /stop.", flush=True)

    while True:
        try:
            updates = get_updates(token, offset if offset > 0 else None, TELEGRAM_POLL_SECONDS)
        except RuntimeError as error:
            print(f"Telegram polling failed: {error}", file=sys.stderr, flush=True)
            time.sleep(5)
            continue

        for update in updates:
            if not isinstance(update, dict):
                continue
            try:
                update_id = int(update.get("update_id", -1))
            except (TypeError, ValueError):
                continue
            offset = max(offset, update_id + 1)
            response = handle_message(update.get("message"), chat_id)
            facing = PHOTO_COMMAND_FACING.get(response.command)
            if facing is not None:
                _capture_and_send_photo(token, chat_id, facing)
            if response.text:
                _send_message_safely(token, chat_id, response.text)
            if response.should_stop:
                print("Stop command received; exiting.", flush=True)
                return


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