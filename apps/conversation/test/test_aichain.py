"""Offline tests for the AIChain client (frames, auth URL, parsing). No network."""
import base64
import hashlib
import json
import unittest

from conversation.aichain import (
    AichainTurn,
    build_append,
    build_session_config,
    build_ws_url,
    chunk_pcm,
    _pcm_to_wav,
)
from conversation.config import ConversationConfig


class TestAuthUrl(unittest.TestCase):
    def test_checksum_is_sha256_appkey_plus_curtime(self):
        cfg = ConversationConfig(env={})
        url = build_ws_url("app123", "key456", "sn1", "wss://aichain-sh.xfyun.cn")
        self.assertIn("/v1/chat/app123?", url)
        self.assertIn("sn=sn1", url)
        # recompute the checksum independently
        params = url.split("?")[1]
        qs = dict(p.split("=") for p in params.split("&"))
        self.assertEqual(qs["checksum"], hashlib.sha256(("key456" + qs["curtime"]).encode()).hexdigest())


class TestSessionConfig(unittest.TestCase):
    def test_shape(self):
        cfg = ConversationConfig(env={})
        msg = build_session_config(cfg, "sid1")
        self.assertEqual(msg["type"], "session.config")
        self.assertEqual(msg["sid"], "sid1")
        c = msg["config"]
        self.assertEqual(c["mode"], "half_duplex")
        self.assertEqual(c["stt"]["sttEngineId"], "5")
        self.assertEqual(c["stt"]["language"], "zh-HK")  # Cantonese
        self.assertEqual(c["tts"]["voices"]["zh-HK"]["voiceId"], "4")  # Cantonese voice key
        self.assertTrue(c["nlu"]["enable"])

    def test_nlu_disabled(self):
        cfg = ConversationConfig(env={"AICHAIN_NLU_ENABLED": "0"})
        c = build_session_config(cfg, "s")["config"]
        self.assertFalse(c["nlu"]["enable"])


class TestAppend(unittest.TestCase):
    def test_text_item(self):
        msg = build_append("s1", "c1", [{"type": "text", "data": "hello"}])
        self.assertEqual(msg["type"], "conversation.user.append")
        self.assertEqual(msg["cid"], "c1")
        self.assertTrue(msg["endFlag"])

    def test_audio_item_base64(self):
        msg = build_append("s1", "c1", [{"type": "audio", "data": "QUJD"}], end_flag=False)
        self.assertFalse(msg["endFlag"])
        self.assertEqual(msg["items"][0]["data"], "QUJD")


class TestWavWrap(unittest.TestCase):
    def test_pcm_to_wav_header(self):
        wav = _pcm_to_wav(b"\x00\x00" * 160)
        self.assertEqual(wav[:4], b"RIFF")
        self.assertEqual(len(wav), 44 + 320)


class TestChunkPcm(unittest.TestCase):
    def test_splits_at_chunk_size(self):
        data = bytes(16000 * 3 + 123)
        chunks = chunk_pcm(data)
        self.assertEqual(len(chunks), 4)
        self.assertTrue(all(len(c) <= 16000 for c in chunks))
        self.assertEqual(b"".join(chunks), data)

    def test_small_audio_is_one_chunk(self):
        data = bytes(8000)
        chunks = chunk_pcm(data)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], data)


class TestTurn(unittest.TestCase):
    def test_defaults(self):
        t = AichainTurn()
        self.assertEqual(t.user_text, "")
        self.assertIsNone(t.audio_wav)


if __name__ == "__main__":
    unittest.main()
