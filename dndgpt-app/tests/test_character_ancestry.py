import copy

import pytest

from app.chat_game import ChatGame, apply_changes
from app.engine import EngineError
from app.mcp_server import rules_page


def test_ancestry_is_saved_and_retrieved_without_changing_mechanics(engine):
    game = ChatGame(engine)
    state = game.create("owner-a", "Ancestry fixture", "ancestry-create", True)
    before = copy.deepcopy(state)
    args = ("owner-a", state["id"], "ancestry-description", state["version"], "Save chosen race",
            {"character": {"ancestry": "Fixture nonhuman people", "ancestry_description":
             "An upright two-legged people with ridged ears and speckled gray skin, native to the crossing."}})
    saved = game.update(*args)["campaign"]
    assert game.update(*args)["campaign"] == saved
    assert engine.get_campaign("owner-a", state["id"])["character"]["ancestry"] == "Fixture nonhuman people"
    assert saved["fictional_time_seconds"] == before["fictional_time_seconds"] == 0
    assert saved["paused"] and saved["phase"] == before["phase"]
    for key in ("attributes", "hp", "mp", "rarity", "class_name", "level", "skill_points"):
        assert saved["character"][key] == before["character"][key]
    assert "ancestry" not in before["character"]  # Unknown is not assigned Human.


def test_new_identity_sections_preserve_creation_and_known_names():
    ancestry = rules_page("rulebook", 0, "ancestry")["content"]
    clarity = rules_page("rulebook", 0, "clear-story")["content"]
    assert "four creation turns" in ancestry and "not automatically human" in ancestry
    assert "preserving established events" in ancestry
    assert "ONE new important proper name" in clarity and "required creation/advancement offer counts" in clarity


def test_ancestry_rejects_nontext_and_preserves_input(engine):
    state = ChatGame(engine).create("owner-a", "Identity validation", "identity-validation", True)
    before = copy.deepcopy(state)
    with pytest.raises(EngineError): apply_changes(state, {"character": {"ancestry": {"name": "Invalid shape"}}})
    assert state == before
