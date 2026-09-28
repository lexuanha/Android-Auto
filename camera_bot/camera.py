import json
import subprocess
from pathlib import Path

CAMERA_TIMEOUT_SECONDS = 60


def _camera_id(facing: str) -> str:
    if facing not in {"front", "back"}:
        raise ValueError("Camera facing must be 'front' or 'back'")
    try:
        result = subprocess.run(
            ["termux-camera-info"],
            check=True,
            capture_output=True,
            text=True,
            timeout=CAMERA_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        raise RuntimeError("Termux:API camera tools are missing; install termux-api") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError("Reading camera information timed out") from None
    except subprocess.CalledProcessError:
        raise RuntimeError("Could not read camera information; check Termux:API permission") from None

    try:
        cameras = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("Termux:API returned invalid camera information") from None
    if not isinstance(cameras, list):
        raise RuntimeError("Termux:API returned invalid camera information")
    for camera in cameras:
        if isinstance(camera, dict) and camera.get("facing") == facing and camera.get("id") is not None:
            return str(camera["id"])
    raise RuntimeError(f"No {facing}-facing camera was found")


def capture_photo(output_path: Path, facing: str = "back") -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    camera_id = _camera_id(facing)
    try:
        subprocess.run(
            ["termux-camera-photo", "-c", camera_id, str(output_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=CAMERA_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        raise RuntimeError("Termux:API camera tools are missing; install termux-api") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError("Camera capture timed out") from None
    except subprocess.CalledProcessError:
        raise RuntimeError("Camera capture failed; check Termux:API camera permission") from None

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("Camera did not create a photo")
    return output_path