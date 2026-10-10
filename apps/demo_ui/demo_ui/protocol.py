"""Contract v2.0 (frozen 2026-10-09) message protocol for the exhibition demo.

Robot Python = WebSocket server on :8765; the exhibition page = WS client.
Message types: chat / video_ready / video_failed / system / send / ping / pong.

Reference: exhibition/接口契约-展会演示系统.md + mock-ws-backend.js (living example).
"""
from __future__ import annotations

import threading
from datetime import datetime

FIXED_BOT_TEXT = "好的，我已收到您的请求，正在为您生成视频，请稍候。"


def now_hhmm() -> str:
    return datetime.now().strftime("%H:%M")


def chat_msg(round_no: int, role: str, text: str) -> dict:
    assert role in ("user", "bot")
    return {"type": "chat", "round": round_no, "role": role, "text": text, "time": now_hhmm()}


def video_ready_msg(round_no: int, url: str) -> dict:
    return {"type": "video_ready", "round": round_no, "url": url}


def video_failed_msg(round_no: int, reason: str) -> dict:
    return {"type": "video_failed", "round": round_no, "reason": reason}


def system_msg(online: bool = True) -> dict:
    return {"type": "system", "online": online}


def pong_msg() -> dict:
    return {"type": "pong"}


class RoundManager:
    """One round at a time. Broadcasts the frozen protocol messages.

    Guarantees (per contract):
      - round increments per new visitor turn and is carried in every message
      - exactly ONE terminal state per round (first terminal wins; later
        terminals for the same or an older round are dropped)
      - 90 s watchdog: if no terminal state was emitted, video_failed(timeout)
    """

    def __init__(self, broadcast, timeout_s: float = 90.0) -> None:
        self._broadcast = broadcast
        self.timeout_s = timeout_s
        self._lock = threading.Lock()
        self.round = 0
        self._timer: threading.Timer | None = None
        self._terminal_rounds: set[int] = set()

    def new_round(self, user_text: str, bot_reply: str | None = None) -> int:
        """Start a round. Emits chat(user); emits chat(bot) only if bot_reply is given."""
        with self._lock:
            self.round += 1
            r = self.round
            self._arm_watchdog(r)
        self._broadcast(chat_msg(r, "user", user_text))
        if bot_reply:
            self._broadcast(chat_msg(r, "bot", bot_reply))
        return r

    def broadcast_chat(self, round_no: int, role: str, text: str) -> None:
        """Public helper: emit an extra chat line for an active round."""
        with self._lock:
            if round_no != self.round:
                return  # never leak a chat line into a newer round
        self._broadcast(chat_msg(round_no, role, text))

    def _arm_watchdog(self, r: int) -> None:
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(self.timeout_s, self._on_timeout, args=(r,))
        self._timer.daemon = True
        self._timer.start()

    def _on_timeout(self, r: int) -> None:
        self.finish_failed(r, "timeout")

    def _emit_terminal(self, r: int, msg: dict) -> None:
        with self._lock:
            if r != self.round or r in self._terminal_rounds:
                return  # stale round or duplicate terminal - drop
            self._terminal_rounds.add(r)
            if self._timer is not None:
                self._timer.cancel()
        self._broadcast(msg)

    def finish_ready(self, r: int, url: str) -> None:
        self._emit_terminal(r, video_ready_msg(r, url))

    def finish_failed(self, r: int, reason: str) -> None:
        self._emit_terminal(r, video_failed_msg(r, reason))
