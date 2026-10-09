"""iFlytek TTS (在线语音合成) — returns a WAV file (PCM16 16 kHz).

Blocking websocket implementation (create_connection) - no threading races.
"""
from __future__ import annotations

import base64
import json
import struct

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
        url = build_ws_url(self.cfg.iflytek_api_key, self.cfg.iflytek_api_secret,
                           TTS_HOST, TTS_PATH)
        ws = websocket.create_connection(url, timeout=timeout)
        chunks: list[bytes] = []
        try:
            ws.send(json.dumps(body))
            while True:
                raw = ws.recv()
                if not raw:
                    break
                msg = json.loads(raw)
                if msg.get("code", 0) != 0:
                    raise TtsError(f"TTS error {msg.get('code')}: {msg.get('message')}")
                audio = (msg.get("data") or {}).get("audio")
                if audio:
                    chunks.append(base64.b64decode(audio))
                if (msg.get("data") or {}).get("status") == 2:
                    break
        finally:
            ws.close()
        pcm = b"".join(chunks)
        if not pcm:
            raise TtsError("TTS returned no audio")
        return wrap_wav(pcm)
