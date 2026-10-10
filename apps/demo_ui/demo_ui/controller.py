"""Demo controller (final architecture, 2026-10-10).

Flow per the finalized spec:
  - visitor asks for a video -> robot replies the fixed waiting phrase
  - robot submits the task to Seedance (visitor's words as prompt) -> taskId
  - robot serves {round, text, time, taskId} on GET :8766/demo/last
  - the developer's page polls it and handles everything else (direct mode)
  - non-video text is answered conversationally via AIChain (Cantonese)
"""
from __future__ import annotations

import os
import threading
import time

from .protocol import RoundManager, now_hhmm

DURATION_SECONDS = 15
RATIO = "16:9"
DRY_VIDEO_URL = os.environ.get("DEMO_DRY_VIDEO_URL", "")
DEFAULT_WAIT_PHRASE = "請稍等，我馬上幫你生成視頻。"


class LatestRound:
    """The robot's small JSON for the page (direct mode): /demo/last."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict = {"round": 0, "text": "", "time": "", "taskId": ""}

    def set(self, round_no: int, text: str, task_id: str) -> None:
        with self._lock:
            self._data = {"round": round_no, "text": text,
                          "time": now_hhmm(), "taskId": task_id}

    def get(self) -> dict:
        with self._lock:
            return dict(self._data)


latest = LatestRound()


class DemoController:
    def __init__(self, rounds: RoundManager, submitter=None, responder=None,
                 wait_phrase: str | None = None) -> None:
        self.rounds = rounds
        self._submitter = submitter or self._seedance_submit
        self._responder = responder or self._aichain_respond
        self.wait_phrase = wait_phrase or os.environ.get("DEMO_WAIT_PHRASE", DEFAULT_WAIT_PHRASE)

    @staticmethod
    def _seedance_submit(prompt: str) -> str:
        """Submit the task; return the taskId. NO waiting.

        Final flow: record what the robot sees (official RTSP capture) and use it
        as the reference video. If the camera is unavailable, fall back to
        prompt-only generation so the demo never breaks.
        """
        if os.environ.get("DEMO_DRY") == "1":
            return f"dry-{int(time.time() * 1000)}"
        from seedance.config import SeedanceConfig
        from seedance.pipeline import SeeDancePipeline

        pipeline = SeeDancePipeline(SeedanceConfig())
        if os.environ.get("CAMERA_VIDEO_REFERENCE", "1") == "1":
            from .camera_capture import capture_clip
            clip = capture_clip()
            if clip is not None:
                try:
                    outcome = pipeline.run(prompt, video_path=str(clip), wait=False)
                    clip.unlink(missing_ok=True)  # temp only — cloud holds the copy
                    return outcome["task_id"]
                except Exception as exc:
                    print(f"[demo] video-reference submit failed "
                          f"({type(exc).__name__}: {exc}); prompt-only fallback", flush=True)
            else:
                print("[demo] camera capture unavailable; prompt-only fallback", flush=True)
        return pipeline.client.submit(prompt, duration=DURATION_SECONDS, ratio=RATIO)

    @staticmethod
    def _aichain_respond(text: str) -> str:
        """Conversational Cantonese answer for non-video turns (AIChain)."""
        from conversation.aichain import AichainClient
        from conversation.config import ConversationConfig

        return AichainClient(ConversationConfig()).send_text(text).answer_text

    def start_round(self, text: str) -> int:
        from conversation.intent import classify_intent
        if classify_intent(text) == "generate_video":
            r = self.rounds.new_round(text, bot_reply=self.wait_phrase)
        else:
            r = self.rounds.new_round(text)  # chat(user) only; AIChain answer follows
        threading.Thread(target=self._run, args=(r, text), daemon=True).start()
        return r

    def _run(self, r: int, text: str) -> None:
        from conversation.intent import classify_intent
        if classify_intent(text) == "generate_video":
            try:
                task_id = self._submitter(text)
                latest.set(r, text, task_id)
                print(f"[demo] round {r} task submitted: {task_id}", flush=True)
            except Exception as exc:
                print(f"[demo] round {r} submit failed: {type(exc).__name__}: {exc}", flush=True)
                self.rounds.finish_failed(r, f"submit_error: {type(exc).__name__}")
            return
        # chat turn: answer via AIChain (Cantonese) and push the reply to the page
        try:
            answer = self._responder(text)
            if answer:
                self.rounds.broadcast_chat(r, "bot", answer)
        except Exception as exc:
            print(f"[demo] round {r} conversation failed: {type(exc).__name__}: {exc}", flush=True)
