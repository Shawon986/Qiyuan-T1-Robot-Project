"""iFlytek IAT (语音听写流式版) ASR client — Cantonese via accent=cantonese."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import websocket  # websocket-client

from .config import ConversationConfig
from .iflytek_auth import build_iat_frames, build_ws_url, parse_iat_result

IAT_HOST = "iat-api.xfyun.cn"
IAT_PATH = "/v2/iat"
SAMPLE_RATE = 16000


class AsrError(RuntimeError):
    pass


def read_pcm_chunks(audio_path: str | Path, chunk_ms: int = 100,
                    sample_rate: int = SAMPLE_RATE) -> list[bytes]:
    """Read a PCM16LE file (or standard PCM WAV) into ~100 ms chunks."""
    data = Path(audio_path).read_bytes()
    if data[:4] == b"RIFF":
        data = data[44:]  # skip the standard 44-byte WAV header
    chunk_size = sample_rate * 2 * chunk_ms // 1000
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)] if data else []


class IflytekASR:
    def __init__(self, cfg: ConversationConfig | None = None) -> None:
        self.cfg = cfg or ConversationConfig()
        if not (self.cfg.iflytek_appid and self.cfg.iflytek_api_key
                and self.cfg.iflytek_api_secret):
            raise AsrError("iFlytek credentials not configured (check .env)")

    def transcribe_file(self, audio_path: str | Path, timeout: float = 30.0) -> str:
        chunks = read_pcm_chunks(audio_path)
        if not chunks:
            raise AsrError(f"no audio data in {audio_path}")
        frames = build_iat_frames(chunks, self.cfg.iflytek_appid, self.cfg.asr_accent)
        pieces: list[str] = []
        done = threading.Event()
        error: list[str] = []

        def on_open(ws):
            for frame in frames:
                ws.send(json.dumps(frame))

        def on_message(ws, message):
            msg = json.loads(message)
            text = parse_iat_result(msg)
            if text:
                pieces.append(text)
            if (msg.get("data") or {}).get("status") == 2:
                done.set()

        def on_error(ws, exc):
            error.append(str(exc))
            done.set()

        def on_close(ws, *args):
            done.set()

        ws = websocket.WebSocketApp(
            build_ws_url(self.cfg.iflytek_api_key, self.cfg.iflytek_api_secret, IAT_HOST, IAT_PATH),
            on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close,
        )
        runner = threading.Thread(target=ws.run_forever, daemon=True)
        runner.start()
        if not done.wait(timeout=timeout):
            ws.close()
            raise AsrError("ASR timeout")
        ws.close()
        if error:
            raise AsrError(f"ASR websocket error: {error[0]}")
        return "".join(pieces)
