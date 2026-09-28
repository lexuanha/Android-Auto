import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from camera_bot.camera import capture_photo


class CameraTests(unittest.TestCase):
    def test_capture_uses_requested_camera_and_requires_output(self):
        with tempfile.TemporaryDirectory() as directory:
            photo_path = Path(directory) / "photo.jpg"

            def run_camera(arguments, **_kwargs):
                if arguments == ["termux-camera-info"]:
                    cameras = [{"id": "0", "facing": "front"}, {"id": "2", "facing": "back"}]
                    return subprocess.CompletedProcess(arguments, 0, stdout=json.dumps(cameras))
                Path(arguments[-1]).write_bytes(b"jpeg-data")
                return subprocess.CompletedProcess(arguments, 0)

            with patch("camera_bot.camera.subprocess.run", side_effect=run_camera) as run:
                self.assertEqual(capture_photo(photo_path, "back"), photo_path)

            self.assertEqual(run.call_args_list[1].args[0][:3], ["termux-camera-photo", "-c", "2"])
            self.assertEqual(photo_path.read_bytes(), b"jpeg-data")

    def test_capture_can_select_front_camera(self):
        cameras = [{"id": "0", "facing": "back"}, {"id": "1", "facing": "front"}]
        photo_path = Path(tempfile.gettempdir()) / "camera-bot-front-test.jpg"

        def run_camera(arguments, **_kwargs):
            if arguments == ["termux-camera-info"]:
                return subprocess.CompletedProcess(arguments, 0, stdout=json.dumps(cameras))
            Path(arguments[-1]).write_bytes(b"jpeg-data")
            return subprocess.CompletedProcess(arguments, 0)

        try:
            with patch("camera_bot.camera.subprocess.run", side_effect=run_camera) as run:
                capture_photo(photo_path, "front")
            self.assertEqual(run.call_args_list[1].args[0][:3], ["termux-camera-photo", "-c", "1"])
        finally:
            photo_path.unlink(missing_ok=True)

    def test_missing_camera_command_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("camera_bot.camera.subprocess.run", side_effect=FileNotFoundError):
                with self.assertRaisesRegex(RuntimeError, "install termux-api"):
                    capture_photo(Path(directory) / "photo.jpg")

    def test_capture_fails_when_no_rear_camera_is_reported(self):
        cameras = [{"id": "0", "facing": "front"}]
        completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(cameras))
        with tempfile.TemporaryDirectory() as directory:
            with patch("camera_bot.camera.subprocess.run", return_value=completed) as run:
                with self.assertRaisesRegex(RuntimeError, "No back-facing camera"):
                    capture_photo(Path(directory) / "photo.jpg")
        run.assert_called_once_with(
            ["termux-camera-info"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )


if __name__ == "__main__":
    unittest.main()