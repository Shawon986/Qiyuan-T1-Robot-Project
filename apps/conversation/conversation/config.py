"""Runtime configuration from environment variables (same .env pattern as seedance)."""
from __future__ import annotations

import os
from pathlib import Path


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


_load_env_file(r"D:\Qiyuan T1 Robotics project\.env")
_load_env_file("/mnt/d/Qiyuan T1 Robotics project/.env")


class ConversationConfig:
    def __init__(self, env: dict | None = None) -> None:
        env = dict(os.environ) if env is None else env
        # iFlytek (Cantonese ASR + TTS)
        self.iflytek_appid = env.get("IFLYTEK_APPID", "")
        self.iflytek_api_key = env.get("IFLYTEK_API_KEY", "")
        self.iflytek_api_secret = env.get("IFLYTEK_API_SECRET", "")
        self.asr_accent = env.get("IFLYTEK_ASR_ACCENT", "cantonese")  # 粤语
        self.tts_voice = env.get("IFLYTEK_TTS_VOICE", "x_xiaoyan")  # set to a Cantonese voice code
        # LLM: default = DeepSeek V4.1 Flash on the user's existing BytePlus ModelArk account
        # (no separate Aliyun/DashScope account needed). Any OpenAI-compatible endpoint works.
        self.llm_endpoint = env.get(
            "LLM_ENDPOINT", "https://ark.ap-southeast.bytepluses.com/api/v3/chat/completions"
        )
        self.llm_model = env.get("LLM_MODEL", "deepseek-v4-1-flash-260910")
        self.llm_api_key = (
            env.get("LLM_API_KEY")
            or env.get("DASHSCOPE_API_KEY")
            or env.get("SEEDANCE_API_KEY", "")
        )
        # Behavior
        self.wake_words = [w for w in env.get("WAKE_WORDS", "机器人").split(",") if w]
        self.system_prompt = env.get(
            "ROBOT_SYSTEM_PROMPT",
            "你是启元机器人（Qiyuan），一位友善的粤语机器人助手。用简短自然的粤语回答，"
            "语气亲切，回复控制在两三句以内。",
        )
        self.max_history_messages = int(env.get("MAX_HISTORY_MESSAGES", "12"))
        # Dialogue event API (the demo session API)
        self.dialogue_api_base = env.get("DIALOGUE_API_BASE", "http://127.0.0.1:8765")

    def ready(self) -> bool:
        return bool(
            self.iflytek_appid and self.iflytek_api_key
            and self.iflytek_api_secret and self.llm_api_key
        )
