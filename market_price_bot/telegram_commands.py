from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .models import ASSETS, PriceQuote

COMMAND_ASSETS = {
    "/gold-price": "gold",
    "/bitcoin-price": "bitcoin",
}
STALE_AFTER = timedelta(minutes=10)


@dataclass(frozen=True)
class CommandResponse:
    text: str | None = None
    should_stop: bool = False


def _command_from_text(text: object) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    token = text.strip().split(maxsplit=1)[0]
    return token.split("@", maxsplit=1)[0].lower()


def _format_price(quote: PriceQuote, now: datetime) -> str:
    value = format(quote.price, ",f")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    fetched_at = quote.fetched_at.astimezone(timezone.utc)
    response = (
        f"{quote.asset.name}: {value} {quote.asset.quote_currency} / {quote.asset.unit}\n"
        f"Lấy lúc: {fetched_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    if now.astimezone(timezone.utc) - fetched_at > STALE_AFTER:
        response = f"DỮ LIỆU CŨ\n{response}"
    return response


def handle_message(
    message: object,
    store: object,
    authorized_chat_id: str,
    now: datetime | None = None,
) -> CommandResponse:
    if not isinstance(message, dict):
        return CommandResponse()
    sender = message.get("from", {})
    chat = message.get("chat", {})
    if not isinstance(sender, dict) or not isinstance(chat, dict):
        return CommandResponse()
    if str(sender.get("id")) != authorized_chat_id or str(chat.get("id")) != authorized_chat_id:
        return CommandResponse()

    command = _command_from_text(message.get("text"))
    if command == "/stop":
        return CommandResponse(text="Đã nhận lệnh dừng collector.", should_stop=True)
    asset_id = COMMAND_ASSETS.get(command)
    if asset_id is None:
        return CommandResponse()

    quote = store.latest(asset_id)
    if quote is None:
        asset = ASSETS[asset_id]
        return CommandResponse(text=f"Chưa có dữ liệu giá cho {asset.name}.")
    current_time = now or datetime.now(timezone.utc)
    return CommandResponse(text=_format_price(quote, current_time))