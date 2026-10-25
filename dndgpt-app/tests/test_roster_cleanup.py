import copy

import pytest

from app.chat_game import ChatGame, apply_changes
from app.engine import EngineError
from app.mcp_server import rules_page
from .test_chat_game import adventure, save
from .test_sovereign import fixture_state, foundation_request


def test_transient_cleanup_keeps_version_history_and_does_not_spend_time(engine):
    game = ChatGame(engine)
    draft = game.create("owner-a", "Roster cleanup", "roster-cleanup", True)
    state = adventure(game, engine, draft)
    state = save(game, state, {"upsert": {
        "enemies": [{"id": "fallen", "name": "Fallen sentry", "hp": 0},
                    {"id": "survivor", "name": "Surviving sentry", "hp": 2}],
        "summons": [{"id": "expired", "name": "Ended husk", "hp": 0},
                    {"id": "living", "name": "Living husk", "hp": 22, "rounds_remaining": 3}]}})
    before = copy.deepcopy(state)
    result = save(game, state, {"remove": {"enemies": ["fallen"], "summons": ["expired"]},
                               "upsert": {"world_log": [{"id": "aftermath", "text": "The sentry fell; the first husk ended."}]}})
    assert result["fictional_time_seconds"] == before["fictional_time_seconds"]
    assert [row["id"] for row in result["enemies"]] == ["survivor"]
    assert [row["id"] for row in result["summons"]] == ["living"]
    assert result["summons"][0]["rounds_remaining"] == 3
    assert game.version("owner-a", state["id"], state["version"])["campaign"] == before


@pytest.mark.parametrize("group", ["commanders", "formations"])
def test_sovereign_casualty_history_cannot_be_deleted(engine, group):
    state = fixture_state(engine)
    if group == "commanders":
        for formation in state["sovereignty"]["formations"]:
            formation.pop("commander_id", None)
    with pytest.raises(EngineError, match="Retain entity history"):
        apply_changes(state, {"sovereignty": {group: []}})
    changed = copy.deepcopy(state["sovereignty"][group])
    changed[0]["status"] = "dead" if group == "commanders" else "destroyed"
    if group == "formations":
        changed[0]["strength"] = 0
    result = apply_changes(state, {"sovereignty": {group: changed}})
    assert result["sovereignty"][group][0]["id"] == state["sovereignty"][group][0]["id"]


@pytest.mark.parametrize("role", ["domain", "general", "army"])
def test_original_foundation_is_preserved_before_first_upgrade(engine, role):
    state = fixture_state(engine)
    request = foundation_request(state, role)
    result = apply_changes(state, request)
    parent = result["abilities"][0]
    assert parent["base_mechanics_display"] == state["abilities"][0]["mechanics"]
    assert parent["mechanics"] != parent["base_mechanics_display"]
    tampered = {**parent, "base_mechanics_display": "Invented original."}
    again = apply_changes(result, {"upsert": {"abilities": [tampered]}})
    assert again["abilities"][0]["base_mechanics_display"] == parent["base_mechanics_display"]


def test_legacy_combined_foundation_is_not_mislabeled_as_original(engine):
    state = fixture_state(engine)
    request = foundation_request(state, "domain")
    state = apply_changes(state, request)
    state["abilities"][0].pop("base_mechanics_display")
    result = apply_changes(state, {"notes": "Inspection does not reconstruct a starting version."})
    assert "base_mechanics_display" not in result["abilities"][0]


@pytest.mark.parametrize("game", ["age-of-convergence", "sovereign-system"])
def test_cleanup_rules_are_routed_and_hardener_stays_one_page(game):
    section = rules_page("rulebook", 0, "roster-cleanup", game)
    assert "changes.remove.enemies" in section["content"]
    assert "Ending combat alone spends no duration" in section["content"]
    assert "protected" in section["content"].lower()
    checklist = rules_page("hardener", 0, None, game)
    assert "roster-cleanup" in checklist["content"]
    assert checklist["next_offset"] is None
