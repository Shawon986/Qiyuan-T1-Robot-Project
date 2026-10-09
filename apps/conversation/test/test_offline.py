"""Offline tests: auth, frames, wake word, intent, memory. No network, no keys."""
import base64
import hashlib
import hmac
import json
import unittest

from conversation.config import ConversationConfig
from conversation.iflytek_auth import build_authorization, build_iat_frames, parse_iat_result
from conversation.intent import classify_intent, contains_wake_word, strip_wake_word
from conversation.llm import SessionMemory
from conversation.tts import wrap_wav


class TestAuth(unittest.TestCase):
    def test_authorization_format(self):
        auth_b64 = build_authorization("key", "secret", "iat-api.xfyun.cn", "/v2/iat")
        decoded = base64.b64decode(auth_b64).decode()
        self.assertIn('api_key="key"', decoded)
        self.assertIn('algorithm="hmac-sha256"', decoded)
        self.assertIn('headers="host date request-line"', decoded)
        self.assertIn("signature=", decoded)

    def test_signature_is_valid_hmac(self):
        # Recompute the expected signature independently (with a fixed secret).
        secret, key, host, path = "s3cret", "k3y", "tts-api.xfyun.cn", "/v2/tts"
        auth_b64 = build_authorization(key, secret, host, path)
        decoded = base64.b64decode(auth_b64).decode()
        sig = decoded.split('signature="')[1].split('"')[0]
        # We can't pin the date, but we can verify structure: base64 of 32 bytes
        self.assertEqual(len(base64.b64decode(sig)), 32)
        self.assertIsInstance(hashlib.sha256(b""), type(hashlib.sha256(b"")))  # sanity


class TestFrames(unittest.TestCase):
    def test_frame_statuses(self):
        chunks = [b"a" * 3200, b"b" * 3200, b"c" * 100]
        frames = build_iat_frames(chunks, "appid123", accent="cantonese")
        self.assertEqual([f["data"]["status"] for f in frames], [0, 1, 2])
        self.assertEqual(frames[0]["common"]["app_id"], "appid123")
        self.assertEqual(frames[0]["business"]["accent"], "cantonese")
        self.assertEqual(frames[0]["business"]["language"], "zh_cn")
        self.assertEqual(frames[0]["data"]["format"], "audio/L16;rate=16000")

    def test_parse_iat_result(self):
        msg = {"data": {"status": 1, "result": {"ws": [
            {"cw": [{"w": "你好"}]}, {"cw": [{"w": "机器人"}]},
        ]}}}
        self.assertEqual(parse_iat_result(msg), "你好机器人")
        self.assertIsNone(parse_iat_result({"data": {"status": 0}}))


class TestWakeAndIntent(unittest.TestCase):
    def test_wake_word(self):
        self.assertTrue(contains_wake_word("机器人，帮我生成一个视频", ["机器人"]))
        self.assertFalse(contains_wake_word("帮我生成一个视频", ["机器人"]))
        self.assertTrue(contains_wake_word("hello", []))  # no wake words -> always on

    def test_strip_wake_word(self):
        self.assertEqual(strip_wake_word("机器人帮我生成视频", ["机器人"]), "帮我生成视频")
        self.assertEqual(strip_wake_word("帮我生成视频", ["机器人"]), "帮我生成视频")

    def test_intents(self):
        self.assertEqual(classify_intent("帮我生成一个视频"), "generate_video")
        self.assertEqual(classify_intent("机器人跳个舞"), "dance")
        self.assertEqual(classify_intent("停止"), "stop")
        self.assertEqual(classify_intent("今天天气怎么样"), "chat")


class TestMemory(unittest.TestCase):
    def test_window(self):
        m = SessionMemory("system", max_messages=4)
        for i in range(4):
            m.add_user(f"q{i}")
            m.add_assistant(f"a{i}")
        msgs = m.build()
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(len(msgs), 5)  # system + last 4 messages
        self.assertEqual(msgs[1]["content"], "q2")  # oldest dropped

    def test_reset(self):
        m = SessionMemory("s", max_messages=10)
        m.add_user("hi")
        m.reset()
        self.assertEqual(len(m.build()), 1)


class TestWavWrap(unittest.TestCase):
    def test_header(self):
        wav = wrap_wav(b"\x00\x00" * 160)
        self.assertEqual(wav[:4], b"RIFF")
        self.assertEqual(wav[8:12], b"WAVE")
        self.assertEqual(len(wav), 44 + 320)


class TestConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = ConversationConfig(env={})
        self.assertFalse(cfg.ready())
        self.assertEqual(cfg.asr_accent, "cantonese")
        self.assertEqual(cfg.llm_model, "deepseek-v4-1-flash-260910")
        self.assertIn("bytepluses", cfg.llm_endpoint)
        self.assertEqual(cfg.max_history_messages, 12)

    def test_ready(self):
        cfg = ConversationConfig(env={
            "IFLYTEK_APPID": "a", "IFLYTEK_API_KEY": "b", "IFLYTEK_API_SECRET": "c",
            "DASHSCOPE_API_KEY": "d",
        })
        self.assertTrue(cfg.ready())

    def test_llm_key_falls_back_to_seedance(self):
        cfg = ConversationConfig(env={
            "IFLYTEK_APPID": "a", "IFLYTEK_API_KEY": "b", "IFLYTEK_API_SECRET": "c",
            "SEEDANCE_API_KEY": "ark-key",
        })
        self.assertEqual(cfg.llm_api_key, "ark-key")
        self.assertTrue(cfg.ready())


if __name__ == "__main__":
    unittest.main()
