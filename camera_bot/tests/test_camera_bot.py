import unittest
from unittest.mock import patch

from camera_bot.camera_bot import run_bot


class CameraBotTests(unittest.TestCase):
    def test_photo_is_sent_and_authorized_stop_exits_polling(self):
        photo_front_update = {
            "update_id": 42,
            "message": {"text": "/photo-front", "from": {"id": 12345}, "chat": {"id": 12345}},
        }
        photo_back_update = {
            "update_id": 43,
            "message": {"text": "/photo-back", "from": {"id": 12345}, "chat": {"id": 12345}},
        }
        photo_update = {
            "update_id": 44,
            "message": {"text": "/photo", "from": {"id": 12345}, "chat": {"id": 12345}},
        }
        stop_update = {
            "update_id": 45,
            "message": {"text": "/stop", "from": {"id": 12345}, "chat": {"id": 12345}},
        }
        with patch(
            "camera_bot.camera_bot.get_updates",
            side_effect=[[], [photo_front_update, photo_back_update, photo_update, stop_update]],
        ):
            with patch("camera_bot.camera_bot.capture_photo") as capture:
                with patch("camera_bot.camera_bot.send_photo") as send_photo:
                    with patch("camera_bot.camera_bot.send_message") as send_message:
                        run_bot("test-token", "12345")

        self.assertEqual([call.args[1] for call in capture.call_args_list], ["front", "back", "back"])
        self.assertEqual(send_photo.call_count, 3)
        self.assertTrue(any("camera trước" in call.args[2] for call in send_message.call_args_list))
        self.assertTrue(any("camera sau" in call.args[2] for call in send_message.call_args_list))
        self.assertTrue(any("dừng" in call.args[2] for call in send_message.call_args_list))


if __name__ == "__main__":
    unittest.main()