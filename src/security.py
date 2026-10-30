"""Walidacja i czyszczenie danych wejściowych od użytkownika."""
import re
from urllib.parse import parse_qs, urlparse

ALLOWED_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}
MAX_URL_LEN = 300
_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def validate_youtube_url(url: str) -> str | None:
    """Przepuszcza tylko linki do YouTube (watch, youtu.be, Shorts).

    Zwraca znormalizowany adres zbudowany od zera z 11-znakowego ID
    albo None, jeśli link jest niepoprawny. Dzięki temu do modelu nigdy
    nie trafia dowolny adres podany przez użytkownika.
    """
    if not isinstance(url, str) or len(url) > MAX_URL_LEN:
        return None
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
        return None

    video_id = ""
    if parsed.hostname == "youtu.be":
        video_id = parsed.path.lstrip("/")
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    elif parsed.path.startswith("/shorts/"):
        parts = parsed.path.split("/")
        video_id = parts[2] if len(parts) > 2 else ""

    if not _VIDEO_ID.fullmatch(video_id):
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def sanitize_text(text: str, max_len: int) -> str:
    """Usuwa znaki sterujące i przycina tekst do max_len znaków."""
    return _CONTROL_CHARS.sub("", text).strip()[:max_len]
