"""Robot camera capture via the OFFICIAL SDK example (get_video_stream.py).

Follows the official interface manual: the camera is a live RTSP stream
(rtsp://{ip}:2554/live_{camera_id}); the official script records a few seconds
of it to a local mp4. The clip is TEMPORARY only — it is uploaded to the cloud
and deleted; the robot keeps no video storage.

The official script is called as a subprocess so the capture code stays exactly
as PrimeBot ships it (apps/demo_ui/robot_tools/get_video_stream.py, verbatim
from the portal SDK v1.0.0.0).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "robot_tools" / "get_video_stream.py"


def capture_clip(output: str | None = None) -> Path | None:
    """Record a clip from the robot's live camera stream with the official script.

    Returns the mp4 path, or None when capture is unavailable (robot not
    reachable, camera off) — callers must fall back to prompt-only generation.
    """
    robot_ip = os.environ.get("CAMERA_ROBOT_IP", "10.1.1.100")
    camera_id = os.environ.get("CAMERA_ID", "head_stereo_left")
    seconds = os.environ.get("CAMERA_CAPTURE_SECONDS", "5.0")
    output_file = output or os.environ.get("CAMERA_OUTPUT_FILE", "/tmp/video_capture.mp4")
    timeout_s = float(os.environ.get("CAMERA_CAPTURE_TIMEOUT_S", str(float(seconds) + 30)))

    if not TOOL.is_file():
        print("[camera] official capture tool missing; prompt-only mode", flush=True)
        return None
    cmd = [
        "python3", str(TOOL),
        "--camera_id", camera_id,
        "--robot_ip", robot_ip,
        "--output_file", output_file,
        "--capture_seconds", seconds,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"[camera] capture failed ({type(exc).__name__}); "
              f"falling back to prompt-only", flush=True)
        return None
    if proc.returncode != 0:
        print(f"[camera] official script exited {proc.returncode}: "
              f"{(proc.stderr or '').strip()[:200]}", flush=True)
        return None
    clip = Path(output_file)
    if not clip.is_file():
        return None
    if os.environ.get("CAMERA_FLIP_180", "0") == "1":
        clip = rotate_180(clip)
    return clip


def rotate_180(clip: Path) -> Path:
    """Official manual note (接口说明.md, RTSP section): in biped form the left
    camera's raw picture is upside-down — the application must rotate 180 degrees.
    Enable via CAMERA_FLIP_180=1 once the demo's form/mode is confirmed on-site."""
    import cv2
    cap = cv2.VideoCapture(str(clip))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = clip.with_name(clip.stem + "_flip.mp4")
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(cv2.rotate(frame, cv2.ROTATE_180))
    cap.release()
    writer.release()
    return out
