"""Public, immutable background art; no campaign or uploaded player files."""
from functools import lru_cache
import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from .scenes import SCENES

ASSETS = Path(__file__).resolve().parent / "assets"
CACHE_CONTROL = "public, max-age=31536000, immutable"
router = APIRouter(prefix="/assets/backgrounds")


@lru_cache(maxsize=1)
def artwork_files():
    result = {}
    for scene in SCENES:
        if asset := scene.get("asset"):
            path = ASSETS / asset
            result[asset] = {"path": path, "digest": hashlib.sha256(path.read_bytes()).hexdigest()}
    return result


def artwork_url(asset, base_url=""):
    return f"{base_url.rstrip('/')}/assets/backgrounds/{artwork_files()[asset]['digest']}/{asset}"


@router.get("/{digest}/{filename}")
def background(digest: str, filename: str, request: Request):
    # Only files explicitly named in the public artwork catalogue can be served.
    row = artwork_files().get(filename)
    if row is None or digest != row["digest"]:
        raise HTTPException(404, "Artwork not found")
    headers = {"Cache-Control": CACHE_CONTROL, "ETag": '"' + digest + '"',
               "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}
    if request.headers.get("if-none-match") == headers["ETag"]:
        return Response(status_code=304, headers=headers)
    mime = {".avif": "image/avif", ".webp": "image/webp", ".jpg": "image/jpeg"}[row["path"].suffix]
    return FileResponse(row["path"], media_type=mime, headers=headers)
