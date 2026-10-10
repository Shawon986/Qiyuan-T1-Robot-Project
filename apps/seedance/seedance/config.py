"""Runtime configuration from environment variables.

The project's .env (D:\\Qiyuan T1 Robotics project\\.env on the dev PC) is loaded
if present; real environment variables always win. On the robot, the skill
runtime supplies the variables directly.
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_API_BASE = "https://ark.ap-southeast.bytepluses.com/api/v3"
DEFAULT_MODEL_ID = "dreamina-seedance-2-0-fast-260128"


def _load_env_file(path: str) -> None:
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and value:
            os.environ.setdefault(key, value)


_load_env_file(os.environ.get("QIYUAN_ENV_FILE", ""))  # explicit override (robot deployment)
_load_env_file(".env")  # current dir (robot board: /home/user/qiyuan-demo/.env)
_load_env_file(r"D:\Qiyuan T1 Robotics project\.env")  # Windows (dev PC)
_load_env_file("/mnt/d/Qiyuan T1 Robotics project/.env")  # WSL view of the same file


class SeedanceConfig:
    """Plain class (not dataclass) so tests can inject a dict as env."""

    def __init__(self, env: dict | None = None) -> None:
        env = dict(os.environ) if env is None else env
        self.api_base = env.get("SEEDANCE_API_BASE", DEFAULT_API_BASE)
        self.api_key = env.get("SEEDANCE_API_KEY", "")
        self.model_id = env.get("SEEDANCE_MODEL_ID", DEFAULT_MODEL_ID)
        self.tos_access_key = env.get("TOS_ACCESS_KEY", "")
        self.tos_secret_key = env.get("TOS_SECRET_KEY", "")
        self.tos_bucket = env.get("TOS_BUCKET", "")
        self.tos_endpoint = env.get("TOS_ENDPOINT", "")
        self.tos_region = env.get("TOS_REGION", "ap-southeast-1")
        # Option A: developer relay inbox (default hosting path, no cloud account needed)
        self.inbox_base = env.get("SEEDANCE_INBOX_BASE", "https://apivmorai.com")
        self.inbox_path = env.get("SEEDANCE_INBOX_PATH", "/sd-inbox-67862519")
        self.poll_interval_s = float(env.get("SEEDANCE_POLL_INTERVAL_S", "5"))
        self.poll_timeout_s = float(env.get("SEEDANCE_POLL_TIMEOUT_S", "600"))
        self.upload_expire_s = int(env.get("SEEDANCE_UPLOAD_EXPIRE_S", "7200"))
        self.uploader_choice = env.get("SEEDANCE_UPLOADER", "")  # ""=auto (TOS first), "tos", "inbox"

    def tos_ready(self) -> bool:
        return bool(self.tos_access_key and self.tos_secret_key and self.tos_bucket)

    def inbox_ready(self) -> bool:
        return bool(self.inbox_base)

    def ready(self) -> bool:
        """True when at least one hosting backend plus the API key are available."""
        return bool(self.api_key and (self.tos_ready() or self.inbox_ready()))
