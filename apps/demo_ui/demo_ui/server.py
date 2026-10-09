"""Contract v2.0 WebSocket server (robot side) for the exhibition demo.

- Speaks the frozen WS protocol on :8765 (root path: ws://<ip>:8765)
- Optionally serves the exhibition pages (PAGE_DIR / --pages) so the page can
  be opened straight from the robot app: http://<ip>:8765/v2-aurora-flow.html
- Incoming `send` (manual trigger from the page's control panel) starts a round;
  `ping` is answered with `pong`.
"""
from __future__ import annotations

import argparse
import json
import os
import threading
from pathlib import Path

from flask import Flask, send_from_directory

from .controller import DemoController
from .protocol import RoundManager, pong_msg, system_msg

app = Flask(__name__)
sock = None  # set up in main() after the flask_sock import
PAGES_DIR: str | None = None


class WsHub:
    """Tracks connected pages; broadcast drops dead connections silently."""

    def __init__(self) -> None:
        self._clients: list = []
        self._lock = threading.Lock()

    def add(self, ws) -> None:
        with self._lock:
            self._clients.append(ws)

    def remove(self, ws) -> None:
        with self._lock:
            if ws in self._clients:
                self._clients.remove(ws)

    def broadcast(self, msg: dict) -> None:
        data = json.dumps(msg, ensure_ascii=False)
        with self._lock:
            for ws in list(self._clients):
                try:
                    ws.send(data)
                except Exception:
                    self._clients.remove(ws)


hub = WsHub()
rounds = RoundManager(hub.broadcast, timeout_s=float(os.environ.get("ROBOT_ROUND_TIMEOUT_S", "90")))
controller = DemoController(rounds)


@app.route("/health")
def health():
    return {"ok": True, "service": "exhibition-robot-ws", "round": rounds.round}


@app.route("/")
def index():
    """Landing goes straight to the confirmed demo page (v2 aurora flow)."""
    from flask import redirect
    target = os.environ.get("PAGE_INDEX", "v2-aurora-flow.html")
    return redirect(f"/{target}")


@app.route("/<path:filename>")
def pages(filename):
    if not PAGES_DIR:
        return {"error": "no page dir configured"}, 404
    path = Path(PAGES_DIR) / filename
    if not path.is_file():
        return {"error": "not found"}, 404
    return send_from_directory(PAGES_DIR, filename)


def _handle_incoming(raw: str, ws) -> None:
    try:
        msg = json.loads(raw)
    except ValueError:
        return
    mtype = msg.get("type")
    if mtype == "ping":
        try:
            ws.send(json.dumps(pong_msg(), ensure_ascii=False))
        except Exception:
            pass
    elif mtype == "send":
        text = (msg.get("text") or "").strip()
        if text:
            controller.start_round(text)


def main() -> int:
    global sock, PAGES_DIR
    from flask_sock import Sock
    sock = Sock(app)

    @sock.route("/")
    def ws_root(ws):
        hub.add(ws)
        try:
            ws.send(json.dumps(system_msg(True), ensure_ascii=False))
            while True:
                raw = ws.receive(timeout=30)
                if raw:
                    _handle_incoming(raw, ws)
        except Exception:
            pass
        finally:
            hub.remove(ws)

    ap = argparse.ArgumentParser(prog="demo-ui")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--pages", default=None, help="directory with the exhibition HTML pages")
    args = ap.parse_args()
    PAGES_DIR = args.pages or os.environ.get("PAGE_DIR")
    print(f"exhibition WS server on ws://{args.host}:{args.port}  pages_dir={PAGES_DIR or 'off'}")
    app.run(host=args.host, port=args.port, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
