"""Shared session state for the demo.

The robot orchestrator updates this state (in-process, or via POST /api/events);
the developer's page polls GET /api/session.

Stale-video guarantee (per the developer's two-request question):
  - a new video request IMMEDIATELY clears the previous result_url,
  - a late-arriving result for an OLD task is ignored.
"""
from __future__ import annotations

import threading
import time

VALID_STATUSES = ("idle", "queued", "running", "succeeded", "failed")


class SessionState:
    def __init__(self, max_dialogues: int = 500) -> None:
        self._lock = threading.Lock()
        self._dialogues: list[dict] = []
        self._max = max_dialogues
        self._current_task_id = ""
        self._task_status = "idle"
        self._result_url: str | None = None

    # ---------------------------------------------------------------- dialogue
    def dialogue(self, speaker: str, text: str) -> None:
        """speaker: 'user' | 'robot'"""
        with self._lock:
            self._dialogues.append({"speaker": speaker, "text": text, "ts": time.time()})
            if len(self._dialogues) > self._max:
                self._dialogues = self._dialogues[-self._max:]

    # ------------------------------------------------------------------- video
    def video_start(self, task_id: str) -> None:
        """Called BEFORE submitting a new generation. Clears the previous result."""
        with self._lock:
            self._current_task_id = task_id
            self._task_status = "queued"
            self._result_url = None

    def video_status(self, task_id: str, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"bad status {status!r}")
        with self._lock:
            if task_id != self._current_task_id:
                return  # stale task update ignored
            self._task_status = status

    def video_result(self, task_id: str, url: str) -> None:
        with self._lock:
            if task_id != self._current_task_id:
                return  # late result for an old task ignored
            self._task_status = "succeeded"
            self._result_url = url

    # ----------------------------------------------------------------- snapshot
    def snapshot(self) -> dict:
        with self._lock:
            return {
                "dialogues": list(self._dialogues),
                "current_task_id": self._current_task_id,
                "task_status": self._task_status,
                "result_url": self._result_url,
            }

    def handle(self, kind: str, **payload) -> None:
        """Dispatch one event (used by POST /api/events)."""
        if kind == "dialogue":
            self.dialogue(payload["speaker"], payload["text"])
        elif kind == "video_start":
            self.video_start(payload["task_id"])
        elif kind == "video_status":
            self.video_status(payload["task_id"], payload["status"])
        elif kind == "video_result":
            self.video_result(payload["task_id"], payload["url"])
        else:
            raise ValueError(f"unknown event kind {kind!r}")


state = SessionState()
