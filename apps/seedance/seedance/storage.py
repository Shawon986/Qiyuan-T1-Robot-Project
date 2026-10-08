"""BytePlus Object Storage (TOS, S3-compatible) video uploader.

Uploads the robot-recorded video and returns a time-limited pre-signed URL that
the ModelArk generation API can fetch (videos require a public URL - verified).
"""
from __future__ import annotations

import time
from pathlib import Path

from .config import SeedanceConfig


def object_key(local_path: str | Path, prefix: str = "seedance") -> str:
    """Deterministic, collision-resistant object key: <prefix>/<date>/<name>-<epoch>."""
    path = Path(local_path)
    stamp = time.strftime("%Y%m%d")
    return f"{prefix}/{stamp}/{path.stem}-{int(time.time())}{path.suffix or ''}"


class StorageUploader:
    def __init__(self, cfg: SeedanceConfig | None = None) -> None:
        self.cfg = cfg or SeedanceConfig()
        if not (self.cfg.tos_access_key and self.cfg.tos_secret_key and self.cfg.tos_bucket):
            raise RuntimeError("TOS credentials not configured (check .env: TOS_ACCESS_KEY/TOS_SECRET_KEY/TOS_BUCKET)")
        import boto3  # lazy import keeps offline unit tests dependency-free
        from botocore.config import Config as BotoConfig
        self._s3 = boto3.client(
            "s3",
            aws_access_key_id=self.cfg.tos_access_key,
            aws_secret_access_key=self.cfg.tos_secret_key,
            endpoint_url=self.cfg.tos_endpoint,
            region_name=self.cfg.tos_region,
            config=BotoConfig(signature_version="s3v4"),
        )

    def upload_video(self, local_path: str | Path, key: str | None = None) -> str:
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(f"video not found: {path}")
        key = key or object_key(path)
        self._s3.upload_file(str(path), self.cfg.tos_bucket, key)
        return key

    def presigned_url(self, key: str, expires: int | None = None) -> str:
        return self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.cfg.tos_bucket, "Key": key},
            ExpiresIn=expires if expires is not None else self.cfg.upload_expire_s,
        )

    def upload_and_publish(self, local_path: str | Path) -> str:
        """Upload the video and return a public URL Ark can download."""
        key = self.upload_video(local_path)
        return self.presigned_url(key)
