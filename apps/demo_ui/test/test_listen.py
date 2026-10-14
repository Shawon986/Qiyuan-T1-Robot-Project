"""Offline tests for the continuous listen-loop helpers (conversation.main)."""
import io
import unittest
import wave
from unittest import mock

from conversation import main as cm


def _wav_bytes(frames, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        w.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


class TestAudioSeconds(unittest.TestCase):
    def test_wav_duration(self):
        self.assertAlmostEqual(cm._audio_seconds(_wav_bytes(16000)), 1.0)

    def test_mp3_returns_none(self):
        self.assertIsNone(cm._audio_seconds(b"ID3 fake mp3 bytes"))

    def test_garbage_returns_none(self):
        self.assertIsNone(cm._audio_seconds(b"\x00" * 100))


class TestWaitReplyFinished(unittest.TestCase):
    """The robot must never hear itself: the loop sleeps for the reply
    duration + a quiet margin before the next capture window."""

    def test_waits_duration_plus_margin(self):
        with mock.patch("conversation.main.time.sleep") as sleep, \
             mock.patch("conversation.main._audio_seconds", return_value=2.0):
            cm._wait_reply_finished(b"whatever")
        sleep.assert_called_once_with(3.5)

    def test_unknown_duration_uses_conservative_fallback(self):
        with mock.patch("conversation.main.time.sleep") as sleep, \
             mock.patch("conversation.main._audio_seconds", return_value=None):
            cm._wait_reply_finished(b"whatever")
        sleep.assert_called_once_with(9.5)


if __name__ == "__main__":
    unittest.main()
