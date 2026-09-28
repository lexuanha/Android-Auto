import unittest

from camera_bot.telegram_commands import handle_message


def message(text, sender_id=12345, chat_id=12345):
    return {"text": text, "from": {"id": sender_id}, "chat": {"id": chat_id}}


class TelegramCommandTests(unittest.TestCase):
    def test_photo_command_accepts_bot_suffix(self):
        response = handle_message(message("/photo@my_camera_bot"), "12345")
        self.assertEqual(response.command, "/photo")
        self.assertIsNone(response.text)

    def test_front_and_back_photo_commands(self):
        front = handle_message(message("/photo-front@my_camera_bot"), "12345")
        back = handle_message(message("/photo-back"), "12345")
        self.assertEqual(front.command, "/photo-front")
        self.assertEqual(back.command, "/photo-back")

    def test_stop_requires_authorized_private_chat(self):
        response = handle_message(message("/stop"), "12345")
        self.assertTrue(response.should_stop)
        self.assertIn("dừng", response.text)

        unauthorized = handle_message(message("/stop", chat_id=999), "12345")
        self.assertFalse(unauthorized.should_stop)
        self.assertIsNone(unauthorized.text)

    def test_video_command_is_explicitly_unavailable(self):
        response = handle_message(message("/video"), "12345")
        self.assertIn("chưa được hỗ trợ", response.text)


if __name__ == "__main__":
    unittest.main()