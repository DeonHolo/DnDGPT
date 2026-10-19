import json
import hashlib
from html.parser import HTMLParser
import pytest

from app.presentation import HERE, dashboard_html
from app.scenes import SCENES, SCENE_IDS
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


def test_every_background_is_embedded_with_attribution_and_a_bounded_resource():
    html = dashboard_html()
    parser = Catalog()
    parser.feed(html)
    catalog = json.loads(parser.content)
    assert len(SCENES) == len(SCENE_IDS) == len(catalog) == 33
    assert catalog[0]["id"] == "classic"
    assert catalog[0]["name"] == "Classic"
    assert catalog[1]["id"] == "quiet"
    assert 'data-scene="classic"' in html
    assert len(html.encode()) < 1024 * 1024
    artworks = [scene for scene in SCENES if scene.get("asset")]
    assert html.count('data:image/avif;base64,') == len(artworks) == 31
    for scene in artworks:
        assert (HERE / "assets" / scene["asset"]).is_file()
        entry = next(item for item in catalog if item["id"] == scene["id"])
        assert all(entry.get(key) for key in ("artist", "title", "source", "license", "license_url"))


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
