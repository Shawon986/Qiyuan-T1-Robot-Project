"""Robot speaker playback via the OFFICIAL PlayAudioFile service.

Why this exists: the platform cloud TTS (primebot.cn) is Mandarin-only and
overwrites local voice configuration within 5 s of connection. We never use
that service — our Cantonese audio (AIChain voice 94 / BytePlus) is generated
with our own API keys, saved to a temp file, and played through
`PlayAudioFile`, which is a LOCAL FILE playback interface: no voice, no
language, no tone settings for the cloud to overwrite.

Protocol (接口说明.md §2.2.1.3), cross-checked against the developer's
on-robot framework (PrimeBuddy, 2026-10-14):

- `file_path` is the DIRECTORY and `file_name` the filename (the official
  Python example plays `file_path:=/robot/software/aimrt_agent/bin/cfg/t1/audio`
  with `file_name:=小星星.wav`).
- The audio service runs on SoC 0 (MC board, default 10.1.1.100) and reads
  files from SoC 0's own disk. Our app runs on SoC 1 (brain board), so the
  file is scp'd to a task-exclusive temp dir on SoC 0 first (inter-board SSH,
  user `run`), played, then cleaned up.
- The official example plays 24 kHz mono PCM16 WAV; our TTS legs output
  16 kHz PCM (AIChain) or mp3 (BytePlus), so files are converted with ffmpeg
  before playback (gracefully skipped if ffmpeg is missing).
- Success = header.code == 0 OR status == SUCCESS (the official example treats
  either as accepted).
- Playback is verified via /aima/hal/audio/play_state events (start within
  8 s, natural end within duration + 12 s). Verification failures are
  warnings, never crashes.

Fully graceful: when ROS, the service, ffmpeg or the inter-board SSH is
unavailable (e.g. on the dev PC), playback is skipped and the conversation
never breaks.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import threading
import time
import wave
from pathlib import Path

SERVICE_NAME = "/aimdk_5Fmsgs/srv/PlayAudioFile"
PLAY_STATE_TOPIC = "/aima/hal/audio/play_state"
MEDIA_ROLE_COMMUNICATION = "Communication"
SERVICE_TIMEOUT_S = 3.0
ROBOT_SAMPLE_RATE = 24000
SOC0_DEFAULT_HOST = "10.1.1.100"
SOC0_DEFAULT_USER = "run"
SOC_INDEX_FILE = "/robot/data/info/soc_index"


def is_robot_board() -> bool:
    """True when running on the robot itself (the official board marker file)."""
    try:
        return Path(SOC_INDEX_FILE).is_file()
    except OSError:
        return False


def upload_enabled() -> bool:
    """Whether to scp audio to SoC 0. ROBOT_AUDIO_UPLOAD=on/off overrides; auto = on the robot."""
    mode = os.environ.get("ROBOT_AUDIO_UPLOAD", "auto").strip().lower()
    if mode in ("0", "off", "false", "no"):
        return False
    if mode in ("1", "on", "true", "yes"):
        return True
    return is_robot_board()


def ssh_target() -> str:
    user = os.environ.get("ROBOT_SSH_USER", "").strip() or SOC0_DEFAULT_USER
    host = os.environ.get("ROBOT_SSH_HOST", "").strip() or SOC0_DEFAULT_HOST
    return f"{user}@{host}"


def _ssh_flags() -> list[str]:
    flags = ["-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=accept-new"]
    key = os.environ.get("ROBOT_SSH_KEY", "").strip()
    if key:
        flags += ["-i", key]
    return flags


def remote_cmd(base: str, *args: str) -> list[str]:
    """ssh/scp command list, sshpass-prefixed when ROBOT_SSH_PASSWORD is set."""
    password = os.environ.get("ROBOT_SSH_PASSWORD", "")
    sshpass = shutil.which("sshpass") if password else None
    cmd = [base, *_ssh_flags()]
    if sshpass:
        cmd = [sshpass, "-p", password, *cmd]
    return [*cmd, *args]


def wav_params(path: Path) -> dict | None:
    try:
        with wave.open(str(path), "rb") as w:
            return {"channels": w.getnchannels(), "sampwidth": w.getsampwidth(),
                    "framerate": w.getframerate(), "frames": w.getnframes()}
    except (wave.Error, EOFError, OSError):
        return None


def wav_duration(path: Path) -> float | None:
    params = wav_params(path)
    if params is None:
        return None
    return params["frames"] / params["framerate"]


def needs_conversion(path: Path) -> bool:
    """True unless the file already is a 24 kHz mono PCM16 WAV (the robot format)."""
    params = wav_params(path)
    if params is None:
        return True  # mp3 or any non-WAV: always convert
    return not (params["channels"] == 1 and params["sampwidth"] == 2
                and params["framerate"] == ROBOT_SAMPLE_RATE)


def convert_to_robot_wav(src: Path) -> Path:
    """Return a 24 kHz mono PCM16 WAV (new file next to src, or src if conversion fails)."""
    if not needs_conversion(src):
        return src
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("[robot_audio] ffmpeg not found; playing the original format "
              "(the robot expects 24 kHz mono WAV)", flush=True)
        return src
    dst = src.with_name(src.stem + "_24k.wav")
    try:
        subprocess.run([ffmpeg, "-y", "-i", str(src), "-ac", "1",
                        "-ar", str(ROBOT_SAMPLE_RATE), "-sample_fmt", "s16",
                        str(dst)], check=True, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return dst
    except Exception as exc:
        print(f"[robot_audio] ffmpeg conversion failed ({type(exc).__name__}); "
              f"trying the original file", flush=True)
        return src


def build_play_request(path: str) -> dict:
    """Official PlayAudioFile field layout (接口说明.md §2.2.1.3 + Python example)."""
    p = Path(path)
    params = wav_params(p)
    if params is None:
        channels, sampwidth, framerate, size = 1, 2, ROBOT_SAMPLE_RATE, 0
    else:
        channels, sampwidth, framerate = (params["channels"], params["sampwidth"],
                                          params["framerate"])
        size = params["frames"] * sampwidth
    return {
        "pkg_name": "qiyuan-demo",
        "file_name": p.name,
        "file_path": str(p.parent),  # DIRECTORY, not the full path
        "info": {
            "channels": channels,
            "sample_rate": framerate,
            "size": size,
            "sample_format": "S16_LE",
            "coding_format": "wave",
        },
        "priority": 6,
        "priority_weight": 0,
        "media_role": MEDIA_ROLE_COMMUNICATION,
    }


def request_accepted(resp) -> bool:
    """Official example: code == 0 OR status == SUCCESS counts as accepted."""
    try:
        common = resp.response
        if int(common.header.code) == 0:
            return True
        return int(common.status.value) == 1  # CommonState.SUCCESS
    except Exception:
        return False


def describe_rejection(resp) -> str:
    try:
        common = resp.response
        return (f"code={common.header.code} status={common.status.value} "
                f"msg={common.message!r}")
    except Exception:
        return "unknown"


def upload_to_soc0(local: Path) -> str | None:
    """scp the WAV to a task-exclusive temp dir on SoC 0 (where the audio
    service reads files). Returns the SoC 0 path, or None to play the local
    path instead (graceful fallback)."""
    target = ssh_target()
    try:
        mk = subprocess.run(remote_cmd("ssh", target, "mktemp -d /tmp/qiyuan-demo.XXXXXXXX"),
                            capture_output=True, text=True, timeout=15, check=True)
    except Exception as exc:
        print(f"[robot_audio] inter-board SSH failed ({type(exc).__name__}); "
              f"playing the local path (may fail: the audio service reads SoC 0 disk)",
              flush=True)
        return None
    remote_dir = mk.stdout.strip()
    if not remote_dir.startswith("/tmp/qiyuan-demo."):
        print("[robot_audio] unexpected remote temp dir; using the local path", flush=True)
        return None
    remote_file = f"{remote_dir}/reply.wav"
    try:
        subprocess.run(remote_cmd("scp", str(local), f"{target}:{remote_file}"),
                       check=True, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return remote_file
    except Exception as exc:
        print(f"[robot_audio] scp to SoC 0 failed ({type(exc).__name__}); "
              f"using the local path", flush=True)
        return None


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
        self._play_events: list[tuple[float, str, int]] = []
        self._events_lock = threading.Lock()

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
                # Best-effort playback feedback (start/end events); only used
                # for warnings — a missing message type must not break playback.
                try:
                    from aimdk_msgs.msg import PlayStateChange
                    node.create_subscription(PlayStateChange, PLAY_STATE_TOPIC,
                                             self._on_play_state, 50)
                except Exception:
                    pass
                return True
            except Exception as exc:
                print(f"[robot_audio] ROS unavailable ({type(exc).__name__}); "
                      f"audio playback skipped", flush=True)
                return False

    def _on_play_state(self, msg) -> None:
        try:
            with self._events_lock:
                self._play_events.append((time.monotonic(),
                                          str(getattr(msg, "pkg_name", "")),
                                          int(msg.state.value)))
                self._play_events = self._play_events[-200:]
        except Exception:
            pass

    def _own_events(self, pkg_name: str) -> list[tuple[float, str, int]]:
        with self._events_lock:
            return [e for e in self._play_events if e[1] == pkg_name]

    def _wait_for_quiet(self, timeout_s: float = 8.0) -> bool:
        """Wait until no other audio is playing before submitting ours.

        The robot's own agent plays wake/status prompts ("我在" + ding) — this
        gives them a moment to finish so our reply doesn't overlap. Same
        pattern as the developer's framework. No state feed (dev PC) -> pass.
        """
        if self._node is None:
            return True
        discover_until = time.monotonic() + 1.0
        deadline = time.monotonic() + timeout_s
        while True:
            with self._events_lock:
                latest = {pkg: state for _, pkg, state in self._play_events}
            now = time.monotonic()
            if now >= discover_until and not any(s == 1 for s in latest.values()):
                return True
            if now >= deadline:
                print(f"[robot_audio] warning: other audio still playing after "
                      f"{timeout_s:.0f}s; submitting anyway", flush=True)
                return False
            time.sleep(0.2)

    def _schedule_aftermath(self, play_src: Path, src: Path, remote: str | None) -> None:
        """Background thread: verify playback (warnings only), then clean up."""
        pkg_name = "qiyuan-demo"
        duration = wav_duration(play_src)

        def task() -> None:
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    own = self._own_events(pkg_name)
                    if own and own[-1][2] == 1:  # started
                        break
                    time.sleep(0.2)
                else:
                    print("[robot_audio] warning: no playback start event "
                          "(did our audio actually play?)", flush=True)
                if duration is not None:
                    end_deadline = time.monotonic() + duration + 12
                    while time.monotonic() < end_deadline:
                        own = self._own_events(pkg_name)
                        if own and own[-1][2] in (0, 2):  # natural end
                            break
                        time.sleep(0.2)
                    else:
                        print("[robot_audio] warning: no natural end event "
                              "(audio may have been cut off)", flush=True)
                else:
                    time.sleep(15)
            except Exception:
                pass
            if remote:
                try:
                    subprocess.run(remote_cmd("ssh", ssh_target(),
                        "rm -f " + shlex.quote(remote) + " && rmdir "
                        + shlex.quote(str(Path(remote).parent))),
                        timeout=20, check=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass  # cleanup is best-effort; leftover /tmp dirs are harmless
            if play_src != src:
                try:
                    play_src.unlink(missing_ok=True)
                except OSError:
                    pass

        if remote is None and duration is None and play_src == src:
            return  # nothing to verify or clean up (e.g. unit tests)
        threading.Thread(target=task, daemon=True).start()

    def play_file(self, audio_path: str | Path) -> bool:
        """Play a local audio file on the robot speaker. Returns True on success."""
        if os.environ.get("AUDIO_PLAYBACK", "off") != "playaudiofile":
            return False
        src = Path(audio_path)
        if not src.is_file():
            return False
        if not self._ensure():
            return False
        play_src = convert_to_robot_wav(src)
        remote = upload_to_soc0(play_src) if upload_enabled() else None
        request_path = remote if remote is not None else str(play_src)
        # give the robot's own wake/status prompts a moment to finish first
        self._wait_for_quiet()
        try:
            fields = build_play_request(request_path)
            req = self._svc.Request()
            req.request = self._CommonRequest()
            if self._node is not None:
                req.request.header.stamp = self._node.get_clock().now().to_msg()
            req.file = self._AudioFile()
            info = fields.pop("info")
            for key, value in fields.items():
                if hasattr(req.file, key):
                    setattr(req.file, key, value)
            if hasattr(req.file, "info"):
                for key, value in info.items():
                    if hasattr(req.file.info, key):
                        setattr(req.file.info, key, value)
            future = self._client.call_async(req)
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                if future.done():
                    resp = future.result()
                    if not request_accepted(resp):
                        print(f"[robot_audio] PlayAudioFile rejected "
                              f"({describe_rejection(resp)})", flush=True)
                        return False
                    self._schedule_aftermath(play_src, src, remote)
                    return True
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
