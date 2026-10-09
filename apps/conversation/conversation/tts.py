"""iFlytek TTS (在线语音合成) — returns a WAV file (PCM16 16 kHz)."""
from __future__ import annotations

import base64
import json
import struct
import threading

import websocket  # websocket-client

from .config import ConversationConfig
from .iflytek_auth import build_ws_url

TTS_HOST = "tts-api.xfyun.cn"
TTS_PATH = "/v2/tts"
SAMPLE_RATE = 16000


class TtsError(RuntimeError):
    pass


def wrap_wav(pcm: bytes, sample_rate: int = SAMPLE_RATE, channels: int = 1) -> bytes:
    """Wrap raw PCM16LE into a standard WAV file."""
    header = (
        b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, channels, sample_rate,
                      sample_rate * 2 * channels, 2 * channels, 16)
        + b"data" + struct.pack("<I", len(pcm))
    )
    return header + pcm


class IflytekTTS:
    def __init__(self, cfg: ConversationConfig | None = None) -> None:
        self.cfg = cfg or ConversationConfig()
        if not (self.cfg.iflytek_appid and self.cfg.iflytek_api_key
                and self.cfg.iflytek_api_secret):
            raise TtsError("iFlytek credentials not configured (check .env)")

    def synthesize(self, text: str, timeout: float = 30.0) -> bytes:
        """Returns WAV bytes for the given text."""
        chunks: list[bytes] = []
        done = threading.Event()
        error: list[str] = []

        def on_open(ws):
            body = {
                "common": {"app_id": self.cfg.iflytek_appid},
                "business": {
                    "aue": "raw",
                    "auf": f"audio/L16;rate={SAMPLE_RATE}",
                    "vcn": self.cfg.tts_voice,
                    "tte": "UTF8",
                    "speed": 50,
                    "volume": 50,
                    "pitch": 50,
                },
                "data": {
                    "status": 2,
                    "text": base64.b64encode(text.encode("utf-8")).decode(),
                },
            }
            ws.send(json.dumps(body))

        def on_message(ws, message):
            msg = json.loads(message)
            audio = (msg.get("data") or {}).get("audio")
            if audio:
                chunks.append(base64.b64decode(audio))
            if (msg.get("data") or {}).get("status") == 2:
                done.set()

        def on_error(ws, exc):
            error.append(str(exc))
            done.set()

        def on_close(ws, *args):
            done.set()

        ws = websocket.WebSocketApp(
            build_ws_url(self.cfg.iflytek_api_key, self.cfg.iflytek_api_secret, TTS_HOST, TTS_PATH),
            on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close,
        )
        runner = threading.Thread(target=ws.run_forever, daemon=True)
        runner.start()
        if not done.wait(timeout=timeout):
            ws.close()
            raise TtsError("TTS timeout")
        ws.close()
        if error:
            raise TtsError(f"TTS websocket error: {error[0]}")
        pcm = b"".join(chunks)
        if not pcm:
            raise TtsError("TTS returned no audio")
        return wrap_wav(pcm)
