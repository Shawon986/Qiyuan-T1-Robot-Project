"""CLI entry point: seedance run --prompt "..." [--video x.mp4] [--image x.png] [--no-wait]"""
from __future__ import annotations

import argparse
import sys

from .client import ArkError, SeedanceClient
from .config import SeedanceConfig
from .pipeline import SeeDancePipeline


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seedance", description="Seedance video generation pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="submit a generation task")
    run.add_argument("--prompt", required=True, help="generation prompt text")
    run.add_argument("--video", default=None, help="local video to upload (goes through BytePlus Object Storage)")
    run.add_argument("--image", default=None, help="local image sent inline as base64 first frame")
    run.add_argument("--no-wait", action="store_true", help="submit only, print task id")

    ns = parser.parse_args(args)
    cfg = SeedanceConfig()
    pipeline = SeeDancePipeline(cfg)
    try:
        if ns.cmd == "run":
            outcome = pipeline.run(ns.prompt, video_path=ns.video, image_path=ns.image, wait=not ns.no_wait)
            print("task_id:", outcome["task_id"])
            print("status:", outcome["status"])
            if outcome["result_url"]:
                print("result_url:", outcome["result_url"])
            return 0
    except ArkError as exc:
        print(f"seedance error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
