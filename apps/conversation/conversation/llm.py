"""Qwen (DashScope) client with in-session long-context memory."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import ConversationConfig


class LlmError(RuntimeError):
    pass


class SessionMemory:
    """Keeps the system prompt + a bounded window of turns (session memory)."""

    def __init__(self, system_prompt: str, max_messages: int = 12) -> None:
        self.system_prompt = system_prompt
        self.max_messages = max_messages
        self._messages: list[dict] = []

    def add_user(self, text: str) -> None:
        self._messages.append({"role": "user", "content": text})

    def add_assistant(self, text: str) -> None:
        self._messages.append({"role": "assistant", "content": text})

    def build(self) -> list[dict]:
        window = self._messages[-self.max_messages:] if self.max_messages > 0 else self._messages
        return [{"role": "system", "content": self.system_prompt}] + window

    def reset(self) -> None:
        self._messages = []


class QwenClient:
    """Minimal OpenAI-compatible chat client for DashScope (no extra deps)."""

    def __init__(self, cfg: ConversationConfig | None = None) -> None:
        self.cfg = cfg or ConversationConfig()
        if not self.cfg.dashscope_key:
            raise LlmError("DASHSCOPE_API_KEY is not configured (check .env)")

    def chat(self, messages: list[dict], timeout: float = 60.0) -> str:
        body = json.dumps({
            "model": self.cfg.llm_model,
            "messages": messages,
            "temperature": 0.7,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.cfg.llm_endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.cfg.dashscope_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise LlmError(f"LLM HTTP {exc.code}: {exc.read()[:200]!r}") from exc
        except urllib.error.URLError as exc:
            raise LlmError(f"LLM unreachable: {exc.reason}") from exc
        try:
            return payload["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise LlmError(f"unexpected LLM response: {payload}") from exc
