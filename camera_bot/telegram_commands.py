from dataclasses import dataclass

PHOTO_COMMAND_FACING = {
    "/photo": "back",
    "/photo-back": "back",
    "/photo-front": "front",
}


@dataclass(frozen=True)
class CommandResponse:
    text: str | None = None
    command: str | None = None
    should_stop: bool = False


def _command_from_text(text: object) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    token = text.strip().split(maxsplit=1)[0]
    return token.split("@", maxsplit=1)[0].lower()


def handle_message(message: object, authorized_chat_id: str) -> CommandResponse:
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
        return CommandResponse(text="Đã nhận lệnh dừng camera bot.", should_stop=True)
    if command in PHOTO_COMMAND_FACING:
        return CommandResponse(command=command)
    if command == "/video":
        return CommandResponse(text="Lệnh /video chưa được hỗ trợ trên Termux:API hiện tại.")
    return CommandResponse()