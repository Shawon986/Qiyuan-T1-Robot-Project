"""Offline tests for the frozen contract protocol + round manager."""
import unittest

from demo_ui.protocol import (
    FIXED_BOT_TEXT,
    RoundManager,
    chat_msg,
    now_hhmm,
    pong_msg,
    system_msg,
    video_failed_msg,
    video_ready_msg,
)


class FakeHub:
    def __init__(self):
        self.sent = []

    def broadcast(self, msg):
        self.sent.append(msg)


class TestMessages(unittest.TestCase):
    def test_chat_shape(self):
        m = chat_msg(5, "user", "hello")
        self.assertEqual(m["type"], "chat")
        self.assertEqual(m["round"], 5)
        self.assertEqual(m["role"], "user")
        self.assertEqual(m["time"], now_hhmm())  # HH:MM format
        self.assertIn(":", m["time"])

    def test_terminal_shapes(self):
        self.assertEqual(video_ready_msg(3, "https://x/v.mp4"),
                         {"type": "video_ready", "round": 3, "url": "https://x/v.mp4"})
        self.assertEqual(video_failed_msg(3, "upstream_error"),
                         {"type": "video_failed", "round": 3, "reason": "upstream_error"})

    def test_system_pong(self):
        self.assertEqual(system_msg(True), {"type": "system", "online": True})
        self.assertEqual(pong_msg(), {"type": "pong"})


class TestRoundManager(unittest.TestCase):
    def setUp(self):
        self.hub = FakeHub()
        self.rm = RoundManager(self.hub.broadcast, timeout_s=90)

    def test_new_round_emits_user_then_fixed_bot(self):
        r = self.rm.new_round("做个视频")
        self.assertEqual(r, 1)
        self.assertEqual(self.hub.sent[0]["type"], "chat")
        self.assertEqual(self.hub.sent[0]["role"], "user")
        self.assertEqual(self.hub.sent[1]["role"], "bot")
        self.assertEqual(self.hub.sent[1]["text"], FIXED_BOT_TEXT)
        self.assertEqual(self.hub.sent[0]["round"], 1)
        self.assertEqual(self.hub.sent[1]["round"], 1)

    def test_round_increments(self):
        self.rm.new_round("a")
        r = self.rm.new_round("b")
        self.assertEqual(r, 2)
        self.assertEqual(self.hub.sent[-1]["round"], 2)

    def test_first_terminal_wins(self):
        r = self.rm.new_round("x")
        self.rm.finish_ready(r, "https://x/1.mp4")
        self.rm.finish_failed(r, "late failure")  # duplicate terminal - dropped
        terminals = [m for m in self.hub.sent if m["type"] in ("video_ready", "video_failed")]
        self.assertEqual(len(terminals), 1)
        self.assertEqual(terminals[0]["type"], "video_ready")

    def test_stale_round_terminal_dropped(self):
        r1 = self.rm.new_round("first")
        self.rm.new_round("second")
        self.rm.finish_ready(r1, "https://x/old.mp4")  # stale - dropped
        terminals = [m for m in self.hub.sent if m["type"] == "video_ready"]
        self.assertEqual(terminals, [])
        # and the current round still works
        self.rm.finish_failed(2, "boom")
        self.assertEqual(self.hub.sent[-1]["type"], "video_failed")
        self.assertEqual(self.hub.sent[-1]["round"], 2)

    def test_watchdog_fires_timeout(self):
        rm = RoundManager(self.hub.broadcast, timeout_s=0.1)
        r = rm.new_round("slow")
        import time
        time.sleep(0.3)
        terminals = [m for m in self.hub.sent if m["type"] == "video_failed"]
        self.assertEqual(len(terminals), 1)
        self.assertEqual(terminals[0]["reason"], "timeout")
        self.assertEqual(terminals[0]["round"], r)

    def test_watchdog_does_not_fire_for_older_round(self):
        rm = RoundManager(self.hub.broadcast, timeout_s=0.1)
        rm.new_round("one")
        time_ = __import__("time")
        time_.sleep(0.05)
        r2 = rm.new_round("two")  # resets watchdog to round 2
        time_.sleep(0.15)
        # only round 2 may have timed out (if at all); round 1 must not emit
        failed_for_r1 = [m for m in self.hub.sent if m["type"] == "video_failed" and m["round"] == 1]
        self.assertEqual(failed_for_r1, [])
        _ = r2


if __name__ == "__main__":
    unittest.main()
