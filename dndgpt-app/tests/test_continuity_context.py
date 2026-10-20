import copy
import json

import pytest

from app.chat_game import ChatGame
from app.continuity import model_view
from app.engine import Engine
from app.storage import Store
from scripts.audit_continuity_context import FACTS, OWNER, audit, build_campaign, save
from .test_server import tool


@pytest.mark.parametrize("saves", [10, 100, 300])
def test_long_save_chain_retains_old_facts_after_reopen(engine, saves):
    original, state = build_campaign(engine, saves)
    reopened = Engine(Store(engine.store.path))
    reopened.store.initialize()
    restored = reopened.get_campaign(OWNER, state["id"])
    report = audit(restored)
    assert restored == state
    assert report["visible_facts"] == {"full": 8, "turn": 5, "resume": 2}
    assert ChatGame(reopened).version(OWNER, state["id"], original["version"])["campaign"] == original
    assert reopened.audit(OWNER, state["id"])["integrity_valid"]


def test_views_do_not_change_history_clock_or_pause_and_full_read_recovers_omissions(engine):
    _, state = build_campaign(engine, 10)
    before = copy.deepcopy(state)
    events = engine.audit(OWNER, state["id"])["event_count"]
    for view in ("turn", "resume", "full"):
        model_view(state, view)
    assert state == before == engine.get_campaign(OWNER, state["id"])
    assert engine.audit(OWNER, state["id"])["event_count"] == events
    turn = model_view(state, "turn")
    assert turn["omitted"]["world_log"] == len(state["world_log"]) - 3
    assert "world" in turn["omitted"]
    assert FACTS["old_promise"][1] not in json.dumps(turn)
    assert FACTS["old_promise"][1] in json.dumps(engine.get_campaign(OWNER, state["id"]))


def test_partial_saves_retain_commitments_and_only_explicitly_change_requested_fields(engine):
    _, state = build_campaign(engine, 10)
    changed = save(ChatGame(engine), state, {"continuity": {"outcome": "The bell was inspected."}})
    assert changed["continuity"]["npc_commitments"] == state["continuity"]["npc_commitments"]
    for key in ("abilities", "inventory", "conditions", "quest_log", "world_log", "world"):
        assert changed[key] == state[key]


def test_compact_world_summary_cannot_erase_omitted_world_details(engine):
    _, state = build_campaign(engine, 10)
    compact = model_view(state, "turn")
    compact["world"]["summary"] = "Evening at the quay."
    changed = save(ChatGame(engine), state, {"world": compact["world"]})
    assert changed["world"]["routes"] == state["world"]["routes"]
    assert changed["world"]["gate"] == state["world"]["gate"]
    assert changed["world"]["summary"] == "Evening at the quay."


def test_nested_world_edits_keep_other_facts_and_approved_correction_can_remove_them(engine):
    _, state = build_campaign(engine, 10)
    state = save(ChatGame(engine), state, {"world": {"gate": {"guard": "Nessa"}}})
    assert state["world"]["gate"]["password"] == FACTS["corrected_fact"][1]
    assert state["world"]["gate"]["guard"] == "Nessa"
    state = save(ChatGame(engine), state, {"world": {"gate": {"password": "Newly changed password"}}})
    assert state["world"]["gate"] == {"password": "Newly changed password", "guard": "Nessa"}
    proposal = engine.propose_action(OWNER, state["id"], "remove-world-after-review", state["version"],
        "correct_chat_state", {"changes": {"world": {"summary": "Player-approved replacement"}},
                               "reason": "Synthetic explicit correction"})
    assert engine.get_campaign(OWNER, state["id"]) == state
    changed = engine.execute_confirmed_action(OWNER, proposal["proposal"]["id"],
        proposal["_meta"]["approval_token"])["campaign"]
    assert changed["world"] == {"summary": "Player-approved replacement"}
    assert changed["paused"] and changed["fictional_time_seconds"] == state["fictional_time_seconds"]


def test_mcp_full_snapshot_is_not_accidentally_counted_as_model_visible_context(web):
    created = tool(web, "create_chat_game", {"name": "Disposable visibility fixture",
                   "action_id": "create-visibility-fixture", "disposable": True})
    state = created["structuredContent"]["campaign"]
    saved = tool(web, "save_chat_update", {"campaign_id": state["id"], "action_id": "seed-visibility-fixture",
        "expected_version": state["version"], "summary": "Synthetic old promise",
        "changes": {"world": {"summary": "A tidal town", "routes": {"causeway": FACTS["world_rule"][1]}},
                    "upsert": {"world_log": [{"id": str(i), "text": FACTS["old_promise"][1] if i == 0 else "Later event"}
                                              for i in range(10)]}}, "result_view": "turn"})
    assert not saved.get("isError"), saved
    result = tool(web, "get_campaign", {"campaign_id": state["id"], "view": "turn"})
    assert FACTS["old_promise"][1] not in json.dumps(result["structuredContent"])
    assert FACTS["old_promise"][1] in json.dumps(result["_meta"]["campaign_snapshot"])
    compact = result["structuredContent"]["campaign"]
    saved = tool(web, "save_chat_update", {"campaign_id": state["id"], "action_id": "edit-compact-world",
        "expected_version": compact["version"], "summary": "Change the short world summary",
        "changes": {"world": {**compact["world"], "summary": "Evening at the quay"}}, "result_view": "turn"})
    assert not saved.get("isError"), saved
    full = tool(web, "get_campaign", {"campaign_id": state["id"], "view": "full"})
    assert FACTS["old_promise"][1] in json.dumps(full["structuredContent"])
    assert full["structuredContent"]["campaign"]["world"]["routes"]["causeway"] == FACTS["world_rule"][1]


def test_full_is_still_default_and_unrecorded_facts_are_not_invented(web):
    created = tool(web, "create_chat_game", {"name": "Disposable unknown-fact fixture",
                   "action_id": "create-unknown-fixture", "disposable": True})
    state = created["structuredContent"]["campaign"]
    result = tool(web, "get_campaign", {"campaign_id": state["id"]})
    assert result["structuredContent"]["campaign"] == state
    assert state["resume_brief"]["missing_continuity"]
    assert not state["resume_brief"]["npc_commitments"]
