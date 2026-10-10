"""Offline tests: payload building, config parsing, key/URL helpers. No network, no keys."""
import unittest

from seedance.client import ArkError, SeedanceClient, build_task_payload, result_video_url
from seedance.config import SeedanceConfig
from seedance.storage import create_uploader, inbox_object_name, inbox_public_url, object_key

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


class TestInbox(unittest.TestCase):
    def test_random_name_shape(self):
        name = inbox_object_name("clip.mp4")
        self.assertTrue(name.endswith(".mp4"))
        self.assertEqual(len(name), 32 + 4)  # 128-bit hex + extension

    def test_unpredictable_names(self):
        self.assertNotEqual(inbox_object_name("a.mp4"), inbox_object_name("a.mp4"))

    def test_public_url_join(self):
        url = inbox_public_url("https://apivmorai.com", "/sd-inbox-67862519", "abc.mp4")
        self.assertEqual(url, "https://apivmorai.com/sd-inbox-67862519/abc.mp4")


class TestUploaderFactory(unittest.TestCase):
    def test_inbox_used_when_tos_unconfigured(self):
        from seedance.storage import InboxUploader
        uploader = create_uploader(SeedanceConfig(env={"SEEDANCE_INBOX_BASE": "https://x.com"}))
        self.assertIsInstance(uploader, InboxUploader)

    def test_tos_preferred_over_inbox(self):
        from seedance.storage import TosUploader
        env = {**FAKE_ENV, "SEEDANCE_INBOX_BASE": "https://x.com"}
        uploader = create_uploader(SeedanceConfig(env=env))
        self.assertIsInstance(uploader, TosUploader)

    def test_uploader_env_override_forces_inbox(self):
        from seedance.storage import InboxUploader
        env = {**FAKE_ENV, "SEEDANCE_INBOX_BASE": "https://x.com",
               "SEEDANCE_UPLOADER": "inbox"}
        uploader = create_uploader(SeedanceConfig(env=env))
        self.assertIsInstance(uploader, InboxUploader)

    def test_no_backend_raises(self):
        with self.assertRaises(RuntimeError):
            create_uploader(SeedanceConfig(env={"SEEDANCE_INBOX_BASE": ""}))


if __name__ == "__main__":
    unittest.main()
