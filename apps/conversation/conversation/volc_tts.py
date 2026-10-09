"""BytePlus/Volcengine TTS (seed-tts) — Cantonese voice leg.

Unidirectional HTTP API, streaming NDJSON response (one JSON per line,
base64_resp = mp3 chunks). Validated live 2026-10-09 with speaker
zh_female_yueyunv_mars_bigtts (温柔粤语) and resource seed-tts-1.0.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from .config import ConversationConfig

DEFAULT_RESOURCE = "seed-tts-1.0"


class VolcTtsError(RuntimeError):
    pass


def parse_ndjson_response(raw: str) -> tuple[bytes, list[str]]:
    """Parse the streaming NDJSON response into mp3 bytes + error list.

    Pure function (offline-testable). Success codes: 0 or 20000000.
    """
    chunks: list[bytes] = []
    errors: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        code = obj.get("code", 0)
        if code not in (0, 20000000):
            errors.append(f"{code}: {obj.get('message')}")
            continue
        b64 = obj.get("base64_resp") or obj.get("data")
        if b64:
            chunks.append(base64.b64decode(b64))
    return b"".join(chunks), errors


class VolcTTS:
    def __init__(self, cfg: ConversationConfig | None = None) -> None:
        self.cfg = cfg or ConversationConfig()
        self.api_key = self.cfg.volc_tts_api_key
        self.endpoint = self.cfg.volc_tts_endpoint
        self.speaker = self.cfg.volc_tts_speaker
        self.resource_id = self.cfg.volc_tts_resource_id or DEFAULT_RESOURCE
        if not self.api_key:
            raise VolcTtsError("VOLC_TTS_API_KEY is not configured")

    def synthesize(self, text: str, timeout: float = 120.0) -> bytes:
        """Returns mp3 bytes for the given Cantonese text."""
        body = {
            "req_params": {
                "text": text,
                "speaker": self.speaker,
                "additions": json.dumps({
                    "disable_markdown_filter": True,
                    "enable_language_detector": True,
                }),
                "audio_params": {"format": "mp3", "sample_rate": 24000},
            }
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "x-api-key": self.api_key,
                "X-Api-Resource-Id": self.resource_id,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise VolcTtsError(f"TTS HTTP {exc.code}: {exc.read()[:200]!r}") from exc
        except urllib.error.URLError as exc:
            raise VolcTtsError(f"TTS unreachable: {exc.reason}") from exc

        chunks, errors = parse_ndjson_response(raw)
        if not chunks:
            raise VolcTtsError("TTS returned no audio" + (f" ({'; '.join(errors)})" if errors else ""))
        return chunks
