"""Owned image copies, kept outside gameplay saves and model-visible image payloads."""
import base64
import hashlib
import http.client
import io
import ipaddress
import json
import socket
import ssl
import time
import warnings
from urllib.parse import urljoin, urlsplit

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict

from . import records
from .engine import fail, identifier
from .storage import canonical

MAX_DOWNLOAD = 8 * 1024 * 1024
MAX_IMAGES = 120


class GalleryFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    download_url: str
    file_id: str
    mime_type: str = ""
    file_name: str = ""


def https_url(value):
    if type(value) is not str or not 1 <= len(value) <= 5000:
        fail(422, "invalid_image_url", "Use an HTTPS image URL")
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == "https" and parsed.hostname and not parsed.username and
                 not parsed.password and parsed.port in (None, 443) and not parsed.fragment)
    except ValueError:
        valid = False
    if not valid:
        fail(422, "invalid_image_url", "Use a public HTTPS URL without credentials")
    return parsed


def download_image(url):
    """Resolve and pin a public IP for every hop; never forward host credentials."""
    for _ in range(4):
        parsed = https_url(url)
        connection = None
        try:
            addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
                fail(422, "private_image_url", "Image imports need a publicly reachable image host")
            address = next((row[4][0] for row in addresses if row[0] == socket.AF_INET), addresses[0][4][0])

            class PinnedHTTPS(http.client.HTTPSConnection):
                def connect(self):
                    raw = socket.create_connection((address, 443), timeout=10)
                    try:
                        self.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=parsed.hostname)
                    except BaseException:
                        raw.close()
                        raise

            connection = PinnedHTTPS(parsed.hostname, timeout=10)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            connection.request("GET", path, headers={"Accept": "image/*", "User-Agent": "DnDGPT-Gallery/1.0"})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                target = response.getheader("Location")
                if not target:
                    break
                url = urljoin(url, target)
                continue
            if response.status != 200:
                fail(422, "image_download_failed", "That image could not be downloaded; use its direct image URL or upload the file")
            length = response.getheader("Content-Length")
            if length and int(length) > MAX_DOWNLOAD:
                fail(413, "image_too_large", "Images can be at most 8 MB")
            data = response.read(MAX_DOWNLOAD + 1)
            if len(data) > MAX_DOWNLOAD:
                fail(413, "image_too_large", "Images can be at most 8 MB")
            return data
        except (OSError, ValueError, http.client.HTTPException):
            fail(422, "image_download_failed", "The image host could not be reached securely; try uploading the file")
        finally:
            if connection:
                connection.close()
    fail(422, "image_redirect_limit", "Image URL redirects too many times")


def image_copy(data):
    if not data or len(data) > MAX_DOWNLOAD:
        fail(413, "image_too_large", "Use an image of at most 8 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as original:
                if original.format not in {"PNG", "JPEG", "WEBP", "GIF", "AVIF"} or original.width * original.height > 20000000:
                    fail(422, "unsupported_gallery_image", "Use a PNG, JPEG, WebP, GIF or AVIF image under 20 megapixels")
                image = ImageOps.exif_transpose(original).convert("RGBA")
                image.thumbnail((2048, 2048))
                output = io.BytesIO()
                for quality in (85, 70, 50):
                    output = io.BytesIO()
                    image.save(output, "WEBP", quality=quality, method=3)
                    if output.tell() <= 750000:
                        break
                if output.tell() > 750000:
                    fail(413, "image_too_complex", "Try a smaller image for the gallery")
                small = image.copy()
                small.thumbnail((400, 400))
                thumb = io.BytesIO()
                small.save(thumb, "WEBP", quality=75, method=3)
                return {"mime_type": "image/webp", "width": image.width, "height": image.height,
                        "sha256": hashlib.sha256(output.getvalue()).hexdigest(),
                        "data": base64.b64encode(output.getvalue()).decode(),
                        "thumbnail": base64.b64encode(thumb.getvalue()).decode()}
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        fail(422, "unsupported_gallery_image", "The file is not a supported readable image")


class Gallery:
    def __init__(self, engine, downloader=None):
        self.engine, self.store = engine, engine.store
        self.downloader = downloader or download_image

    def list(self, owner, campaign_id, include_removed=False):
        with self.store.transaction() as db:
            self.engine._get(db, owner, campaign_id)
            rows = records.find(db, "gallery_entries_v1", {"owner": owner, "campaign_id": campaign_id},
                                order="created_at", descending=True, limit=MAX_IMAGES + 1)
            items = [json.loads(row["data"]) for row in rows]
        return {"campaign_id": campaign_id, "gallery_items": [item for item in items if include_removed or not item.get("removed")]}

    def save(self, owner, campaign_id, action_id, title, caption="", source_kind="web", source_url="",
             credit="", scene_ref="", auto_curated=False, image_url=None, file=None, image_data=None):
        identifier(action_id, "action_id")
        for value, maximum in ((title, 160), (caption, 1200), (credit, 400), (scene_ref, 160)):
            if type(value) is not str or len(value) > maximum:
                fail(422, "invalid_gallery_entry", "Use a short title, caption, credit and scene label")
        if not title.strip() or source_kind not in {"web", "generated", "upload"} or type(auto_curated) is not bool:
            fail(422, "invalid_gallery_entry", "An image needs a title and valid source kind")
        if source_url:
            https_url(source_url)
        if auto_curated and (source_kind != "web" or not scene_ref.strip()):
            fail(422, "invalid_gallery_entry", "Automatic curation needs a web image and the established scene/overview label")
        if sum(value is not None for value in (image_url, file, image_data)) != 1:
            fail(422, "invalid_gallery_image", "Provide one image URL, ChatGPT file or upload")
        if image_data is not None and (type(image_data) is not str or len(image_data) > 2000000):
            fail(413, "image_too_large", "Upload a smaller image")
        if file is not None and (not file.file_id or len(file.file_id) > 200):
            fail(422, "invalid_gallery_image", "Use an available ChatGPT image file")
        source = {"image_url": image_url} if image_url is not None else (
            {"file_id": file.file_id} if file is not None else {"upload_hash": hashlib.sha256(image_data.encode()).hexdigest()})
        args = {"campaign_id": campaign_id, "title": title, "caption": caption, "source_kind": source_kind,
                "source_url": source_url, "credit": credit, "scene_ref": scene_ref, "auto_curated": auto_curated, **source}
        request = canonical(args)
        key = {"owner": owner, "action_id": action_id}
        with self.store.transaction() as db:
            self.engine._get(db, owner, campaign_id)
            previous = records.get(db, "gallery_actions_v1", key)
            if previous:
                if previous["request"] != request:
                    fail(409, "idempotency_conflict", "Gallery action_id already has different arguments")
                return json.loads(previous["result"])
        if image_data is not None:
            if type(image_data) is not str or len(image_data) > 2000000:
                fail(413, "image_too_large", "Upload a smaller image")
            try:
                data = base64.b64decode(image_data.split(",", 1)[-1], validate=True)
            except ValueError:
                fail(422, "invalid_gallery_image", "Upload data is not valid base64")
        else:
            data = self.downloader(file.download_url if file is not None else image_url)
        asset = image_copy(data)
        image_id = hashlib.sha256(canonical([owner, campaign_id, asset["sha256"]]).encode()).hexdigest()[:32]
        with self.store.transaction() as db:
            self.engine._get(db, owner, campaign_id)
            previous = records.get(db, "gallery_actions_v1", key)
            if previous:
                if previous["request"] != request:
                    fail(409, "idempotency_conflict", "Gallery action_id already has different arguments")
                return json.loads(previous["result"])
            entries = records.find(db, "gallery_entries_v1", {"owner": owner, "campaign_id": campaign_id}, limit=MAX_IMAGES + 1)
            existing = next((row for row in entries if row["id"] == image_id), None)
            if not existing and len(entries) >= MAX_IMAGES:
                fail(409, "gallery_full", "This campaign gallery has reached 120 saved images")
            if auto_curated and not existing and sum(json.loads(row["data"]).get("auto_curated") and
                    json.loads(row["data"]).get("scene_ref") == scene_ref for row in entries) >= 3:
                fail(409, "gallery_scene_limit", "Keep up to three automatically curated images per scene or overview")
            old = json.loads(existing["data"]) if existing else {}
            entry = {"id": image_id, "title": title.strip(), "caption": caption, "source_kind": source_kind,
                     "source_url": source_url, "credit": credit, "scene_ref": scene_ref,
                     "auto_curated": auto_curated, "removed": False, "created_at": old.get("created_at", time.time()),
                     **{k: asset[k] for k in ("width", "height", "sha256", "mime_type")}}
            if file is not None:
                entry["file_id"] = file.file_id
            where = {"owner": owner, "id": image_id}
            records.upsert(db, "gallery_entries_v1", where, {"campaign_id": campaign_id,
                           "created_at": entry["created_at"], "data": canonical(entry)})
            if not existing:
                records.insert(db, "gallery_assets_v1", {**where, "campaign_id": campaign_id, "data": canonical(asset)})
            result = {"campaign_id": campaign_id, "gallery_entry": entry, "gameplay_changed": False}
            records.insert(db, "gallery_actions_v1", {**key, "campaign_id": campaign_id, "request": request, "result": canonical(result)})
            return result

    def image(self, owner, campaign_id, image_id, size="thumbnail"):
        if size not in {"thumbnail", "full"}:
            fail(422, "invalid_gallery_size", "Choose thumbnail or full")
        with self.store.transaction() as db:
            self.engine._get(db, owner, campaign_id)
            row = records.get(db, "gallery_assets_v1", {"owner": owner, "id": image_id})
            if not row or row["campaign_id"] != campaign_id:
                fail(404, "gallery_image_not_found", "Gallery image not found")
            asset = json.loads(row["data"])
        return {"image_id": image_id, "_meta": {"gallery_image": "data:" + asset["mime_type"] + ";base64," + asset["data" if size == "full" else "thumbnail"]}}

    def visibility(self, owner, campaign_id, image_id, removed):
        if type(removed) is not bool:
            fail(422, "invalid_gallery_entry", "removed must be boolean")
        with self.store.transaction() as db:
            self.engine._get(db, owner, campaign_id)
            key = {"owner": owner, "id": image_id}
            row = records.get(db, "gallery_entries_v1", key)
            if not row or row["campaign_id"] != campaign_id:
                fail(404, "gallery_image_not_found", "Gallery image not found")
            entry = json.loads(row["data"])
            entry["removed"] = removed
            records.update(db, "gallery_entries_v1", key, {"data": canonical(entry)})
        return {"campaign_id": campaign_id, "gallery_entry": entry, "gameplay_changed": False}
