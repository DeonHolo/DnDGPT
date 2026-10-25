import copy

import pytest

from app import records
from app.campaign_archive import CampaignArchive, digest, validate_archive
from app.campaign_focus import DEFAULTS
from app.chat_game import ChatGame, apply_changes
from app.continuity import model_view
from app.engine import EngineError, public_state
from app.game_profiles import AGE, SOVEREIGN
from app.mcp_server import rules_page
from app.storage import canonical
from .test_campaign_life import seed, save, quest
from .test_server import tool


@pytest.mark.parametrize("game", [AGE, SOVEREIGN])
def test_preferences_merge_retry_and_keep_existing_gameplay(engine, game):
    state = seed(engine, game)
    first = {"campaign_preferences": {"focus": "conquest"}}
    result = ChatGame(engine).update("owner-a", state["id"], "focus-once", state["version"], "Choose conquest", first)
    assert ChatGame(engine).update("owner-a", state["id"], "focus-once", state["version"], "Choose conquest", first) == result
    changed = result["campaign"]
    assert changed["version"] == state["version"] + 1
    assert changed["campaign_preferences"] == {"focus": "conquest", "dialogue": "normal"}
    changed = save(engine, changed, {"campaign_preferences": {"dialogue": "on-request"}})
    assert changed["campaign_preferences"] == {"focus": "conquest", "dialogue": "on-request"}
    for key in ("game_id", "character", "equipment", "abilities", "quest_log", "world", "phase", "paused", "fictional_time_seconds"):
        assert changed[key] == state[key]
    if game == SOVEREIGN:
        assert changed["sovereignty"] == state["sovereignty"]
    changed = save(engine, changed, {"notes": "A normal authorized scene update"})
    assert changed["campaign_preferences"]["focus"] == "conquest"
    for view in ("full", "turn", "resume"):
        shown = model_view(changed, view)
        prefs = shown["resume_brief"]["campaign_preferences"] if view == "resume" else shown["campaign_preferences"]
        assert prefs == {"focus": "conquest", "dialogue": "on-request"}


@pytest.mark.parametrize("phase,paused,frozen", [("character_draft", True, False), ("ready", True, False),
                                               ("adventure", True, False), ("adventure", False, True)])
def test_preference_only_change_never_resumes_or_bypasses_other_guards(engine, phase, paused, frozen):
    state = seed(engine)
    state.update(phase=phase, paused=paused, level_up_freeze=frozen)
    with engine.store.transaction() as db:
        records.update(db, "campaigns_v1", {"id": state["id"]}, {"data": canonical(state)})
    changed = save(engine, state, {"campaign_preferences": {"focus": "hunt-explore", "dialogue": "minimal"}})
    assert (changed["phase"], changed["paused"], changed["level_up_freeze"]) == (phase, paused, frozen)
    assert changed["fictional_time_seconds"] == 0
    if phase == "adventure" and paused:
        with pytest.raises(EngineError, match="Resume explicitly"):
            save(engine, changed, {"campaign_preferences": {"focus": "mixed"}, "character": {"hp": 1}})
    with pytest.raises(EngineError):
        save(engine, changed, {"fictional_time_seconds": 1})


@pytest.mark.parametrize("value", [None, [], {}, {"focus": "politics"}, {"focus": []}, {"dialogue": True},
                                    {"dialogue": "never"}, {"focus": "mixed", "paused": False}])
def test_bad_preferences_fail_atomically(engine, value):
    state = seed(engine)
    before = copy.deepcopy(engine.get_campaign("owner-a", state["id"]))
    with pytest.raises(EngineError, match="Use focus="):
        save(engine, state, {"campaign_preferences": value, "character": {"hp": 1}})
    assert engine.get_campaign("owner-a", state["id"]) == before


def test_legacy_defaults_are_read_only_and_portable(engine):
    state = seed(engine)
    state.pop("campaign_preferences", None)
    before = copy.deepcopy(state)
    assert public_state(state)["campaign_preferences"] == DEFAULTS
    assert state == before
    changed = apply_changes(state, {"campaign_preferences": {"dialogue": "minimal"}})
    assert changed["campaign_preferences"] == {"focus": "mixed", "dialogue": "minimal"}
    with engine.store.transaction() as db:
        records.update(db, "campaigns_v1", {"id": state["id"]}, {"data": canonical(changed)})
    archive = CampaignArchive(engine).export("owner-a", state["id"])["archive"]
    restored = validate_archive(archive)
    assert restored["campaign_preferences"] == changed["campaign_preferences"]
    archive["campaign"]["campaign_preferences"]["focus"] = "unknown"
    archive["sha256"] = digest(archive["campaign"])
    with pytest.raises(EngineError):
        validate_archive(archive)


def test_preference_changes_keep_owner_version_and_history_guards(web):
    state = tool(web, "create_chat_game", {"name": "Focus fixture", "action_id": "focus-create", "disposable": True})["structuredContent"]["campaign"]
    args = {"campaign_id": state["id"], "action_id": "focus-choice", "expected_version": state["version"],
            "summary": "Choose a hunting campaign", "changes": {"campaign_preferences": {"focus": "hunt-explore", "dialogue": "minimal"}}}
    result = tool(web, "save_chat_update", args)
    assert not result.get("isError"), result
    assert result["structuredContent"]["campaign"]["campaign_preferences"]["dialogue"] == "minimal"
    assert tool(web, "save_chat_update", {**args, "action_id": "focus-stale"}).get("isError")
    assert tool(web, "save_chat_update", {**args, "campaign_id": "chat-other-owner"}).get("isError")


@pytest.mark.parametrize("game", [AGE, SOVEREIGN])
def test_activity_completion_keeps_rewards_once_and_finishes(engine, game):
    state = seed(engine, game)
    q = {**quest(), "activity": "conquest", "target": "The quarry", "known_opposition": "A raider camp",
         "victory_benefit": "The quarry road becomes usable"}
    state = save(engine, state, {"campaign_preferences": {"focus": "conquest", "dialogue": "minimal"}, "upsert": {"quest_log": [q]}})
    q = copy.deepcopy(state["quest_log"][0]);q["objectives"][0]["status"] = "done"
    state = save(engine, state, {"upsert": {"quest_log": [q]}})
    assert state["quest_log"][0]["status"] == "completed" and state["funds"]["silver"] == 5
    state = save(engine, state, {"campaign_preferences": {"focus": "hunt-explore"}})
    assert state["funds"]["silver"] == 5 and state["quest_log"][0]["status"] == "completed"


@pytest.mark.parametrize("game", [AGE, SOVEREIGN])
def test_focus_rules_are_delivered_for_each_selected_game(game):
    page = rules_page("rulebook", 0, "campaign-focus", game_id=game)
    assert page["next_offset"] is None
    assert "70/30" in page["content"] and "on-request" in page["content"]
    assert "no compulsory negotiation" in page["content"]
    assert rules_page("hardener", 0, game_id=game)["next_offset"] is None
