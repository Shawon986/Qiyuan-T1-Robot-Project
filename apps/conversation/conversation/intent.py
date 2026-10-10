"""Wake-word detection and intent classification (pure, offline-testable)."""

VIDEO_INTENT_KEYWORDS = [
    # simplified (Mandarin visitors)
    "生成视频", "做个视频", "拍个视频", "制作视频", "视频",
    # traditional (Cantonese visitors) — 2026-10-10: C2 check showed 視頻 was missed
    "生成視頻", "做個視頻", "拍個視頻", "製作視頻", "視頻",
    "generate video", "make a video", "create a video",
]

DANCE_INTENT_KEYWORDS = ["跳舞", "跳支舞", "跳个舞", "dance"]

STOP_INTENT_KEYWORDS = ["停止", "停低", "stop", "取消"]


def contains_wake_word(text: str, wake_words: list[str]) -> bool:
    if not wake_words:
        return True  # no wake words configured -> always listening
    lowered = text.lower()
    return any(w.lower() in lowered for w in wake_words)


def strip_wake_word(text: str, wake_words: list[str]) -> str:
    """Remove leading wake words so the LLM hears the actual question."""
    for w in sorted(wake_words, key=len, reverse=True):
        if text.startswith(w):
            text = text[len(w):]
            break
    return text.strip()


def classify_intent(text: str) -> str:
    """Returns: generate_video | dance | stop | chat"""
    lowered = text.lower()
    if any(k.lower() in lowered for k in STOP_INTENT_KEYWORDS):
        return "stop"
    if any(k.lower() in lowered for k in VIDEO_INTENT_KEYWORDS):
        return "generate_video"
    if any(k.lower() in lowered for k in DANCE_INTENT_KEYWORDS):
        return "dance"
    return "chat"
