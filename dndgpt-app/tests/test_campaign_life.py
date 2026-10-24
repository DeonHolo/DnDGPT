import copy
import json
import time
from pathlib import Path

import pytest

from app import records
from app.campaign_archive import CampaignArchive, digest, validate_archive
from app.campaign_life import public_life, validate_snapshot
from app.chat_game import ChatGame, apply_changes
from app.engine import EngineError
from app.game_profiles import AGE, SOVEREIGN
from app.storage import canonical
from .test_server import tool
from .test_sovereign import fixture_state


def seed(engine, selected=AGE, owner="owner-a"):
    state = fixture_state(engine) if selected == SOVEREIGN else ChatGame(engine).create(owner, "Living test", "living-create", True)
    state.update(phase="adventure", paused=False)
    for key in ("rules_check", "resume_brief"):
        state.pop(key, None)
    with engine.store.transaction() as db:
        records.update(db, "campaigns_v1", {"id": state["id"]}, {"data": canonical(state)})
    return state


def save(engine, state, changes, action=None):
    return ChatGame(engine).update("owner-a", state["id"], action or "living-"+str(state["version"]),
                                   state["version"], "Disposable living-campaign test", changes)["campaign"]


def opening():
    return {"upsert": {"world_log": [{"id": "encounter", "text": "The captain saw the summoned moth guard its caller.", "witnesses": ["captain"]}]},
            "life_updates": {"actors": [{"id": "captain", "name": "The river captain", "kind": "rival", "description": "A surviving river raider.",
                                          "traits": ["cautious"], "goal": "Control the crossing", "preferred_approach": "Scout before attacking"}],
                             "places": [{"id": "quay", "name": "The quay", "kind": "location", "description": "A closed ferry landing."}],
                             "events": [{"id": "learned-moth", "kind": "observation", "subject_id": "captain", "source_id": "encounter",
                                         "memory_id": "moth", "summary": "The moth protects its caller.", "tactic": "disrupt_support", "known_to_player": True}]}}


@pytest.mark.parametrize("selected", [AGE, SOVEREIGN])
def test_learning_is_persistent_evidence_backed_and_deduplicated(engine, selected):
    state = save(engine, seed(engine, selected), opening())
    actor = state["campaign_life"]["actors"][0]
    assert actor["observations"][0]["observations"] == 1
    assert "event_ledger" not in state["campaign_life"]
    repeated = {"life_updates": {"events": opening()["life_updates"]["events"]}}
    state = save(engine, state, repeated)
    assert state["campaign_life"]["actors"][0]["observations"][0]["observations"] == 1
    changed = copy.deepcopy(repeated)
    changed["life_updates"]["events"][0]["summary"] = "Invented weakness"
    with pytest.raises(EngineError, match="different outcome"):
        save(engine, state, changed)
    assert engine.get_campaign("owner-a", state["id"])["version"] == state["version"]


@pytest.mark.parametrize("mutation", [
    lambda p: p["upsert"]["world_log"][0].pop("witnesses"),
    lambda p: p["upsert"]["world_log"][0].update(witnesses=None),
    lambda p: p.pop("upsert"),
    lambda p: p["life_updates"]["events"][0].update(tactic="omniscient_counter"),
    lambda p: p["life_updates"]["actors"][0].update(observations=[]),
    lambda p: p["life_updates"]["places"][0].update(links=["undiscovered"]),
    lambda p: p["life_updates"]["events"][0].update(known_to_player="false"),
])
def test_missing_witnesses_sources_and_unsupported_registry_edits_are_atomic(engine, mutation):
    state = seed(engine)
    patch = opening(); mutation(patch)
    with pytest.raises(EngineError):
        save(engine, state, patch)
    assert "campaign_life" not in engine.get_campaign("owner-a", state["id"])


def test_relationships_promises_and_private_knowledge(engine):
    state = save(engine, seed(engine), opening())
    common = {"subject_id": "captain", "source_id": "encounter"}
    events = [{**common, "id": "truce", "kind": "relationship", "stance": "wary", "summary": "Accepted a truce after the rescue."},
              {**common, "id": "promise", "kind": "commitment", "commitment_id": "passage", "status": "open", "summary": "Provide passage after the bell is returned."},
              {**common, "id": "secret", "kind": "observation", "memory_id": "hidden", "summary": "A private tactical observation.", "known_to_player": False}]
    state = save(engine, state, {"life_updates": {"events": events}})
    assert state["campaign_life"]["actors"][0]["relationship"]["stance"] == "wary"
    assert "private tactical" not in json.dumps(public_life(state["campaign_life"]))
    assert "private tactical" in json.dumps(state["campaign_life"])
    resolved = {**events[1], "id": "promise-kept", "status": "fulfilled"}
    state = save(engine, state, {"life_updates": {"events": [resolved]}})
    with pytest.raises(EngineError, match="stays resolved"):
        save(engine, state, {"life_updates": {"events": [{**resolved, "id": "reopen", "status": "open"}]}})


def quest():
    return {"id": "bell", "name": "Return the bell", "quest_schema": 1, "status": "active",
            "finish_condition": "Return the bell intact", "objectives": [{"id": "return", "text": "Return the bell", "status": "pending"}],
            "system_reward": {"source": "System", "xp": 10, "currency": {"silver": 5}}}


def test_completion_changes_a_place_and_settles_once(engine):
    patch = opening(); patch["upsert"]["quest_log"] = [quest()]
    state = save(engine, seed(engine), patch)
    event = {"id": "aftermath", "kind": "quest_aftermath", "subject_id": "quay", "quest_id": "bell", "source_id": "bell", "summary": "The ferry landing reopens."}
    with pytest.raises(EngineError, match="source"):
        save(engine, state, {"life_updates": {"events": [event]}})
    q = copy.deepcopy(state["quest_log"][0]); q["objectives"][0]["status"] = "done"
    change = {"id": "open-quay", "kind": "place_change", "subject_id": "quay", "source_id": "bell", "summary": "The ferry landing reopens.",
              "feature": {"id": "ferry", "name": "Working ferry", "description": "Passage to the far bank is available."}}
    state = save(engine, state, {"upsert": {"quest_log": [q]}, "life_updates": {"events": [change, event]}})
    assert state["funds"]["silver"] == 5 and state["character"]["xp"] == 10
    assert state["quest_log"][0]["status"] == "completed"
    assert state["campaign_life"]["places"][0]["features"][0]["id"] == "ferry"
    state = save(engine, state, {"life_updates": {"events": [change, event]}})
    assert state["funds"]["silver"] == 5 and len(state["campaign_life"]["aftermath"]) == 1


def test_development_needs_an_actual_owned_capability_change(engine):
    state = save(engine, seed(engine), opening())
    ability = {"id": "moth", "name": "Moth guard", "mechanics": "Guard one ally."}
    state = save(engine, state, {"upsert": {"abilities": [ability]}})
    event = {"id": "growth", "kind": "development", "subject_id": "moth", "source_id": "encounter", "summary": "The moth can carry a ward to a second ally."}
    with pytest.raises(EngineError, match="not only"):
        save(engine, state, {"life_updates": {"events": [event]}})
    improved = {**ability, "upgrades": [{"id": "second", "name": "Second ward", "mechanics": "Guard a second ally."}]}
    state = save(engine, state, {"upsert": {"abilities": [improved]}, "life_updates": {"events": [event]}})
    assert state["campaign_life"]["developments"][0]["subject_id"] == "moth"


def test_cited_evidence_requires_a_reviewed_correction(engine):
    state = save(engine, seed(engine), opening())
    change = {"upsert": {"world_log": [{"id": "encounter", "text": "A different past event", "witnesses": ["captain"]}]}}
    with pytest.raises(EngineError, match="reviewed correction"):
        save(engine, state, change)
    with engine.store.transaction() as db:
        raw = engine._get(db, "owner-a", state["id"])
    corrected = apply_changes(raw, change, correction=True)
    assert apply_changes(corrected, {"notes": "Continued after reviewed correction"})["world_log"][0]["text"] == "A different past event"


def test_private_observations_default_to_hidden_and_sources_can_be_revealed(engine):
    patch = opening(); patch["upsert"]["world_log"][0]["known_to_player"] = False
    patch["life_updates"]["events"][0].pop("known_to_player")
    state = save(engine, seed(engine), patch)
    assert public_life(state["campaign_life"])["actors"][0]["observations"] == []
    assert public_life(state["campaign_life"])["recent_events"] == []
    source = {**state["world_log"][0], "known_to_player": True}
    state = save(engine, state, {"upsert": {"world_log": [source]}})
    assert state["world_log"][0]["known_to_player"] is True


def test_collecting_a_contract_after_aftermath_keeps_system_rewards_once_only(engine):
    patch = opening(); q = quest(); q["objectives"][0]["status"] = "done"
    q["contract_payment"] = {"creditor": "Mara", "condition": "Return to the quay", "status": "owed", "reward": {"currency": {"silver": 10}}}
    patch["upsert"]["quest_log"] = [q]
    patch["life_updates"]["events"].append({"id": "aftermath", "kind": "quest_aftermath", "subject_id": "quay", "quest_id": "bell", "source_id": "bell", "summary": "The ferry reopens."})
    state = save(engine, seed(engine), patch)
    q = copy.deepcopy(state["quest_log"][0]); q["contract_payment"]["status"] = "collected"
    state = save(engine, state, {"upsert": {"quest_log": [q]}})
    assert state["funds"]["silver"] == 15 and state["character"]["xp"] == 10


def test_journey_stops_at_new_decisions_or_its_horizon(engine):
    state = seed(engine)
    state = save(engine, state, {"life_updates": {"pacing": {"mode": "journey", "objective": "Reach the quay", "authorized_until": 600}}})
    with pytest.raises(EngineError, match="horizon"):
        save(engine, state, {"fictional_time_seconds": 601})
    state = save(engine, state, {"fictional_time_seconds": 300, "continuity": {"pending_decision": "A washed-out bridge blocks the route. Choose an approach."}})
    assert state["campaign_life"]["pacing"]["mode"] == "scene"
    assert state["fictional_time_seconds"] == 300


@pytest.mark.parametrize("pacing", [{"mode": "journey"}, {"mode": "journey", "objective": "Travel", "authorized_until": True},
                                    {"mode": "expedition", "objective": "Scout", "authorized_until": 8*86400},
                                    {"mode": "automatic_success"}])
def test_pacing_rejects_unbounded_or_fake_authorization(engine, pacing):
    with pytest.raises(EngineError):
        save(engine, seed(engine), {"life_updates": {"pacing": pacing}})


@pytest.mark.parametrize("selected", [AGE, SOVEREIGN])
def test_export_restore_preserves_memory_and_retry_receipts(engine, selected):
    state = save(engine, seed(engine, selected), opening())
    archive = CampaignArchive(engine).export("owner-a", state["id"])["archive"]
    source = archive["campaign"]["campaign_life"]
    validate_snapshot(source)
    restored = CampaignArchive(engine).restore("owner-a", archive, "restore-living", True)["campaign"]
    assert restored["campaign_life"] == state["campaign_life"]
    assert restored["paused"] and restored["game_id"] == selected
    broken = copy.deepcopy(archive); broken["campaign"]["campaign_life"]["actors"][0]["observations"] = "corrupt"
    broken["sha256"] = digest(broken["campaign"])
    with pytest.raises(EngineError):
        validate_archive(broken)


@pytest.mark.parametrize("selected", [AGE, SOVEREIGN])
def test_sixty_turn_authenticated_save_chain_keeps_early_promises_and_closed_quests(web, selected, tmp_path):
    created = tool(web, "create_chat_game", {"name": "Disposable sustained test", "action_id": "sustained-create", "disposable": True, "game_id": selected})["structuredContent"]
    state = created.get("campaign", created)
    engine = web.app.state.engine
    # Disposable fixture setup only: this is transport/storage evidence, never a model-play claim.
    with engine.store.transaction() as db:
        row = records.find(db, "campaigns_v1", {"id": state["id"]}, limit=1)[0]
        state.update(phase="adventure", paused=False)
        for key in ("rules_check", "resume_brief"):
            state.pop(key, None)
        records.update(db, "campaigns_v1", {"id": state["id"]}, {"data": canonical(state)})
    durations = []
    for turn in range(60):
        start = time.perf_counter()
        read = tool(web, "get_campaign", {"campaign_id": state["id"], "view": "full"})["structuredContent"]["campaign"]
        changes = opening() if turn == 0 else {"upsert": {"world_log": [{"id": "turn-"+str(turn), "text": "A new recorded turn.", "witnesses": ["captain"]}]}}
        if turn == 1:
            changes["life_updates"] = {"events": [{"id": "promise", "kind": "commitment", "subject_id": "captain", "source_id": "turn-1", "commitment_id": "passage", "status": "open", "summary": "Provide passage after the bell is returned."}]}
        result = tool(web, "save_chat_update", {"campaign_id": read["id"], "expected_version": read["version"], "action_id": "sustained-"+str(turn), "summary": "Scripted fixture turn", "changes": changes})
        assert not result.get("isError"), result
        state = result["structuredContent"]["campaign"]
        durations.append((time.perf_counter()-start)*1000)
        if turn > 1:
            actor = state["campaign_life"]["actors"][0]
            assert actor["observations"][0]["summary"] == "The moth protects its caller."
            assert actor["commitments"][0]["text"] == "Provide passage after the bell is returned."
    report = {"game_id": selected, "turns": 60, "model_calls": 0, "tool_calls_per_turn": 2,
              "player_campaigns_accessed": 0, "scope": "Authenticated local read/save transport; no AI narration, host scheduling or phone timing", "turn_ms": durations}
    (tmp_path / (selected+"-turn-timings.json")).write_text(json.dumps(report), encoding="utf-8")
    output = Path(__file__).resolve().parents[1] / "test-results" / (selected+"-living-turns.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")

@pytest.mark.parametrize("selected", [AGE, SOVEREIGN])
def test_turn_view_retains_actual_equipment_and_upgraded_mechanics(engine, selected):
    from app.continuity import model_view
    state = seed(engine, selected)
    state["equipment"] = {"Ring 1": "signet"}
    state["inventory"] = [
        {"id": "signet", "effects": "After a successful summon command, gain the recorded ward.",
         "charges": {"current": 1, "maximum": 3}},
        {"id": "stored-wand", "location": "STORED", "effects": "Requires equipping; 0 charges.",
         "charges": {"current": 0, "maximum": 2}}]
    state["abilities"] = [{"id": "command", "activation": "Free action", "mp_cost": 5,
        "cooldown_remaining": 0, "mechanics": "The exact current combined command rules.",
        "upgrades": [{"id": "command-growth", "change_display": "The command reaches a second ally."}]}]
    original = copy.deepcopy(state)
    view = model_view(state, "turn")
    for field in ("equipment", "inventory", "abilities", "character"):
        assert view[field] == state[field]
    assert state == original
