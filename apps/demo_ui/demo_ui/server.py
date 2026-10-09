"""Session API server (no UI): the developer's page polls GET /api/session.

Run: demo-ui --host 0.0.0.0 --port 8765
CORS is enabled so the page can poll from any origin.
"""
from __future__ import annotations

import argparse

from flask import Flask, jsonify, request

from .events import state

app = Flask(__name__)


@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "demo-session-api"})


@app.route("/api/session", methods=["GET"])
def session():
    return jsonify(state.snapshot())


@app.route("/api/events", methods=["POST", "OPTIONS"])
def events():
    """Optional: a separate robot-app process can push events here."""
    if request.method == "OPTIONS":
        return ("", 204)
    body = request.get_json(silent=True) or {}
    kind = body.get("kind")
    if not kind:
        return jsonify({"error": "missing kind"}), 400
    try:
        state.handle(kind, **{k: v for k, v in body.items() if k != "kind"})
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


def main() -> int:
    ap = argparse.ArgumentParser(prog="demo-ui")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    print(f"session API on http://{args.host}:{args.port}/api/session")
    app.run(host=args.host, port=args.port, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
