"""CLI for the conversation pipeline (PC testing without the robot).

  conversation --say "你好"          one text turn: LLM reply + TTS file saved
  conversation --asr clip.wav        transcribe a PCM/WAV file (Cantonese)
  conversation --full clip.wav       ASR -> LLM -> TTS -> play (if paplay exists)
  conversation --mic 6               capture 6 s from the robot/PC mic, then
                                     ASR -> LLM -> TTS -> play (one robot turn)
  conversation --listen              continuous robot loop: capture -> ASR ->
                                     LLM -> TTS -> play -> re-arm (see _listen)
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

from .config import ConversationConfig
from .engine import ConversationEngine


def _audio_seconds(audio: bytes) -> float | None:
    """WAV duration from bytes; None for mp3/unknown formats."""
    if audio[:4] == b"RIFF":
        try:
            with wave.open(io.BytesIO(audio), "rb") as w:
                return w.getnframes() / w.getframerate()
        except Exception:
            return None
    return None


def _wait_reply_finished(audio: bytes) -> None:
    """Wait for the reply to finish + a quiet margin, so the next capture
    window never contains our own voice (the mic picks up the speaker
    acoustically even though the ch1-2 loopback channels are excluded)."""
    margin = 1.5
    time.sleep((_audio_seconds(audio) or 8.0) + margin)


def _listen(engine: ConversationEngine, window: float, idle: float = 0.8) -> None:
    """Continuous on-robot voice loop. Safe by construction: replies only when
    a wake word is in the transcript, and never captures while the robot is
    speaking. Ctrl+C stops."""
    from .mic_capture import capture

    print(f"[listen] capture {window:.0f}s windows; wake words "
          f"{engine.cfg.wake_words}; Ctrl+C to stop", flush=True)
    while True:
        try:
            with tempfile.TemporaryDirectory() as td:
                clip = Path(td) / "mic.wav"
                capture(window, clip)
                text = engine.transcribe_file(str(clip))
        except Exception as exc:
            print(f"[listen] capture/ASR failed ({type(exc).__name__}); "
                  f"retrying in {idle:.0f}s", flush=True)
            time.sleep(idle)
            continue
        if not text.strip():
            time.sleep(idle)
            continue
        print("user:", text, flush=True)
        reply = engine.handle_user_text(text)
        if not reply:
            time.sleep(idle)
            continue
        print("robot:", reply, flush=True)
        audio = engine.speak(reply)
        print(_play(reply, audio), flush=True)
        _wait_reply_finished(audio)


def _play(text: str, wav_bytes: bytes) -> str:
    """On the robot (AUDIO_PLAYBACK=playaudiofile): speak via PlayAudioFile.
    Else play via paplay; otherwise save the file and say where."""
    if os.environ.get("AUDIO_PLAYBACK", "off") == "playaudiofile":
        try:
            from demo_ui.robot_audio import play_text  # type: ignore
            if play_text(text):
                return "played via PlayAudioFile (robot speaker)"
        except Exception:
            pass
    tmp = Path(tempfile.gettempdir()) / "qiyuan_reply.wav"
    tmp.write_bytes(wav_bytes)
    try:
        subprocess.run(["paplay", str(tmp)], check=True, timeout=30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"played via paplay ({tmp})"
    except Exception:
        return f"audio saved to {tmp} (paplay not available in this environment)"


def main(args: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="conversation")
    ap.add_argument("--say", help="one text turn (robot replies via LLM + TTS)")
    ap.add_argument("--asr", help="transcribe a PCM/WAV audio file")
    ap.add_argument("--full", help="audio file -> ASR -> LLM -> TTS -> play")
    ap.add_argument("--mic", type=float, metavar="SECONDS",
                    help="capture N seconds from the robot/PC mic, then "
                         "ASR -> LLM -> TTS -> play (the on-robot loop)")
    ap.add_argument("--listen", action="store_true",
                    help="continuous robot loop: capture -> ASR -> LLM -> "
                         "TTS -> play -> re-arm (Ctrl+C stops)")
    ap.add_argument("--window", type=float, default=8.0,
                    help="capture window seconds for --listen (default 8)")
    ns = ap.parse_args(args)

    cfg = ConversationConfig()
    if not cfg.ready():
        print("Missing credentials in .env: IFLYTEK_APPID/API_KEY/API_SECRET and DASHSCOPE_API_KEY",
              file=sys.stderr)
        return 1

    engine = ConversationEngine(cfg)
    try:
        if ns.say:
            reply = engine.handle_user_text(ns.say)
            if not reply:
                print("(no wake word matched; try starting with 机器人)")
                return 0
            print("robot:", reply)
            print(_play(reply, engine.speak(reply)))
        elif ns.asr:
            print("transcript:", engine.transcribe_file(ns.asr))
        elif ns.full:
            text = engine.transcribe_file(ns.full)
            print("user:", text)
            reply = engine.handle_user_text(text)
            print("robot:", reply)
            print(_play(reply, engine.speak(reply)))
        elif ns.mic:
            from .mic_capture import capture
            with tempfile.TemporaryDirectory() as td:
                clip = Path(td) / "mic.wav"
                capture(ns.mic, clip)
                text = engine.transcribe_file(str(clip))
                print("user:", text)
                reply = engine.handle_user_text(text)
                if not reply:
                    print("(no wake word matched)")
                    return 0
                print("robot:", reply)
                print(_play(reply, engine.speak(reply)))
        elif ns.listen:
            try:
                _listen(engine, ns.window)
            except KeyboardInterrupt:
                print("\n[listen] stopped", flush=True)
            return 0
        else:
            ap.print_help()
            return 2
        return 0
    except Exception as exc:  # fail-closed: report, don't crash the demo
        print(f"conversation error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
