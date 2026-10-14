"""Offline tests for the robot mic capture math (official 8ch/48kHz protocol)."""
import array
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

import conversation.mic_capture as mc


class TestExtractMicMono(unittest.TestCase):
    def test_rejects_partial_frames(self):
        with self.assertRaises(ValueError):
            mc.extract_mic_mono(b"\x00\x00" * 3)

    def test_averages_ch5_ch6_and_applies_gain(self):
        frame = array.array("h", [0, 0, 0, 0, 1000, 2000, 0, 0])
        mono = mc.extract_mic_mono(frame.tobytes(), gain=10.0)
        self.assertEqual(array.array("h", mono).tolist(), [15000])

    def test_clips_at_int16(self):
        frame = array.array("h", [0, 0, 0, 0, 30000, 30000, 0, 0])
        mono = mc.extract_mic_mono(frame.tobytes(), gain=10.0)
        self.assertEqual(array.array("h", mono).tolist(), [32767])

    def test_multiple_frames(self):
        frames = array.array("h", [0, 0, 0, 0, 100, 200, 0, 0] * 4)
        mono = array.array("h", mc.extract_mic_mono(frames.tobytes(), gain=1.0))
        self.assertEqual(mono.tolist(), [150] * 4)


class TestResampleAndWav(unittest.TestCase):
    def test_decimate_48k_to_16k(self):
        pcm = array.array("h", range(9)).tobytes()  # 0..8
        out = mc.decimate_mono(pcm, 48000, 16000)
        self.assertEqual(array.array("h", out).tolist(), [0, 3, 6])

    def test_decimate_non_integer_ratio_raises(self):
        with self.assertRaises(ValueError):
            mc.decimate_mono(b"\x00\x00", 48000, 22050)

    def test_write_mono_wav_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.wav"
            pcm = array.array("h", [1, -2, 3]).tobytes()
            mc.write_mono_wav(path, pcm, 16000)
            with wave.open(str(path), "rb") as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth(),
                                  w.getframerate()), (1, 2, 16000))
                self.assertEqual(w.readframes(3), pcm)


class TestPulseServer(unittest.TestCase):
    def test_env_override_wins(self):
        with mock.patch.dict("os.environ", {"MIC_PULSE_SERVER": "unix:/tmp/x"}):
            self.assertEqual(mc.pulse_server(), "unix:/tmp/x")

    def test_robot_board_uses_unix_socket(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch.object(mc, "is_robot_board", return_value=True):
            self.assertEqual(mc.pulse_server(), "unix:/run/user/1000/pulse/native")

    def test_pc_uses_camera_robot_ip_tcp(self):
        with mock.patch.dict("os.environ", {"CAMERA_ROBOT_IP": "10.1.1.100"},
                             clear=True), \
             mock.patch.object(mc, "is_robot_board", return_value=False):
            self.assertEqual(mc.pulse_server(), "tcp:10.1.1.100:4713")

    def test_no_endpoint_raises(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch.object(mc, "is_robot_board", return_value=False):
            with self.assertRaises(RuntimeError):
                mc.pulse_server()


class TestCaptureFailure(unittest.TestCase):
    def test_capture_without_parec_raises_helpfully(self):
        with mock.patch.dict("os.environ", {"MIC_PULSE_SERVER": "tcp:10.1.1.100:4713"}), \
             mock.patch("conversation.mic_capture.shutil.which", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                mc.capture(1.0, Path("/tmp/out.wav"))
            self.assertIn("parec", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
