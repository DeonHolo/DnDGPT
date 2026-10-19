"""Layout preferences persist per player without touching campaign records."""
import pytest

from app.engine import EngineError
from app.presentation import dashboard_html


def test_layouts_round_trip_independently_from_atmosphere(engine, state):
    before = engine.audit("owner-a", state["id"])
    for layout in ("original", "reclaimed", "orrery", "ember"):
        prefs = {"panels": ["skills"], "details": ["character-story"],
                 "hud_hidden": False, "scene": "classic", "layout": layout,
                 "ambient_motion": False}
        engine.set_view_preferences("owner-a", prefs)
        assert engine.get_view_preferences("owner-a") == prefs
        assert engine.get_view_preferences("owner-b") != prefs
    assert engine.get_campaign("owner-a", state["id"]) == state
    assert engine.audit("owner-a", state["id"]) == before


@pytest.mark.parametrize("key,value", [("layout", "unknown"), ("layout", []),
    ("layout", None), ("layout", True), ("ambient_motion", 1),
    ("ambient_motion", "false"), ("ambient_motion", None)])
def test_invalid_layout_preferences_do_not_overwrite_saved_choices(engine, key, value):
    prefs = {"panels": [], "details": [], "hud_hidden": False, "scene": "classic"}
    engine.set_view_preferences("owner-a", prefs)
    with pytest.raises(EngineError):
        engine.set_view_preferences("owner-a", {**prefs, key: value})
    assert engine.get_view_preferences("owner-a") == prefs


def test_layout_resource_is_self_contained_and_keeps_original_as_default():
    html = dashboard_html()
    assert 'data-layout="original"' in html
    assert html.count('data:image/svg+xml;base64,') == 4
    assert "/* dashboard layouts */" not in html
    assert "Local preview. Actions are not sent." not in html
    assert "The Greenwater Crossing" not in html
