"""CLI for the conversation pipeline (PC testing without the robot).

  conversation --say "你好"          one text turn: LLM reply + TTS file saved
  conversation --asr clip.wav        transcribe a PCM/WAV file (Cantonese)
  conversation --full clip.wav       ASR -> LLM -> TTS -> play (if paplay exists)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import ConversationConfig
from .engine import ConversationEngine


def _play(wav_bytes: bytes) -> str:
    """Play via PulseAudio if available; otherwise save the file and say where."""
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
            print(_play(engine.speak(reply)))
        elif ns.asr:
            print("transcript:", engine.transcribe_file(ns.asr))
        elif ns.full:
            text = engine.transcribe_file(ns.full)
            print("user:", text)
            reply = engine.handle_user_text(text)
            print("robot:", reply)
            print(_play(engine.speak(reply)))
        else:
            ap.print_help()
            return 2
        return 0
    except Exception as exc:  # fail-closed: report, don't crash the demo
        print(f"conversation error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
