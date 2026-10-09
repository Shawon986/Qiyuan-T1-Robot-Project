"""ConversationEngine: ASR -> Qwen (session memory) -> intent -> TTS, with event posting.

Every user turn and robot reply is posted to the demo session API so the
developer's page renders the live dialogue. A generate_video intent posts a
video_request for the page to auto-generate.
"""
from __future__ import annotations

import json
import time
import urllib.request

from .asr import IflytekASR
from .config import ConversationConfig
from .intent import classify_intent, contains_wake_word, strip_wake_word
from .llm import LlmClient, SessionMemory
from .tts import IflytekTTS


class HttpEventPoster:
    """Posts events to the demo session API; never breaks the conversation."""

    def __init__(self, base: str) -> None:
        self.base = base

    def post(self, kind: str, **payload) -> None:
        try:
            req = urllib.request.Request(
                self.base + "/api/events",
                data=json.dumps({"kind": kind, **payload}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # the demo page being offline must not break the robot


class ConversationEngine:
    def __init__(self, cfg: ConversationConfig | None = None, poster=None) -> None:
        self.cfg = cfg or ConversationConfig()
        self.memory = SessionMemory(self.cfg.system_prompt, self.cfg.max_history_messages)
        self.llm = LlmClient(self.cfg)
        self.asr = IflytekASR(self.cfg)
        self.tts = IflytekTTS(self.cfg)
        self.poster = poster or HttpEventPoster(self.cfg.dialogue_api_base)

    def handle_user_text(self, text: str) -> str:
        """One conversational turn. Returns the robot's reply ('' if not addressed)."""
        if not contains_wake_word(text, self.cfg.wake_words):
            return ""
        clean = strip_wake_word(text, self.cfg.wake_words)
        self.memory.add_user(clean)
        self.poster.post("dialogue", speaker="user", text=text)

        reply = self.llm.chat(self.memory.build())
        self.memory.add_assistant(reply)
        self.poster.post("dialogue", speaker="robot", text=reply)

        intent = classify_intent(clean)
        if intent == "generate_video":
            self.poster.post(
                "video_request",
                request_id=f"req-{int(time.time() * 1000)}",
                prompt=clean,
            )
        return reply

    def speak(self, text: str) -> bytes:
        """TTS the text; returns WAV bytes (caller plays or saves)."""
        return self.tts.synthesize(text)

    def transcribe_file(self, audio_path: str) -> str:
        return self.asr.transcribe_file(audio_path)
