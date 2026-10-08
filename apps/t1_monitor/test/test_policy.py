"""No-ROS, no-robot tests for the local fail-closed policies."""
import unittest

from t1_monitor.policy import MAX_TTS_CHARACTERS, TTS_CONFIRMATION_TOKEN, GuardedTtsPolicy, MotionGuard


class TestSafety(unittest.TestCase):
    def setUp(self) -> None:
        self.tts = GuardedTtsPolicy()
        self.motion = MotionGuard()

    def test_tts_is_disabled_by_default(self) -> None:
        decision = self.tts.decide(
            enabled=False, confirmation_token=TTS_CONFIRMATION_TOKEN, text="hello"
        )
        self.assertFalse(decision.allowed)

    def test_tts_requires_exact_confirmation(self) -> None:
        decision = self.tts.decide(enabled=True, confirmation_token="wrong", text="hello")
        self.assertFalse(decision.allowed)

    def test_tts_rejects_empty_text(self) -> None:
        decision = self.tts.decide(
            enabled=True, confirmation_token=TTS_CONFIRMATION_TOKEN, text="   "
        )
        self.assertFalse(decision.allowed)

    def test_tts_accepts_bounded_explicit_request(self) -> None:
        decision = self.tts.decide(
            enabled=True, confirmation_token=TTS_CONFIRMATION_TOKEN, text="hello"
        )
        self.assertTrue(decision.allowed)

    def test_tts_rejects_overlong_text(self) -> None:
        decision = self.tts.decide(
            enabled=True,
            confirmation_token=TTS_CONFIRMATION_TOKEN,
            text="x" * (MAX_TTS_CHARACTERS + 1),
        )
        self.assertFalse(decision.allowed)

    def test_motion_is_always_disabled(self) -> None:
        decision = self.motion.request("any operation")
        self.assertFalse(decision.allowed)
        self.assertIn("disabled", decision.reason)


if __name__ == "__main__":
    unittest.main()
