"""AIChain (iFlytek AIUI overseas) unified STT+NLU+TTS WebSocket client.

Spec: WebSocket API v2.1. Auth: checksum = sha256(appKey + curtime) in the URL query.
Flow: connect -> session.created -> session.config -> conversation.user.append ->
collect stt.result / nlu.answer / tts.audio -> event.cid_end.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

import websocket  # websocket-client

from .config import ConversationConfig

STT_RESULT = "stt.result"
NLU_ANSWER = "nlu.answer"
TTS_AUDIO = "tts.audio"
CID_END = "event.cid_end"
SESSION_CREATED = "session.created"
SESSION_CONFIGED = "session.configed"

# The server rejects audio items larger than 25600 bytes; 16000 bytes = 0.5 s
# of 16 kHz / 16-bit mono PCM, a safe streaming chunk size.
AUDIO_CHUNK_MAX = 16000


class AichainError(RuntimeError):
    pass


def build_ws_url(app_id: str, app_key: str, sn: str, base: str) -> str:
    """URL with checksum auth: /v1/chat/{appId}?curtime=&checksum=&sn=."""
    curtime = str(int(time.time()))
    checksum = hashlib.sha256((app_key + curtime).encode()).hexdigest()
    params = urllib.parse.urlencode({"curtime": curtime, "checksum": checksum, "sn": sn})
    return f"{base.rstrip('/')}/v1/chat/{app_id}?{params}"


def build_session_config(cfg: ConversationConfig, sid: str) -> dict:
    """session.config frame: half-duplex, STT (Cantonese), optional NLU, TTS raw."""
    config: dict = {
        "mode": "half_duplex",
        "simplifiedResponse": True,
        "multiTurnEnabled": True,
        "stt": {
            "enable": True,
            "sttEngineId": cfg.aichain_stt_engine,
            "language": cfg.aichain_stt_language,
            "audioConfig": {
                "audioEncoding": "raw", "format": "plain",
                "sampleRate": 16000, "bitDepth": 16, "channels": 1,
            },
            "vad": {"enable": True},
            "turnDetection": {"enable": True},
        },
        "tts": {
            "enable": True,
            "voices": {
                # voices are keyed by language: "zh" = Mandarin, "zh-HK" = Cantonese.
                # (Until 2026-10-10 we sent "zh" only, so the robot spoke Mandarin
                #  even for Cantonese text — the zh-HK key selects the Cantonese voice.)
                cfg.aichain_tts_voice_key: {
                    "voiceId": cfg.aichain_tts_voice_id,
                    "audioConfig": {
                        "audioEncoding": "raw",
                        "sampleRate": 16000, "bitDepth": 16, "channels": 1,
                    },
                }
            },
        },
    }
    if cfg.aichain_nlu_enabled:
        config["nlu"] = {"enable": True, "streamingBufferLength": 10}
    else:
        config["nlu"] = {"enable": False}
    return {"type": "session.config", "sid": sid, "config": config}


def build_append(sid: str, cid: str, items: list[dict], end_flag: bool = True) -> dict:
    return {"type": "conversation.user.append", "sid": sid, "cid": cid,
            "items": items, "endFlag": end_flag}


@dataclass
class AichainTurn:
    user_text: str = ""
    answer_text: str = ""
    audio_wav: bytes | None = None
    errors: list[str] = field(default_factory=list)


class AichainClient:
    def __init__(self, cfg: ConversationConfig | None = None) -> None:
        self.cfg = cfg or ConversationConfig()
        if not (self.cfg.aichain_app_id and self.cfg.aichain_app_key):
            raise AichainError("AICHAIN_APP_ID / AICHAIN_APP_KEY not configured")

    def _open_session(self, cfg: ConversationConfig | None = None) -> tuple:
        cfg = cfg or self.cfg
        url = build_ws_url(cfg.aichain_app_id, cfg.aichain_app_key,
                           cfg.aichain_sn, cfg.aichain_base)
        ws = websocket.create_connection(url, timeout=60)
        created = json.loads(ws.recv())
        if created.get("type") != SESSION_CREATED:
            raise AichainError(f"expected session.created, got: {created}")
        sid = created["sid"]
        ws.send(json.dumps(build_session_config(cfg, sid)))
        configured = json.loads(ws.recv())
        if configured.get("type") not in (SESSION_CONFIGED,):
            if configured.get("type") == "session.error":
                err = configured.get("error") or {}
                raise AichainError(f"session config failed: {err.get('code')} {err.get('message')}")
            raise AichainError(f"expected session.configed, got: {configured}")
        return ws, sid

    @staticmethod
    def _consume(ws, sid: str, cid: str, turn: AichainTurn) -> None:
        """Read frames until event.cid_end for the given cid (or error)."""
        stt_parts: list[str] = []
        answer_parts: list[str] = []
        audio_chunks: list[bytes] = []
        while True:
            raw = ws.recv()
            if not raw:
                break
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "session.error":
                err = msg.get("error") or {}
                turn.errors.append(f"{err.get('code')}: {err.get('message')}")
                break
            if mtype == STT_RESULT:
                data = msg.get("data") or {}
                if data.get("action") == "replace":
                    pos = data.get("position") or {}
                    start = pos.get("start", 0)
                    end = pos.get("end", len(stt_parts))
                    del stt_parts[start:end]
                stt_parts.append(data.get("text", ""))
            elif mtype == NLU_ANSWER:
                answer_parts.append((msg.get("data") or {}).get("answer", ""))
            elif mtype == TTS_AUDIO:
                data = msg.get("data") or ""
                if isinstance(data, str) and data:
                    audio_chunks.append(base64.b64decode(data))
            elif mtype == CID_END:
                break
        turn.user_text = "".join(stt_parts).strip()
        turn.answer_text = "".join(answer_parts).strip()
        if audio_chunks:
            turn.audio_wav = _pcm_to_wav(b"".join(audio_chunks))

    def send_text(self, text: str) -> AichainTurn:
        """One text turn through the capability chain (NLU+TTS per app config)."""
        ws, sid = self._open_session()
        cid = f"cid-{int(time.time() * 1000)}"
        turn = AichainTurn()
        try:
            ws.send(json.dumps(build_append(sid, cid, [{"type": "text", "data": text}])))
            self._consume(ws, sid, cid, turn)
        finally:
            ws.close()
        if turn.errors:
            raise AichainError("; ".join(turn.errors))
        return turn

    def send_audio_file(self, audio_path: str | Path) -> AichainTurn:
        """One audio turn (STT via engine config; then NLU/TTS per app config).

        The audio is streamed in <= 16000-byte chunks (server limit: 25600 bytes
        per audio item), each chunk as its own append frame, endFlag on the last.
        """
        data = Path(audio_path).read_bytes()
        if data[:4] == b"RIFF":
            data = data[44:]  # strip standard WAV header
        if not data:
            raise AichainError(f"no audio data in {audio_path}")
        ws, sid = self._open_session()
        cid = f"cid-{int(time.time() * 1000)}"
        turn = AichainTurn()
        try:
            chunks = chunk_pcm(data)
            for i, chunk in enumerate(chunks):
                b64 = base64.b64encode(chunk).decode()
                last = i == len(chunks) - 1
                ws.send(json.dumps(build_append(
                    sid, cid, [{"type": "audio", "data": b64}], end_flag=last)))
            self._consume(ws, sid, cid, turn)
        finally:
            ws.close()
        if turn.errors:
            raise AichainError("; ".join(turn.errors))
        return turn

    def synthesize(self, text: str) -> bytes:
        """TTS-only turn: speak arbitrary Cantonese text with the configured voice.

        NLU is disabled for the session, so the tts.audio frames carry the TTS of
        the input text itself (verified live 2026-10-10). Returns WAV bytes.
        """
        import os as _os
        cfg = ConversationConfig(env={**_os.environ, "AICHAIN_NLU_ENABLED": "0"})
        ws, sid = self._open_session(cfg)
        cid = f"cid-{int(time.time() * 1000)}"
        turn = AichainTurn()
        try:
            ws.send(json.dumps(build_append(sid, cid, [{"type": "text", "data": text}])))
            self._consume(ws, sid, cid, turn)
        finally:
            ws.close()
        if turn.errors:
            raise AichainError("; ".join(turn.errors))
        if not turn.audio_wav:
            raise AichainError("TTS returned no audio")
        return turn.audio_wav


def chunk_pcm(data: bytes, chunk_size: int = AUDIO_CHUNK_MAX) -> list[bytes]:
    """Split PCM into server-acceptable chunks (<= 25600 bytes per audio item)."""
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


def _pcm_to_wav(pcm: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    import struct
    header = (
        b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, channels, sample_rate,
                      sample_rate * 2 * channels, 2 * channels, 16)
        + b"data" + struct.pack("<I", len(pcm))
    )
    return header + pcm
