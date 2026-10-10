"""Offline tests for the camera capture wrapper (official-script subprocess)."""
import unittest
from pathlib import Path
from unittest import mock

from demo_ui.camera_capture import TOOL, capture_clip, rotate_180


class TestCaptureClip(unittest.TestCase):
    def _run_mock(self, returncode=0, stderr="", side_effect=None):
        return mock.patch(
            "demo_ui.camera_capture.subprocess.run",
            return_value=mock.Mock(returncode=returncode, stderr=stderr),
            side_effect=side_effect,
        )

    def test_success_returns_clip_path(self):
        with mock.patch.dict("os.environ", {"CAMERA_OUTPUT_FILE": "/tmp/video_capture.mp4"}):
            with self._run_mock() as run, mock.patch.object(
                    Path, "is_file", return_value=True):
                clip = capture_clip()
        self.assertEqual(clip, Path("/tmp/video_capture.mp4"))
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[0], "python3")
        self.assertEqual(cmd[1], str(TOOL))
        self.assertIn("--camera_id", cmd)
        self.assertIn("--robot_ip", cmd)
        self.assertIn("--output_file", cmd)
        self.assertIn("--capture_seconds", cmd)

    def test_nonzero_exit_falls_back_to_none(self):
        with self._run_mock(returncode=1, stderr="connection refused") as run:
            self.assertIsNone(capture_clip())

    def test_timeout_falls_back_to_none(self):
        with self._run_mock(side_effect=__import__("subprocess").TimeoutExpired("x", 30)):
            self.assertIsNone(capture_clip())

    def test_missing_tool_falls_back_to_none(self):
        with mock.patch.object(Path, "is_file", return_value=False):
            self.assertIsNone(capture_clip())


class TestRotate180(unittest.TestCase):
    def test_rotates_frames_and_keeps_resolution(self):
        import cv2
        import numpy as np
        src = Path("/tmp/_test_clip_rot.mp4")
        writer = cv2.VideoWriter(str(src), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (320, 240))
        for i in range(3):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            cv2.putText(frame, str(i), (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            writer.write(frame)
        writer.release()
        out = rotate_180(src)
        self.assertTrue(out.is_file())
        cap = cv2.VideoCapture(str(out))
        ok, frame = cap.read()
        cap.release()
        self.assertTrue(ok)
        self.assertEqual(frame.shape[:2], (240, 320))
        out.unlink()
        src.unlink()


if __name__ == "__main__":
    unittest.main()
