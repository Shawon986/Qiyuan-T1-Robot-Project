"""BytePlus ModelArk Seedance generation client (validated live 2026-10-08)."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from .config import SeedanceConfig


class ArkError(RuntimeError):
    """Raised for any upstream failure; callers treat it as fail-closed."""


def build_task_payload(model: str, prompt: str, image_b64: str | None = None,
                       video_url: str | None = None, role: str = "first_frame",
                       duration: int | None = None, ratio: str | None = None) -> dict[str, Any]:
    """Pure payload builder (offline-testable).

    Validated reference rules:
      - text: {"type": "text", "text": ...}
      - image: inline base64 data URI (or public URL) - base64 verified working
      - video: public URL only (role "reference_video") - base64 rejected upstream
    Generation params (per the frozen exhibition contract): top-level
    `duration` (seconds) and `ratio` (e.g. "16:9") - confirmed from the
    developer's original page payload.
    """
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    if image_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
            "role": role,
        })
    if video_url:
        content.append({
            "type": "video_url",
            "video_url": {"url": video_url},
            "role": "reference_video",
        })
    body: dict[str, Any] = {"model": model, "content": content}
    if duration is not None:
        body["duration"] = duration
    if ratio:
        body["ratio"] = ratio
    return body


def result_video_url(task: dict) -> str | None:
    """Extract the result mp4 URL from a finished task."""
    content = task.get("content") or {}
    return content.get("video_url")


class SeedanceClient:
    def __init__(self, cfg: SeedanceConfig | None = None) -> None:
        self.cfg = cfg or SeedanceConfig()
        if not self.cfg.api_key:
            raise ArkError("SEEDANCE_API_KEY is not configured (check .env)")

    def _request(self, method: str, path: str, payload: dict | None = None,
                 timeout: float = 120.0) -> dict:
        url = f"{self.cfg.api_base}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Authorization": f"Bearer {self.cfg.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise ArkError(f"upstream HTTP {exc.code}: {exc.read()[:300]!r}") from exc
        except urllib.error.URLError as exc:
            raise ArkError(f"upstream unreachable: {exc.reason}") from exc

    def submit(self, prompt: str, image_b64: str | None = None,
               video_url: str | None = None, role: str = "first_frame",
               duration: int | None = None, ratio: str | None = None) -> str:
        body = build_task_payload(self.cfg.model_id, prompt, image_b64, video_url, role,
                                  duration=duration, ratio=ratio)
        resp = self._request("POST", "/contents/generations/tasks", body)
        task_id = resp.get("id")
        if not task_id:
            raise ArkError(f"no task id in response: {resp}")
        return task_id

    def get(self, task_id: str) -> dict:
        return self._request("GET", f"/contents/generations/tasks/{task_id}")

    def wait(self, task_id: str, poll_interval: float | None = None,
             timeout: float | None = None) -> dict:
        interval = poll_interval if poll_interval is not None else self.cfg.poll_interval_s
        deadline = time.monotonic() + (timeout if timeout is not None else self.cfg.poll_timeout_s)
        while True:
            task = self.get(task_id)
            status = task.get("status")
            if status in ("succeeded", "failed", "cancelled"):
                return task
            if time.monotonic() > deadline:
                raise ArkError(f"task {task_id} timed out (last status={status})")
            time.sleep(interval)
