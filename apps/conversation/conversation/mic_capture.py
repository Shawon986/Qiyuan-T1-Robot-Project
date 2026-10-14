"""Robot microphone capture via PulseAudio (official 接口说明.md §2.2.1.6).

The robot mic is an 8-channel 48 kHz S16LE PulseAudio source
(``alsa_input.platform-aw89403_sound.pro-input-0``): ch1-2 are playback
loopback, ch3-8 are mics, and ch5-6 are the main pickup channels. The official
``record_audio.py`` example extracts ch5-6, mixes them to mono and amplifies
x10 (its ``mic_mono.wav`` output) — we do the same, then resample to the ASR
rate (16 kHz for the AIChain STT leg).

On the robot itself the PulseAudio unix socket is used (shared memory, no
module loading). From a PC, TCP :4713 is used — ``module-native-protocol-tcp``
must be loaded on the robot first; the official ``record_audio.py`` example
loads it automatically over SSH (running it once is enough).

Pure stdlib: channel math is testable on the PC without any robot hardware.
"""
from __future__ import annotations

import array
import os
import shutil
import subprocess
import time
import wave
from pathlib import Path

MIC_DEVICE = "alsa_input.platform-aw89403_sound.pro-input-0"
MIC_RATE = 48000
MIC_CHANNELS = 8
TCP_PORT = 4713
SOC_INDEX_FILE = "/robot/data/info/soc_index"


def is_robot_board() -> bool:
    """True when running on the robot itself (the official board marker file)."""
    try:
        return Path(SOC_INDEX_FILE).is_file()
    except OSError:
        return False


def pulse_server() -> str:
    """Resolve the PulseAudio endpoint: MIC_PULSE_SERVER > on-robot unix
    socket > TCP to CAMERA_ROBOT_IP (the PC-side convention)."""
    env = os.environ.get("MIC_PULSE_SERVER", "").strip()
    if env:
        return env
    if is_robot_board():
        return "unix:/run/user/1000/pulse/native"
    ip = os.environ.get("CAMERA_ROBOT_IP", "").strip()
    if ip:
        return f"tcp:{ip}:{TCP_PORT}"
    raise RuntimeError(
        "no PulseAudio endpoint known: set MIC_PULSE_SERVER "
        "(e.g. tcp:<robot-ip>:4713 or unix:/run/user/1000/pulse/native) or "
        "CAMERA_ROBOT_IP")


def extract_mic_mono(pcm_8ch: bytes, gain: float = 10.0) -> bytes:
    """ch5-6 of the 8ch/48kHz stream, averaged and amplified, as mono S16LE.

    Mirrors the official record_audio.py mic_mono.wav processing.
    """
    if len(pcm_8ch) % (MIC_CHANNELS * 2):
        raise ValueError(
            f"8-channel PCM16 length must be a multiple of {MIC_CHANNELS * 2} bytes")
    src = array.array("h", pcm_8ch)
    out = array.array("h")
    out_append = out.append
    for frame in range(0, len(src), MIC_CHANNELS):
        value = int((src[frame + 4] + src[frame + 5]) / 2 * gain)
        out_append(max(-32768, min(32767, value)))
    return out.tobytes()


def decimate_mono(pcm: bytes, in_rate: int, out_rate: int) -> bytes:
    """Naive decimation for exact integer ratios (48k -> 16k = every 3rd sample)."""
    if in_rate % out_rate:
        raise ValueError("only exact-integer decimation supported; use ffmpeg")
    step = in_rate // out_rate
    return array.array("h", pcm)[::step].tobytes()


def write_mono_wav(path: Path, pcm: bytes, rate: int) -> Path:
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        out.writeframes(pcm)
    return path


def capture(duration_s: float, out_path: Path, out_rate: int = 16000,
            gain: float = 10.0, device: str | None = None) -> Path:
    """Record `duration_s` from the robot mic; write a mono WAV at `out_rate`.

    Raises RuntimeError with an actionable message on failure — callers stay
    graceful, the conversation never breaks.
    """
    server = pulse_server()
    if shutil.which("parec") is None:
        raise RuntimeError("parec not found — install pulseaudio-utils")
    cmd = ["parec", "--channels", str(MIC_CHANNELS), "--rate", str(MIC_RATE),
           "--format", "s16le", "--device", device or MIC_DEVICE]
    env = dict(os.environ, PULSE_SERVER=server)
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    time.sleep(duration_s)
    proc.terminate()
    try:
        raw, err = proc.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        raw, err = proc.communicate()
    if len(raw) < MIC_RATE * MIC_CHANNELS * 2:  # less than 1 s of audio
        detail = err.decode(errors="replace").strip()[:300]
        raise RuntimeError(
            f"mic capture returned no audio from {server}. {detail} "
            "TCP mode needs module-native-protocol-tcp loaded on the robot "
            "(run the official record_audio.py example once, or capture on "
            "the robot itself)")
    mono = extract_mic_mono(raw, gain)
    if out_rate == MIC_RATE:
        return write_mono_wav(out_path, mono, out_rate)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        tmp48 = out_path.with_name(out_path.stem + "_48k.wav")
        write_mono_wav(tmp48, mono, MIC_RATE)
        try:
            subprocess.run([ffmpeg, "-y", "-i", str(tmp48), "-ar", str(out_rate),
                            str(out_path)], check=True, timeout=60,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return out_path
        finally:
            tmp48.unlink(missing_ok=True)
    return write_mono_wav(out_path, decimate_mono(mono, MIC_RATE, out_rate), out_rate)
