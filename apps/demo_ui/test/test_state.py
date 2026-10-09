"""Offline tests for the session state — incl. the developer's two-request scenario."""
import unittest

from demo_ui.events import SessionState


class TestDialogue(unittest.TestCase):
    def test_append_and_speaker(self):
        s = SessionState()
        s.dialogue("user", "hello")
        s.dialogue("robot", "hi there")
        snap = s.snapshot()
        self.assertEqual(len(snap["dialogues"]), 2)
        self.assertEqual(snap["dialogues"][0]["speaker"], "user")

    def test_capped(self):
        s = SessionState(max_dialogues=3)
        for i in range(5):
            s.dialogue("user", str(i))
        self.assertEqual(len(s.snapshot()["dialogues"]), 3)


class TestStaleVideoPrevention(unittest.TestCase):
    """The developer's exact question: request 1 succeeds, request 2 starts -
    must the page ever show video 1 as the current result?"""

    def test_second_request_clears_previous_result(self):
        s = SessionState()
        s.video_start("task-A")
        s.video_status("task-A", "running")
        s.video_result("task-A", "https://x/videoA.mp4")
        self.assertEqual(s.snapshot()["result_url"], "https://x/videoA.mp4")

        # second conversation asks for a new video
        s.video_start("task-B")
        snap = s.snapshot()
        self.assertEqual(snap["current_task_id"], "task-B")
        self.assertEqual(snap["task_status"], "queued")
        self.assertIsNone(snap["result_url"])  # previous video cleared

    def test_late_old_result_is_ignored(self):
        s = SessionState()
        s.video_start("task-A")
        s.video_start("task-B")
        # task-A finishes AFTER task-B started
        s.video_result("task-A", "https://x/videoA.mp4")
        snap = s.snapshot()
        self.assertIsNone(snap["result_url"])
        self.assertEqual(snap["current_task_id"], "task-B")
        # and the current task's result still lands correctly
        s.video_result("task-B", "https://x/videoB.mp4")
        self.assertEqual(s.snapshot()["result_url"], "https://x/videoB.mp4")

    def test_stale_status_update_ignored(self):
        s = SessionState()
        s.video_start("task-A")
        s.video_start("task-B")
        s.video_status("task-A", "failed")
        self.assertEqual(s.snapshot()["task_status"], "queued")

    def test_bad_status_rejected(self):
        s = SessionState()
        with self.assertRaises(ValueError):
            s.video_status("t", "exploded")


class TestEventDispatch(unittest.TestCase):
    def test_handle(self):
        s = SessionState()
        s.handle("dialogue", speaker="user", text="hi")
        s.handle("video_start", task_id="t1")
        s.handle("video_result", task_id="t1", url="https://x/y.mp4")
        snap = s.snapshot()
        self.assertEqual(snap["task_status"], "succeeded")
        self.assertEqual(snap["result_url"], "https://x/y.mp4")


if __name__ == "__main__":
    unittest.main()
