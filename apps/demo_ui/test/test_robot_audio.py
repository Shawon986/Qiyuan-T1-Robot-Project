"""Offline tests for the robot speaker playback (official PlayAudioFile path)."""
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest import mock

import demo_ui.robot_audio as ra
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
        """Official example: file_path = DIRECTORY, file_name = filename,
        24 kHz mono; media_role Communication; success = code 0."""

        class FakeInfo:
            def __init__(self):
                self.channels = 0
                self.sample_rate = 0
                self.size = 0
                self.sample_format = ""
                self.coding_format = ""

        class FakeAudioFile:
            def __init__(self):
                self.info = FakeInfo()
                self.pkg_name = ""
                self.file_name = ""
                self.file_path = ""
                self.media_role = ""
                self.priority = 0
                self.priority_weight = 0

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
             mock.patch.object(Path, "is_file", return_value=True), \
             mock.patch.object(ra, "convert_to_robot_wav", side_effect=lambda p: p), \
             mock.patch.object(ra, "upload_enabled", return_value=False):
            ok = player.play_file("/tmp/reply.wav")

        self.assertTrue(ok)
        req = captured["req"]
        self.assertEqual(req.file.pkg_name, "qiyuan-demo")
        self.assertEqual(req.file.file_name, "reply.wav")
        self.assertEqual(req.file.file_path, "/tmp")  # directory, not the full path
        self.assertEqual(req.file.media_role, "Communication")
        self.assertEqual(req.file.priority, 6)
        self.assertEqual(req.file.info.channels, 1)
        self.assertEqual(req.file.info.sample_rate, 24000)
        self.assertEqual(req.file.info.coding_format, "wave")
        self.assertEqual(req.file.info.sample_format, "S16_LE")

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


class TestAcceptedSemantics(unittest.TestCase):
    """Official example treats code == 0 OR status == SUCCESS as accepted."""

    @staticmethod
    def _resp(code, status=None):
        common = types.SimpleNamespace(
            header=types.SimpleNamespace(code=code),
            status=types.SimpleNamespace(value=status if status is not None else 0),
            message="")
        return types.SimpleNamespace(response=common)

    def test_code_zero_accepted_even_with_failing_status(self):
        self.assertTrue(ra.request_accepted(self._resp(0, 0)))

    def test_status_success_accepted_even_with_failing_code(self):
        self.assertTrue(ra.request_accepted(self._resp(1, 1)))

    def test_both_failing_rejected(self):
        self.assertFalse(ra.request_accepted(self._resp(1, 0)))

    def test_malformed_response_rejected(self):
        self.assertFalse(ra.request_accepted(types.SimpleNamespace()))


class TestWaitForQuiet(unittest.TestCase):
    def test_no_state_feed_passes_immediately(self):
        player = RobotAudioPlayer()
        player._node = None  # dev PC: no play-state subscription -> nothing to wait for
        self.assertTrue(player._wait_for_quiet())

    def test_quiet_topic_returns_true(self):
        player = RobotAudioPlayer()
        player._node = mock.Mock()
        # monotonic is called for both deadline computations, then once per loop
        with mock.patch("demo_ui.robot_audio.time.monotonic", side_effect=[0.0, 0.1, 1.5]), \
             mock.patch("demo_ui.robot_audio.time.sleep"):
            self.assertTrue(player._wait_for_quiet())

    def test_other_audio_playing_times_out_to_false(self):
        player = RobotAudioPlayer()
        player._node = mock.Mock()
        player._play_events = [(0.0, "other", 1)]  # someone else is playing
        with mock.patch("demo_ui.robot_audio.time.monotonic", side_effect=[0.0, 0.1, 9.0]), \
             mock.patch("demo_ui.robot_audio.time.sleep"):
            self.assertFalse(player._wait_for_quiet())


class TestConversion(unittest.TestCase):
    def _wav(self, rate, channels=1, width=2):
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as w:
            w.setparams((channels, width, rate, 0, "NONE", "not compressed"))
            w.writeframes(b"\x00\x00" * 10)
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_needs_conversion_for_mp3(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(b"ID3 fake mp3 bytes")
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        self.assertTrue(ra.needs_conversion(Path(tmp.name)))

    def test_needs_conversion_for_16k_wav(self):
        self.assertTrue(ra.needs_conversion(self._wav(16000)))

    def test_24k_mono_wav_needs_no_conversion(self):
        self.assertFalse(ra.needs_conversion(self._wav(24000)))

    def test_convert_without_ffmpeg_returns_source(self):
        src = self._wav(16000)
        with mock.patch("demo_ui.robot_audio.shutil.which", return_value=None):
            self.assertEqual(ra.convert_to_robot_wav(src), src)

    def test_convert_runs_ffmpeg_to_24k_mono(self):
        src = self._wav(16000)
        with mock.patch("demo_ui.robot_audio.shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("demo_ui.robot_audio.subprocess.run") as run:
            dst = ra.convert_to_robot_wav(src)
        self.assertEqual(dst.name, src.stem + "_24k.wav")
        args = run.call_args.args[0]
        self.assertEqual(args[0], "/usr/bin/ffmpeg")
        self.assertIn("-ar", args)
        self.assertIn("24000", args)


class TestUpload(unittest.TestCase):
    def test_upload_enabled_env_off(self):
        with mock.patch.dict("os.environ", {"ROBOT_AUDIO_UPLOAD": "off"}):
            self.assertFalse(ra.upload_enabled())

    def test_upload_enabled_env_on(self):
        with mock.patch.dict("os.environ", {"ROBOT_AUDIO_UPLOAD": "on"}):
            self.assertTrue(ra.upload_enabled())

    def test_upload_auto_on_pc_is_off(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch.object(ra, "is_robot_board", return_value=False):
            self.assertFalse(ra.upload_enabled())

    def test_upload_auto_on_robot_is_on(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch.object(ra, "is_robot_board", return_value=True):
            self.assertTrue(ra.upload_enabled())

    def test_remote_cmd_plain_ssh(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            cmd = ra.remote_cmd("ssh", "run@10.1.1.100", "echo hi")
        self.assertEqual(cmd[0], "ssh")
        self.assertIn("-o", cmd)
        self.assertIn("StrictHostKeyChecking=accept-new", cmd)
        self.assertEqual(cmd[-2:], ["run@10.1.1.100", "echo hi"])

    def test_remote_cmd_sshpass_prefix(self):
        with mock.patch.dict("os.environ", {"ROBOT_SSH_PASSWORD": "secret"}, clear=True), \
             mock.patch("demo_ui.robot_audio.shutil.which", return_value="/usr/bin/sshpass"):
            cmd = ra.remote_cmd("scp", "a.wav", "run@10.1.1.100:/tmp/x.wav")
        self.assertEqual(cmd[:3], ["/usr/bin/sshpass", "-p", "secret"])
        self.assertEqual(cmd[3], "scp")

    def test_upload_to_soc0_returns_remote_path(self):
        def fake_run(cmd, **kwargs):
            if cmd[0] == "ssh":
                out = mock.Mock()
                out.stdout = "/tmp/qiyuan-demo.ABC12345\n"
                return out
            return mock.Mock()  # scp ok
        with mock.patch("demo_ui.robot_audio.subprocess.run", side_effect=fake_run):
            self.assertEqual(ra.upload_to_soc0(Path("/tmp/reply.wav")),
                             "/tmp/qiyuan-demo.ABC12345/reply.wav")

    def test_upload_to_soc0_ssh_failure_falls_back_to_none(self):
        with mock.patch("demo_ui.robot_audio.subprocess.run",
                        side_effect=OSError("down")):
            self.assertIsNone(ra.upload_to_soc0(Path("/tmp/reply.wav")))


if __name__ == "__main__":
    unittest.main()
