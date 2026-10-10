"""Offline tests for the final demo controller (video intent + /demo/last)."""
import unittest

from demo_ui.controller import DEFAULT_WAIT_PHRASE, DemoController, LatestRound
from demo_ui.protocol import RoundManager


class FakeHub:
    def __init__(self):
        self.sent = []

    def broadcast(self, msg):
        self.sent.append(msg)


def make_controller(submitter=None, responder=None):
    hub = FakeHub()
    rounds = RoundManager(hub.broadcast, timeout_s=90)
    ctrl = DemoController(rounds, submitter=submitter or (lambda t: "task-123"),
                          responder=responder or (lambda t: "我好好呀"))
    return hub, rounds, ctrl


class TestLatestRound(unittest.TestCase):
    def test_set_get(self):
        latest = LatestRound()
        latest.set(3, "帮我生成视频", "cgt-abc")
        data = latest.get()
        self.assertEqual(data["round"], 3)
        self.assertEqual(data["taskId"], "cgt-abc")
        self.assertIn(":", data["time"])  # HH:MM


class TestVideoIntent(unittest.TestCase):
    def test_video_request_replies_wait_phrase_and_records_task(self):
        from demo_ui import controller
        controller.latest = LatestRound()
        hub, rounds, ctrl = make_controller()
        r = ctrl.start_round("帮我生成一个海边日落的视频")
        self.assertEqual(hub.sent[0]["role"], "user")
        self.assertEqual(hub.sent[1]["role"], "bot")
        self.assertEqual(hub.sent[1]["text"], DEFAULT_WAIT_PHRASE)
        import time
        time.sleep(0.3)  # background thread completes
        data = controller.latest.get()
        self.assertEqual(data["round"], r)
        self.assertEqual(data["taskId"], "task-123")
        self.assertEqual(data["text"], "帮我生成一个海边日落的视频")

    def test_submit_failure_emits_video_failed(self):
        hub, rounds, ctrl = make_controller(submitter=(lambda t: (_ for _ in ()).throw(RuntimeError("boom"))))
        ctrl.start_round("帮我生成一个视频")
        import time
        time.sleep(0.3)
        terminals = [m for m in hub.sent if m["type"] == "video_failed"]
        self.assertEqual(len(terminals), 1)
        self.assertIn("submit_error", terminals[0]["reason"])


class TestChatIntent(unittest.TestCase):
    def test_chat_turn_answers_via_responder(self):
        hub, rounds, ctrl = make_controller()
        ctrl.start_round("你今日點呀？")
        import time
        time.sleep(0.3)
        bots = [m for m in hub.sent if m["role"] == "bot"]
        self.assertEqual(len(bots), 1)
        self.assertEqual(bots[0]["text"], "我好好呀")


if __name__ == "__main__":
    unittest.main()
