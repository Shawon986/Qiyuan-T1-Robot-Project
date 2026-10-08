"""Offline tests: payload building, config parsing, key/URL helpers. No network, no keys."""
import unittest

from seedance.client import ArkError, SeedanceClient, build_task_payload, result_video_url
from seedance.config import SeedanceConfig
from seedance.storage import object_key

FAKE_ENV = {
    "SEEDANCE_API_KEY": "test-key",
    "SEEDANCE_MODEL_ID": "dreamina-seedance-2-0-fast-260128",
    "TOS_ACCESS_KEY": "ak",
    "TOS_SECRET_KEY": "sk",
    "TOS_BUCKET": "bucket",
    "TOS_ENDPOINT": "https://tos.example.com",
}


class TestConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = SeedanceConfig(env={})
        self.assertEqual(cfg.model_id, "dreamina-seedance-2-0-fast-260128")
        self.assertFalse(cfg.ready())

    def test_full_env(self):
        cfg = SeedanceConfig(env=FAKE_ENV)
        self.assertTrue(cfg.ready())
        self.assertEqual(cfg.tos_bucket, "bucket")

    def test_poll_defaults(self):
        cfg = SeedanceConfig(env=FAKE_ENV)
        self.assertEqual(cfg.poll_interval_s, 5.0)
        self.assertEqual(cfg.poll_timeout_s, 600.0)


class TestPayload(unittest.TestCase):
    def test_text_only(self):
        payload = build_task_payload("m", "hello")
        self.assertEqual(payload["model"], "m")
        self.assertEqual(payload["content"], [{"type": "text", "text": "hello"}])

    def test_image_base64_inline(self):
        payload = build_task_payload("m", "hello", image_b64="aGk=")
        self.assertEqual(payload["content"][1]["type"], "image_url")
        self.assertEqual(payload["content"][1]["image_url"]["url"], "data:image/png;base64,aGk=")
        self.assertEqual(payload["content"][1]["role"], "first_frame")

    def test_video_public_url_reference(self):
        payload = build_task_payload("m", "hello", video_url="https://x/y.mp4")
        self.assertEqual(payload["content"][1]["type"], "video_url")
        self.assertEqual(payload["content"][1]["video_url"]["url"], "https://x/y.mp4")
        self.assertEqual(payload["content"][1]["role"], "reference_video")


class TestResultUrl(unittest.TestCase):
    def test_succeeded(self):
        task = {"status": "succeeded", "content": {"video_url": "https://x/out.mp4"}}
        self.assertEqual(result_video_url(task), "https://x/out.mp4")

    def test_failed_no_content(self):
        self.assertIsNone(result_video_url({"status": "failed"}))


class TestFailClosed(unittest.TestCase):
    def test_missing_key_raises(self):
        with self.assertRaises(ArkError):
            SeedanceClient(SeedanceConfig(env={}))


class TestObjectKey(unittest.TestCase):
    def test_shape(self):
        key = object_key("clip.mp4")
        self.assertTrue(key.startswith("seedance/"))
        self.assertTrue(key.endswith(".mp4"))
        self.assertIn("-", key)


if __name__ == "__main__":
    unittest.main()
