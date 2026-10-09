"""iFlytek IAT (语音听写流式版) ASR client — Cantonese via accent=cantonese.

Blocking websocket implementation (create_connection) - no threading races.
"""
from __future__ import annotations

import json
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
        url = build_ws_url(self.cfg.iflytek_api_key, self.cfg.iflytek_api_secret,
                           IAT_HOST, IAT_PATH)
        ws = websocket.create_connection(url, timeout=timeout)
        pieces: list[str] = []
        try:
            for frame in frames:
                ws.send(json.dumps(frame))
            while True:
                raw = ws.recv()
                if not raw:
                    break
                msg = json.loads(raw)
                if msg.get("code", 0) != 0:
                    raise AsrError(f"ASR error {msg.get('code')}: {msg.get('message')}")
                text = parse_iat_result(msg)
                if text:
                    pieces.append(text)
                if (msg.get("data") or {}).get("status") == 2:
                    break
        finally:
            ws.close()
        return "".join(pieces)
