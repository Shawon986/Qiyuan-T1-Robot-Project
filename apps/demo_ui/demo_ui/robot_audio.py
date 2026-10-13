"""Robot speaker playback via the OFFICIAL PlayAudioFile service.

Why this exists: the platform cloud TTS (primebot.cn) is Mandarin-only and
overwrites local voice configuration within 5 s of connection. We never use
that service — our Cantonese audio (AIChain voice 94 / BytePlus) is generated
with our own API keys, saved to a temp file, and played through
`PlayAudioFile`, which is a LOCAL FILE playback interface: no voice, no
language, no tone settings for the cloud to overwrite.

Protocol (接口说明.md §2.2.1.3): request = CommonRequest + AudioFile
(pkg_name / file_name / file_path absolute / info / priority 1-10 /
media_role — "Communication" = 对话语音, priority 60, ducks music).
WAV files: the RIFF header is auto-parsed; AudioInfo optional.

Fully graceful: when ROS or the service is unavailable (e.g. on the dev PC),
playback is skipped and the conversation never breaks.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

SERVICE_NAME = "/aimdk_5Fmsgs/srv/PlayAudioFile"
MEDIA_ROLE_COMMUNICATION = "Communication"
SERVICE_TIMEOUT_S = 3.0


class RobotAudioPlayer:
    def __init__(self, temp_dir: str | None = None) -> None:
        # official storage scheme (快速入门指南 §2.1.6): audio files -> /home/user/audio.
        # On machines without /home/user (e.g. the dev PC) fall back to the system
        # temp dir so the module never breaks.
        path = Path(temp_dir or os.environ.get("AUDIO_TEMP_DIR", "/home/user/audio"))
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            import tempfile
            path = Path(tempfile.gettempdir()) / "qiyuan_audio"
            path.mkdir(parents=True, exist_ok=True)
        self.temp_dir = path
        self._client = None
        self._node = None
        self._lock = threading.Lock()

    def _ensure(self) -> bool:
        with self._lock:
            if self._client is not None:
                return True
            try:
                import rclpy
                from rclpy.node import Node
                from aimdk_msgs.srv import PlayAudioFile
                from aimdk_msgs.msg import AudioFile, CommonRequest

                if not rclpy.ok():
                    rclpy.init(args=["--ros-args", "--log-level", "warn"])
                node = Node("qiyuan_audio_player")
                client = node.create_client(PlayAudioFile, SERVICE_NAME)
                threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
                if not client.wait_for_service(timeout_sec=SERVICE_TIMEOUT_S):
                    print(f"[robot_audio] {SERVICE_NAME} not available; "
                          f"audio playback skipped", flush=True)
                    return False
                self._node = node
                self._client = client
                self._svc = PlayAudioFile
                self._AudioFile = AudioFile
                self._CommonRequest = CommonRequest
                return True
            except Exception as exc:
                print(f"[robot_audio] ROS unavailable ({type(exc).__name__}); "
                      f"audio playback skipped", flush=True)
                return False

    def play_file(self, audio_path: str | Path) -> bool:
        """Play a local audio file on the robot speaker. Returns True on success."""
        if os.environ.get("AUDIO_PLAYBACK", "off") != "playaudiofile":
            return False
        path = Path(audio_path)
        if not path.is_file():
            return False
        if not self._ensure():
            return False
        try:
            req = self._svc.Request()
            req.request = self._CommonRequest()
            req.file = self._AudioFile()
            req.file.pkg_name = "qiyuan-demo"
            req.file.file_name = path.name
            req.file.file_path = str(path)
            req.file.priority = 6
            req.file.media_role = MEDIA_ROLE_COMMUNICATION
            req.file.info.channels = 1
            req.file.info.sample_rate = 16000
            req.file.info.coding_format = "wave"
            future = self._client.call_async(req)
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                if future.done():
                    resp = future.result()
                    return resp.response.header.code == 0
                time.sleep(0.05)
            print("[robot_audio] PlayAudioFile call timed out", flush=True)
            return False
        except Exception as exc:
            print(f"[robot_audio] play failed ({type(exc).__name__}); continuing", flush=True)
            return False

    def play_audio_bytes(self, audio: bytes, name: str = "reply.wav") -> bool:
        """Save audio bytes (WAV from AIChain, mp3 from BytePlus) and play them."""
        path = self.temp_dir / f"reply_{int(time.time() * 1000)}{Path(name).suffix or '.wav'}"
        path.write_bytes(audio)
        return self.play_file(path)


_player: RobotAudioPlayer | None = None


def get_player() -> RobotAudioPlayer:
    global _player
    if _player is None:
        _player = RobotAudioPlayer()
    return _player


def play_text(text: str) -> bool:
    """Generate the Cantonese audio for `text` and play it on the robot."""
    try:
        from conversation.config import ConversationConfig
        from conversation.engine import ConversationEngine

        audio = ConversationEngine(ConversationConfig()).speak(text)
        suffix = ".wav" if audio[:4] == b"RIFF" else ".mp3"
        return get_player().play_audio_bytes(audio, f"reply{suffix}")
    except Exception as exc:
        print(f"[robot_audio] play_text failed ({type(exc).__name__}); continuing", flush=True)
        return False
