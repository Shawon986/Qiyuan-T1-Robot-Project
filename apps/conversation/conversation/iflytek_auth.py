"""iFlytek WebAPI authentication (HMAC-SHA256 signature scheme).

Used by both IAT (ASR) and TTS WebSocket endpoints. Pure functions, offline-testable.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse
from datetime import datetime, timezone
from email.utils import format_datetime


def build_authorization(api_key: str, api_secret: str, host: str, path: str) -> str:
    """Return the `authorization` header value for an iFlytek WebSocket API."""
    date = format_datetime(datetime.now(timezone.utc), usegmt=True)
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    digest = hmac.new(api_secret.encode(), signature_origin.encode(), hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode()
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    return base64.b64encode(authorization_origin.encode()).decode()


def build_ws_url(api_key: str, api_secret: str, host: str, path: str) -> str:
    """Return the full wss:// URL with authorization and date query params."""
    date = format_datetime(datetime.now(timezone.utc), usegmt=True)
    auth = build_authorization(api_key, api_secret, host, path)
    params = urllib.parse.urlencode(
        {"authorization": auth, "date": date, "host": host}
    )
    return f"wss://{host}{path}?{params}"


def build_iat_frames(audio_chunks: list[bytes], appid: str, accent: str = "cantonese",
                     sample_rate: int = 16000) -> list[dict]:
    """Build the ordered JSON frame list for the IAT streaming protocol.

    status: 0 = first frame, 1 = middle, 2 = last (ends the stream).
    """
    frames: list[dict] = []
    total = len(audio_chunks)
    for i, chunk in enumerate(audio_chunks):
        status = 2 if i == total - 1 else (0 if i == 0 else 1)
        frames.append({
            "common": {"app_id": appid},
            "business": {
                "language": "zh_cn",
                "domain": "iat",
                "accent": accent,
                "vad_eos": 3000,
                "dwa": "wpgs",
            },
            "data": {
                "status": status,
                "format": f"audio/L16;rate={sample_rate}",
                "encoding": "raw",
                "audio": base64.b64encode(chunk).decode(),
            },
        })
    return frames


def parse_iat_result(message: dict) -> str | None:
    """Extract the recognized text from one IAT ws result message (dwa=wpgs format)."""
    data = message.get("data") or {}
    result = data.get("result") or {}
    text = result.get("ws") or []
    return "".join((w.get("cw") or [{}])[0].get("w", "") for w in text) or None
