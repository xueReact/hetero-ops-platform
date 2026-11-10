import mimetypes
from pathlib import Path

from platform_app.config import WEB_DIR, AIRPORT_SITE_DIR


def resolve_static_path(url_path: str) -> Path | None:
    root = WEB_DIR
    if url_path.startswith("/airport-console/view/"):
        root = AIRPORT_SITE_DIR
        relative = url_path.removeprefix("/airport-console/view/") or "index.html"
    else:
        relative = "index.html" if url_path in ("/", "", "/airport-console", "/airport-console/") else url_path.lstrip("/")
    candidate = (root / relative).resolve()
    if candidate != root.resolve() and root.resolve() not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None


def content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"
