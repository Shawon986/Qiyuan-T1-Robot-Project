"""High-level SeeDance pipeline: upload -> submit -> poll -> result.

PC-testable today (any local video file); the robot camera adapter plugs in
later without changing this module.
"""
from __future__ import annotations

import base64
from pathlib import Path

from .client import ArkError, SeedanceClient, result_video_url
from .config import SeedanceConfig
from .storage import StorageUploader


class SeeDancePipeline:
    def __init__(self, cfg: SeedanceConfig | None = None) -> None:
        self.cfg = cfg or SeedanceConfig()
        self.client = SeedanceClient(self.cfg)
        self.storage = StorageUploader(self.cfg) if self.cfg.ready() else None

    def run(self, prompt: str, video_path: str | None = None,
            image_path: str | None = None, wait: bool = True) -> dict:
        """Run one generation. Fail-closed: any upstream error raises ArkError."""
        video_url = None
        if video_path:
            if self.storage is None:
                raise ArkError("TOS credentials not configured - cannot host the video")
            video_url = self.storage.upload_and_publish(video_path)

        image_b64 = None
        if image_path:
            image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")

        task_id = self.client.submit(prompt, image_b64=image_b64, video_url=video_url)
        outcome = {"task_id": task_id, "status": None, "result_url": None}
        if wait:
            task = self.client.wait(task_id)
            outcome["status"] = task.get("status")
            outcome["result_url"] = result_video_url(task)
        return outcome
