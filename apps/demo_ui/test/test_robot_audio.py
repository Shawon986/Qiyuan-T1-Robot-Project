"""Offline tests for the robot speaker playback (official PlayAudioFile path)."""
import unittest
from pathlib import Path
from unittest import mock

from demo_ui.robot_audio import RobotAudioPlayer, SERVICE_NAME


class TestPlaybackGate(unittest.TestCase):
    def test_disabled_by_default_does_nothing(self):
        player = RobotAudioPlayer()
        with mock.patch.dict("os.environ", {"AUDIO_PLAYBACK": "off"}):
            self.assertFalse(player.play_file("/tmp/whatever.wav"))

    def test_missing_file_returns_false(self):
        player = RobotAudioPlayer()
        with mock.patch.dict("os.environ", {"AUDIO_PLAYBACK": "playaudiofile"}):
            self.assertFalse(player.play_file("/tmp/does_not_exist.wav"))


class TestRequestBuilding(unittest.TestCase):
    def test_request_fields_follow_official_protocol(self):
        """Request must be CommonRequest + AudioFile with the official fields."""

        class FakeInfo:
            def __init__(self):
                self.channels = 0
                self.sample_rate = 0
                self.coding_format = ""

        class FakeAudioFile:
            def __init__(self):
                self.info = FakeInfo()

        class FakeRequest:
            def __init__(self):
                self.file = FakeAudioFile()

        class FakeSvc:
            Request = FakeRequest

        class FakeFuture:
            def __init__(self, code=0):
                self._resp = mock.Mock()
                self._resp.response.header.code = code

            def done(self):
                return True

            def result(self):
                return self._resp

        player = RobotAudioPlayer()
        captured = {}

        def call(req):
            captured["req"] = req
            return FakeFuture()

        client = mock.Mock()
        client.call_async = call
        player._client = client
        player._svc = FakeSvc
        player._AudioFile = FakeAudioFile
        player._CommonRequest = mock.Mock

        with mock.patch.dict("os.environ", {"AUDIO_PLAYBACK": "playaudiofile"}), \
             mock.patch.object(Path, "is_file", return_value=True):
            ok = player.play_file("/tmp/reply.wav")

        self.assertTrue(ok)
        req = captured["req"]
        self.assertEqual(req.file.pkg_name, "qiyuan-demo")
        self.assertEqual(req.file.file_name, "reply.wav")
        self.assertEqual(req.file.file_path, "/tmp/reply.wav")
        self.assertEqual(req.file.media_role, "Communication")
        self.assertEqual(req.file.priority, 6)
        self.assertEqual(req.file.info.channels, 1)
        self.assertEqual(req.file.info.sample_rate, 16000)
        self.assertEqual(req.file.info.coding_format, "wave")

    def test_service_failure_returns_false(self):
        player = RobotAudioPlayer()
        with mock.patch.dict("os.environ", {"AUDIO_PLAYBACK": "playaudiofile"}), \
             mock.patch.object(Path, "is_file", return_value=True), \
             mock.patch.object(player, "_ensure", return_value=False):
            self.assertFalse(player.play_file("/tmp/reply.wav"))


class TestRosUnavailable(unittest.TestCase):
    def test_ensure_graceful_when_ros_missing(self):
        player = RobotAudioPlayer()
        with mock.patch.dict("sys.modules", {"rclpy": None}):
            self.assertFalse(player._ensure())


if __name__ == "__main__":
    unittest.main()
