# Android Camera Bot

A Python Telegram bot for Termux that captures a photo with the Android rear camera and sends it to the configured private chat. The bot polls Telegram continuously and exits on `/stop`.

## Commands

- `/photo`: alias for `/photo-back`.
- `/photo-back`: find a rear-facing camera using `termux-camera-info`, capture a JPEG, and send it to Telegram.
- `/photo-front`: find a front-facing camera, capture a JPEG, and send it to Telegram.
- `/stop`: stop the bot.
- `/video`: currently reports that video capture is unavailable. The official Termux:API package provides photo capture but no video-recording command.

Only the configured private chat can run commands. Stop any other process polling updates for the same bot before starting this one.

## Requirements

- Termux and Python 3.10 or newer.
- The Termux:API package in Termux and the matching Termux:API Android companion app. Install Termux and its add-ons from the same source/signing family.
- Camera permission granted to the Termux:API app.
- The shared Telegram configuration at `~/.config/telegram/config.json`:

```json
{
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_PRIVATE_CHAT_ID"
}
```

Keep the config private (`chmod 600 ~/.config/telegram/config.json`) and never commit the token. `TG_BOT_TOKEN` and `TG_CHAT_ID` environment variables override the corresponding config values. `TELEGRAM_CONFIG_PATH` selects another config file.

## Install and run

In Termux, install Python and the command-line bridge:

```sh
pkg update
pkg install python termux-api
```

Copy the `camera_bot` directory to a location Termux can access. From its parent directory, run:

```sh
python -m camera_bot
```

Grant camera permission when Android prompts. The bot finds the camera whose reported facing is `back`, captures with `termux-camera-photo`, and removes the temporary image after Telegram accepts the upload.

## Tests

Run offline tests from the repository root; no Telegram token, network, or Android camera is needed:

```sh
python -m unittest discover -s camera_bot/tests -v
python -m compileall camera_bot
```