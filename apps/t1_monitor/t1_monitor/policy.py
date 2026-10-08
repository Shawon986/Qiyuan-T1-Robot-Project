"""Pure, fail-closed validation helpers - no ROS, no robot, fully offline-testable.

These policies mirror the handbook's t1_python_app design: a side-effecting
request (TTS) is only allowed after explicit opt-in + exact confirmation
token + bounded text, and motion is ALWAYS disabled in this application.
"""
from __future__ import annotations

from dataclasses import dataclass

TTS_CONFIRMATION_TOKEN = "T1_TTS_CONFIRMED"
MAX_TTS_CHARACTERS = 240


@dataclass(frozen=True)
class GuardDecision:
    """Result of a local guard check before any external side effect."""

    allowed: bool
    reason: str


@dataclass(frozen=True)
class MotionDecision:
    """T1 motion is intentionally out of scope for the monitor application."""

    allowed: bool
    reason: str


class MotionGuard:
    """Fail closed: this application never creates a motion interface."""

    def request(self, requested_operation: str) -> MotionDecision:
        return MotionDecision(
            allowed=False,
            reason=(
                "Motion is intentionally disabled in t1_monitor; no T1 motion "
                f"endpoint was called for request {requested_operation!r}."
            ),
        )


def validate_tts_request(*, enabled: bool, confirmation_token: str, text: str) -> GuardDecision:
    """Allow TTS only after explicit opt-in, exact confirmation, and bounded text."""
    if not enabled:
        return GuardDecision(False, "TTS is disabled (enable_tts is false).")
    if confirmation_token != TTS_CONFIRMATION_TOKEN:
        return GuardDecision(False, "TTS confirmation token is absent or incorrect.")
    if not text.strip():
        return GuardDecision(False, "TTS text is empty.")
    if len(text) > MAX_TTS_CHARACTERS:
        return GuardDecision(False, f"TTS text exceeds the {MAX_TTS_CHARACTERS}-character local limit.")
    return GuardDecision(True, "Local guard accepted the request.")


class GuardedTtsPolicy:
    """Keep the side-effecting TTS request behind one inspectable local policy."""

    def decide(self, enabled: bool, confirmation_token: str, text: str) -> GuardDecision:
        return validate_tts_request(
            enabled=enabled, confirmation_token=confirmation_token, text=text
        )
