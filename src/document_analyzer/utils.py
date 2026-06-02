import re


def _shorten_text(text: str, limit: int) -> str:
    """Shorten text to a specific limit, ensuring it ends cleanly."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
