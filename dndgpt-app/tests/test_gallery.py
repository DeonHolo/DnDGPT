import base64
import io
import json
import socket

import pytest
from PIL import Image

from app.engine import Engine, EngineError
from app.gallery import Gallery, GalleryFile, download_image, image_copy
from app.storage import Store
from .test_server import rpc, tool


def picture(color="green"):
    data = io.BytesIO(); Image.new("RGB", (160, 100), color).save(data, "PNG")
    return data.getvalue()


def upload(gallery, state, action="gallery-first", color="green", **changes):
    args = {"owner": "owner-a", "campaign_id": state["id"], "action_id": action,
            "title": "The crossing", "caption": "A saved scene", "source_kind": "upload",
            "image_data": base64.b64encode(picture(color)).decode()}
    args.update(changes); return gallery.save(**args)


def test_owned_copy_reopens_deduplicates_and_changes_no_gameplay(engine, state):
    gallery = Gallery(engine); before = engine.get_campaign("owner-a", state["id"])
    first = upload(gallery, state); image_id = first["gallery_entry"]["id"]
    assert upload(gallery, state) == first
    assert upload(gallery, state, "new-label", title="Crossing at dawn")["gallery_entry"]["id"] == image_id
    reopened = Gallery(Engine(Store(engine.store.path)))
    items = reopened.list("owner-a", state["id"])["gallery_items"]
    assert len(items) == 1 and items[0]["title"] == "Crossing at dawn"
    assert not any(k in json.dumps(items) for k in ["data:image", "thumbnail"])
    image = reopened.image("owner-a", state["id"], image_id, "full")
    assert set(image) == {"image_id", "_meta"} and image["_meta"]["gallery_image"].startswith("data:image/webp;base64,")
    assert engine.get_campaign("owner-a", state["id"]) == before
    assert gallery.visibility("owner-a", state["id"], image_id, True)["gallery_entry"]["removed"]
    assert not gallery.list("owner-a", state["id"])["gallery_items"]
    assert len(gallery.list("owner-a", state["id"], True)["gallery_items"]) == 1
    gallery.visibility("owner-a", state["id"], image_id, False)
    with pytest.raises(EngineError): reopened.image("owner-b", state["id"], image_id)


def test_native_file_retry_ignores_expiring_download_url(engine, state):
    calls = []; gallery = Gallery(engine, lambda url: calls.append(url) or picture())
    common = dict(owner="owner-a", campaign_id=state["id"], action_id="native-file", title="Generated crossing", source_kind="generated")
    first = gallery.save(**common, file=GalleryFile(download_url="https://files.example/image", file_id="file-abc"))
    assert gallery.save(**common, file=GalleryFile(download_url="https://files.example/refreshed", file_id="file-abc")) == first
    assert calls == ["https://files.example/image"]


def test_automatic_web_curation_has_three_per_scene_limit(engine, state):
    images = iter([picture(c) for c in ["red", "blue", "green", "yellow", "purple"]])
    gallery = Gallery(engine, lambda _: next(images))
    common = dict(owner="owner-a", campaign_id=state["id"], title="World overview", scene_ref="Chapter 1 / crossing",
                  source_url="https://artist.example/scene", credit="Fixture artist", auto_curated=True)
    for i in range(3): gallery.save(**common, action_id="web-image-" + str(i), image_url="https://images.example/" + str(i))
    with pytest.raises(EngineError) as error: gallery.save(**common, action_id="web-four", image_url="https://images.example/4")
    assert error.value.code == "gallery_scene_limit"
    common["auto_curated"] = False
    gallery.save(**common, action_id="manual-extra", image_url="https://images.example/5")
    assert len(gallery.list("owner-a", state["id"])["gallery_items"]) == 4


@pytest.mark.parametrize("url", ["http://example.com/a.png", "file:///secret", "https://user:secret@example.com/x", "https://example.com:444/x"])
def test_invalid_image_url_rejected(url):
    with pytest.raises(EngineError): download_image(url)


def test_private_dns_and_unreadable_images_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(EngineError) as error: download_image("https://internal.example/secret")
    assert error.value.code == "private_image_url"
    with pytest.raises(EngineError): image_copy(b"<svg><script>bad()</script></svg>")


def test_file_tool_schema_and_widget_only_image_bytes(web):
    tools = rpc(web, "tools/list")["tools"]
    entry = next(t for t in tools if t["name"] == "save_gallery_image")
    schema = entry["inputSchema"]["$defs"]["GalleryFile"]
    assert set(schema["required"]) == {"download_url", "file_id"}
    assert set(schema["properties"]) == {"download_url", "file_id", "mime_type", "file_name"}
    assert entry["_meta"]["openai/fileParams"] == ["image"]
    state = tool(web, "create_chat_game", {"name": "Image transport fixture", "action_id": "gallery-create", "disposable": True})["structuredContent"]["campaign"]
    saved = tool(web, "upload_gallery_image", {"campaign_id": state["id"], "action_id": "gallery-upload", "title": "Fixture", "image_data": base64.b64encode(picture()).decode()})
    assert not saved.get("isError"), saved
    image = tool(web, "get_gallery_image", {"campaign_id": state["id"], "image_id": saved["structuredContent"]["gallery_entry"]["id"]})
    assert "gallery_image" in image["_meta"] and "data:image" not in json.dumps(image["structuredContent"])


def test_gallery_roundtrip_through_appwrite_contract():
    from .test_appwrite_hosting import MemoryAPI
    from app.appwrite_store import AppwriteStore
    engine = Engine(AppwriteStore(MemoryAPI())); engine.store.initialize()
    state = engine.create_sandbox("owner-a", "Hosted media fixture", "hosted-media")
    gallery = Gallery(engine); entry = upload(gallery, state)
    assert gallery.image("owner-a", state["id"], entry["gallery_entry"]["id"])["_meta"]["gallery_image"]


def test_campaign_delete_clears_media_and_preserves_retry_tombstones(engine, state):
    from app import records
    from app.campaign_lifecycle import CampaignLifecycle
    from app.game_random import GameRandom
    from app.rules import Dice
    gallery = Gallery(engine); saved = upload(gallery, state)
    rolls = [{"label": "Fixture", "kind": "dice", "sides": 6}]
    box = GameRandom(engine.store, Dice(lambda _: 0), engine)
    box.roll("owner-a", "delete-media-roll", rolls, state["id"])
    lifecycle = CampaignLifecycle(engine)
    preview = lifecycle.preview_delete("owner-a", state["id"], state["version"])
    for _ in range(20):
        result = lifecycle.delete("owner-a", state["id"], state["version"], preview["confirmation_token"], True)
        if not result["cleanup_pending"]: break
    assert result["deleted"]
    with engine.store.transaction() as db:
        for table in ("gallery_entries_v1", "gallery_assets_v1", "gallery_actions_v1"):
            assert not records.find(db, table, {"owner": "owner-a", "campaign_id": state["id"]})
        assert records.get(db, "creations_v1", {"owner": "owner-a", "action_id": "create-action-001"})
        assert records.get(db, "game_rolls_v1", {"owner": "owner-a", "action_id": "delete-media-roll"})
    with pytest.raises(EngineError): gallery.image("owner-a", state["id"], saved["gallery_entry"]["id"])
    with pytest.raises(EngineError): upload(gallery, state)
    with pytest.raises(EngineError): box.roll("owner-a", "delete-media-roll", rolls, state["id"])
