"""Offline tests for the :8766 handler (direct-mode /demo/last JSON + static page)."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from demo_ui import controller, server as server_mod
from demo_ui.server import _last_json_handler_cls


class _ServeCtx:
    """Starts a :8766-style server on an ephemeral port; use as context manager."""

    def __init__(self):
        self.httpd = None

    def __enter__(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _last_json_handler_cls())
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.port = self.httpd.server_address[1]
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()

    def get(self, path: str):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            return r.status, r.read()


class TestLastJsonHandler(unittest.TestCase):
    def test_serves_latest_singleton(self):
        saved = controller.latest.get()
        try:
            controller.latest.set(7, "帮我生成视频", "task-42")
            with _ServeCtx() as srv:
                status, body = srv.get("/demo/last")
            self.assertEqual(status, 200)
            data = json.loads(body.decode("utf-8"))
            self.assertEqual(data["round"], 7)
            self.assertEqual(data["text"], "帮我生成视频")
            self.assertEqual(data["taskId"], "task-42")
            self.assertIn(":", data["time"])  # HH:MM
        finally:
            controller.latest.set(saved["round"], saved["text"], saved["taskId"])


class TestStaticServing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved_pages_dir = server_mod.PAGES_DIR
        server_mod.PAGES_DIR = self.tmp.name
        (Path(self.tmp.name) / "v2-aurora-flow.html").write_text("<html>page</html>", encoding="utf-8")
        (Path(self.tmp.name) / "assets").mkdir()
        (Path(self.tmp.name) / "assets" / "fallback-1.mp4").write_bytes(b"\x00\x00 fake mp4")

    def tearDown(self):
        server_mod.PAGES_DIR = self.saved_pages_dir
        self.tmp.cleanup()

    def test_serves_page_html(self):
        with _ServeCtx() as srv:
            status, body = srv.get("/v2-aurora-flow.html")
        self.assertEqual(status, 200)
        self.assertIn(b"page", body)

    def test_root_serves_default_page(self):
        with _ServeCtx() as srv:
            status, body = srv.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"page", body)

    def test_serves_asset_binary(self):
        with _ServeCtx() as srv:
            status, body = srv.get("/assets/fallback-1.mp4")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"\x00\x00 fake mp4")

    def test_demo_last_still_json_when_pages_configured(self):
        saved = controller.latest.get()
        try:
            controller.latest.set(1, "你好", "t-1")
            with _ServeCtx() as srv:
                status, body = srv.get("/demo/last")
            self.assertEqual(status, 200)
            self.assertIn(b"taskId", body)
        finally:
            controller.latest.set(saved["round"], saved["text"], saved["taskId"])

    def test_path_traversal_blocked(self):
        with _ServeCtx() as srv:
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                srv.get("/../.env")
            self.assertIn(ctx.exception.code, (403, 404))


if __name__ == "__main__":
    unittest.main()
