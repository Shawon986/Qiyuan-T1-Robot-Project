"""Offline test for the :8766 /demo/last handler (direct mode robotUrl poll)."""
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from demo_ui import controller
from demo_ui.server import _last_json_handler_cls


class TestLastJsonHandler(unittest.TestCase):
    def test_serves_latest_singleton(self):
        saved = controller.latest.get()
        try:
            controller.latest.set(7, "帮我生成视频", "task-42")
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), _last_json_handler_cls())
            port = httpd.server_address[1]
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/demo/last", timeout=5) as resp:
                    self.assertEqual(resp.status, 200)
                    data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["round"], 7)
                self.assertEqual(data["text"], "帮我生成视频")
                self.assertEqual(data["taskId"], "task-42")
                self.assertIn(":", data["time"])  # HH:MM
            finally:
                httpd.shutdown()
                httpd.server_close()
        finally:
            controller.latest.set(saved["round"], saved["text"], saved["taskId"])


if __name__ == "__main__":
    unittest.main()
