import json
import hashlib
from html.parser import HTMLParser
import pytest

from app.presentation import HERE, dashboard_html
from app.artwork import artwork_url, artwork_files
from app.scenes import SCENES, SCENE_IDS, scene_ids_for_game
from app.engine import EngineError


class Catalog(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_catalog = False
        self.content = ""

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "sceneCatalog":
            self.in_catalog = True

    def handle_data(self, data):
        if self.in_catalog:
            self.content += data

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_catalog = False


def test_every_background_is_linked_with_attribution_and_a_compact_resource():
    html = dashboard_html()
    parser = Catalog()
    parser.feed(html)
    catalog = json.loads(parser.content)
    assert len(SCENES) == len(SCENE_IDS) == len(catalog) == 48
    assert catalog[0]["id"] == "classic"
    assert catalog[0]["name"] == "Classic"
    assert catalog[1]["id"] == "quiet"
    assert 'data-scene="classic"' in html
    assert len(html.encode()) < 300_000
    artworks = [scene for scene in SCENES if scene.get("asset")]
    assert 'data:image/avif;base64,' not in html
    assert len(artworks) == 46
    for scene in artworks:
        assert (HERE / "assets" / scene["asset"]).is_file()
        assert artwork_url(scene["asset"]) in html
        entry = next(item for item in catalog if item["id"] == scene["id"])
        assert all(entry.get(key) for key in ("artist", "title", "source", "license", "license_url"))


def test_original_resolution_wallpapers_are_public_cached_and_byte_exact(web):
    from PIL import Image
    manifest = json.loads((HERE.parents[1] / "docs/ARTWORK_SOURCES.json").read_text(encoding="utf-8"))
    expected = {scene["asset"].split("/")[-1]: (scene["width"], scene["height"])
                for scene in manifest if scene.get("game_id")}
    assert expected["dnd-dalelands.png"] == (4000, 1403)
    for asset, size in expected.items():
        row = artwork_files()[asset]
        with Image.open(row["path"]) as image:
            assert image.size == size
            assert image.width >= 1920 and image.height >= 1080
        path = artwork_url(asset)
        response = web.get(path, headers={"Authorization": ""})
        assert response.status_code == 200
        assert response.content == row["path"].read_bytes()
        assert hashlib.sha256(response.content).hexdigest() == row["digest"]
        assert response.headers["content-type"] == {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}[row["path"].suffix]
        assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert web.get(path, headers={"If-None-Match": response.headers["etag"]}).status_code == 304
        assert web.get(path.replace(row["digest"], "0" * 64)).status_code == 404


def test_artwork_route_never_serves_private_or_uncatalogued_files(web):
    for path in ("/assets/backgrounds/abc/auth.py", "/assets/backgrounds/abc/campaigns.sqlite3",
                 "/assets/backgrounds/abc/..%2Fauth.py", "/assets/backgrounds/abc/layouts/ivy.svg"):
        assert web.get(path).status_code == 404
    assert web.get("/api/campaigns", headers={"Authorization": ""}).status_code == 401


def test_background_urls_are_scoped_to_the_configured_server_origin():
    html = dashboard_html("https://host.example.test")
    for asset in artwork_files():
        assert artwork_url(asset, "https://host.example.test") in html
    assert 'src="https://www.dndbeyond.com' not in html


def test_official_wallpapers_are_available_only_for_dnd_and_keep_copyright():
    official = [scene for scene in SCENES if scene.get("game_id")]
    assert len(official) == 15
    for scene in official:
        assert scene["id"] in scene_ids_for_game("dnd-2024")
        for game in ("age-of-convergence", "sovereign-system"):
            assert scene["id"] not in scene_ids_for_game(game)
        assert scene["license"] == "© Wizards of the Coast"
        assert "Not approved/endorsed" in scene["notice"]
        assert scene["source"].startswith(("https://www.dndbeyond.com/", "https://maihope.artstation.com/", "https://erelmaatita.artstation.com/"))


def test_per_game_atmospheres_remember_choices_and_reject_cross_game_art(engine):
    prefs = {"panels": [], "details": [], "hud_hidden": False,
             "scene": "dnd-dalelands",
             "game_scenes": {"dnd-2024": "dnd-dalelands", "sovereign-system": "glowwood"}}
    engine.set_view_preferences("owner-a", prefs)
    assert engine.get_view_preferences("owner-a") == prefs
    assert "game_scenes" not in engine.get_view_preferences("owner-b")
    for invalid in ([], {"unknown": "classic"}, {"sovereign-system": "dnd-dalelands"},
                    {"dnd-2024": []}):
        with pytest.raises(EngineError):
            engine.set_view_preferences("owner-a", {**prefs, "game_scenes": invalid})
        assert engine.get_view_preferences("owner-a") == prefs


def test_new_scenes_round_trip_per_owner_without_changing_a_campaign(engine, state):
    for scene in SCENE_IDS:
        prefs = {"panels": [], "details": [], "hud_hidden": False, "scene": scene}
        engine.set_view_preferences("owner-a", prefs)
        assert engine.get_view_preferences("owner-a") == prefs
        assert engine.get_view_preferences("owner-b") != prefs
    assert engine.get_campaign("owner-a", state["id"]) == state
    assert engine.audit("owner-a", state["id"])["event_count"] == 1


def test_packaged_art_matches_the_credited_sources_and_readme_count():
    root = HERE.parents[1]
    entries = json.loads((root / "docs/ARTWORK_SOURCES.json").read_text(encoding="utf-8"))
    artworks = [scene for scene in SCENES if scene.get("asset")]
    assert {item["id"] for item in entries} == {scene["id"] for scene in artworks}
    for scene in artworks:
        entry = next(item for item in entries if item["id"] == scene["id"])
        data = (root / entry["asset"]).read_bytes()
        assert len(data) == entry["bytes"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        for key in ("name", "artist", "title", "source", "license", "license_url"):
            assert entry[key] == scene[key]
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert f"**{len(SCENES)} reading atmospheres**" in readme


@pytest.mark.parametrize("scene", [None, [], {}, 1, True, "unknown"])
def test_invalid_atmosphere_preserves_saved_preferences(engine, scene):
    prefs = {"panels": [], "details": [], "hud_hidden": False, "scene": "classic"}
    engine.set_view_preferences("owner-a", prefs)
    with pytest.raises(EngineError):
        engine.set_view_preferences("owner-a", {**prefs, "scene": scene})
    assert engine.get_view_preferences("owner-a") == prefs
