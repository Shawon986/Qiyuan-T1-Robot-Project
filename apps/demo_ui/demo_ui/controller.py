"""Demo controller: visitor text -> round -> fixed bot phrase -> SeeDance -> terminal.

Per the frozen contract: the ROBOT calls SeeDance directly (keys never enter the
browser), generation params are fixed (15 s, 16:9), and exactly one terminal
state is emitted per round.
"""
from __future__ import annotations

import os
import threading

from .protocol import RoundManager

DURATION_SECONDS = 15
RATIO = "16:9"
DRY_VIDEO_URL = os.environ.get("DEMO_DRY_VIDEO_URL", "")


class DemoController:
    def __init__(self, rounds: RoundManager, generator=None) -> None:
        self.rounds = rounds
        self._generator = generator or self._seedance_generate

    @staticmethod
    def _seedance_generate(prompt: str) -> str:
        """Live generation via the validated seedance pipeline (15 s, 16:9).

        DEMO_DRY=1 (rehearsal mode) returns a fixed URL instantly instead.
        """
        if os.environ.get("DEMO_DRY") == "1":
            return DRY_VIDEO_URL or "https://www.w3schools.com/html/mov_bbb.mp4"
        from seedance.client import result_video_url
        from seedance.config import SeedanceConfig
        from seedance.pipeline import SeeDancePipeline

        pipeline = SeeDancePipeline(SeedanceConfig())
        task_id = pipeline.client.submit(prompt, duration=DURATION_SECONDS, ratio=RATIO)
        task = pipeline.client.wait(task_id)
        if task.get("status") != "succeeded":
            raise RuntimeError(f"generation {task.get('status')}")
        url = result_video_url(task)
        if not url:
            raise RuntimeError("generation succeeded but no video_url")
        return url

    def start_round(self, text: str) -> int:
        r = self.rounds.new_round(text)
        threading.Thread(target=self._run, args=(r, text), daemon=True).start()
        return r

    def _run(self, r: int, text: str) -> None:
        try:
            url = self._generator(text)
            self.rounds.finish_ready(r, url)
        except Exception as exc:
            # Log the real reason server-side (the page intentionally shows fallbacks only)
            print(f"[demo] round {r} generation failed: {type(exc).__name__}: {exc}", flush=True)
            self.rounds.finish_failed(r, f"upstream_error: {type(exc).__name__}")
