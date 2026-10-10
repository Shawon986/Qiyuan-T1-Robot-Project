"""Video hosting backends for the Seedance pipeline.

Two interchangeable uploaders (both return a public URL Ark can download):
  - InboxUploader: PUT the file to the developer's relay inbox — no cloud account
    needed; the server returns a temporary public link (auto-deletes ~2h).
    This is the DEFAULT path (Option A, chosen 2026-10-08).
  - TosUploader: BytePlus Object Storage (S3-compatible) with pre-signed URLs
    (Option B fallback).
"""
from __future__ import annotations

import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import SeedanceConfig


def inbox_object_name(local_path: str | Path) -> str:
    """Unpredictable 128-bit random name with a whitelisted extension."""
    path = Path(local_path)
    suffix = path.suffix or ".mp4"
    return f"{secrets.token_hex(16)}{suffix}"


def inbox_public_url(base: str, inbox_path: str, name: str) -> str:
    """The temporary public link the inbox serves the file from."""
    return f"{base.rstrip('/')}{inbox_path}/{name}"


def object_key(local_path: str | Path, prefix: str = "seedance") -> str:
    """Deterministic, collision-resistant object key: <prefix>/<date>/<name>-<epoch>."""
    path = Path(local_path)
    stamp = time.strftime("%Y%m%d")
    return f"{prefix}/{stamp}/{path.stem}-{int(time.time())}{path.suffix or ''}"


class InboxUploader:
    """Uploads to the developer's relay inbox (plain PUT, no auth by design)."""

    def __init__(self, cfg: SeedanceConfig | None = None) -> None:
        self.cfg = cfg or SeedanceConfig()
        if not self.cfg.inbox_base:
            raise RuntimeError("SEEDANCE_INBOX_BASE is not configured")

    def upload_and_publish(self, local_path: str | Path) -> str:
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(f"video not found: {path}")
        name = inbox_object_name(path)
        url = inbox_public_url(self.cfg.inbox_base, self.cfg.inbox_path, name)
        req = urllib.request.Request(
            url, data=path.read_bytes(), method="PUT",
            headers={"Content-Type": "application/octet-stream"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                if resp.status not in (200, 201, 204):
                    raise RuntimeError(f"inbox upload failed: HTTP {resp.status}")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"inbox upload rejected: HTTP {exc.code}") from exc
        return url


class TosUploader:
    """BytePlus Object Storage (S3-compatible) uploader with pre-signed URLs."""

    def __init__(self, cfg: SeedanceConfig | None = None) -> None:
        self.cfg = cfg or SeedanceConfig()
        if not self.cfg.tos_ready():
            raise RuntimeError(
                "TOS credentials not configured (TOS_ACCESS_KEY/TOS_SECRET_KEY/TOS_BUCKET)"
            )
        import boto3  # lazy import keeps offline unit tests dependency-free
        from botocore.config import Config as BotoConfig
        self._s3 = boto3.client(
            "s3",
            aws_access_key_id=self.cfg.tos_access_key,
            aws_secret_access_key=self.cfg.tos_secret_key,
            endpoint_url=self.cfg.tos_endpoint,
            region_name=self.cfg.tos_region,
            config=BotoConfig(
                signature_version="s3v4",
                # Live-verified 2026-10-10: this bucket requires VIRTUAL-hosted style;
                # path-style PUTs fail with InvalidPathAccess.
                s3={"addressing_style": "virtual"},
            ),
        )

    def upload_and_publish(self, local_path: str | Path) -> str:
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(f"video not found: {path}")
        key = object_key(path)
        self._s3.upload_file(str(path), self.cfg.tos_bucket, key)
        return self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.cfg.tos_bucket, "Key": key},
            ExpiresIn=self.cfg.upload_expire_s,
        )


def create_uploader(cfg: SeedanceConfig | None = None):
    """Factory: TOS (our own BytePlus bucket) first since 2026-10-10 — the
    developer's inbox was removed from their server (HTTP 404). Inbox stays as
    fallback. SEEDANCE_UPLOADER=inbox|tos overrides."""
    cfg = cfg or SeedanceConfig()
    choice = cfg.uploader_choice
    if choice == "inbox":
        if cfg.inbox_ready():
            return InboxUploader(cfg)
        raise RuntimeError("SEEDANCE_UPLOADER=inbox but inbox not configured")
    if choice == "tos":
        if cfg.tos_ready():
            return TosUploader(cfg)
        raise RuntimeError("SEEDANCE_UPLOADER=tos but TOS credentials not configured")
    if cfg.tos_ready():
        return TosUploader(cfg)
    if cfg.inbox_ready():
        return InboxUploader(cfg)
    raise RuntimeError(
        "no video-hosting backend configured (set TOS_* credentials or SEEDANCE_INBOX_BASE)"
    )
