from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json

import pytest

from app.engine import Engine, EngineError
from app.rules import Dice
from app.storage import Store
from .conftest import commit


def test_initially_paused_and_inspection_does_not_roll(engine, state):
    engine.dice = Dice(lambda _: pytest.fail("Inspection or blocked action consumed RNG"))
    before = copy.deepcopy(state)
    assert engine.get_campaign("owner-a", state["id"]) == before
    for kind, payload in [("roll_check", {"dc": 11, "modifier": 2}),
                          ("roll_dice", {"sides": 20, "count": 1}),
                          ("roll_rarity", {"candidate_id": "candidate-001"}),
                          ("spend_mp", {"cost": 3}),
                          ("award_xp", {"amount": 5, "reward_id": "reward-0001"}),
                          ("record_scene", {"scene_id": "scene-00001"})]:
        with pytest.raises(EngineError) as error:
            engine.propose_action("owner-a", state["id"], "blocked-action-01", 1, kind, payload)
        assert error.value.status == 423
    assert engine.get_campaign("owner-a", state["id"]) == before
    assert engine.audit("owner-a", state["id"])["event_count"] == 1


def test_proposal_no_rng_approval_required_and_retry_once(engine, state):
    state = commit(engine, state, "resume")["campaign"]
    rolls = []
    engine.dice = Dice(lambda sides: rolls.append(sides) or 10)
    args = ("owner-a", state["id"], "roll-action-001", state["version"],
            "roll_check", {"dc": 11, "modifier": 3})
    proposal = engine.propose_action(*args)
    assert engine.propose_action(*args) == proposal
    assert rolls == []
    assert engine.get_campaign("owner-a", state["id"]) == state
    with pytest.raises(EngineError) as error:
        engine.execute_confirmed_action("owner-a", proposal["proposal"]["id"], "forged")
    assert error.value.status == 403
    approved = engine.execute_confirmed_action("owner-a", proposal["proposal"]["id"], proposal["_meta"]["approval_token"])
    assert approved["event"]["total"] == 14
    assert engine.execute_confirmed_action("owner-a", proposal["proposal"]["id"], proposal["_meta"]["approval_token"]) == approved
    assert rolls == [20]
    assert engine.audit("owner-a", state["id"])["integrity_valid"]


def test_changed_payload_and_stale_approval_rejected(engine, state):
    proposal = engine.propose_action("owner-a", state["id"], "resume-action-01", 1, "resume", {})
    with pytest.raises(EngineError) as error:
        engine.propose_action("owner-a", state["id"], "resume-action-01", 1, "pause", {})
    assert error.value.code == "idempotency_conflict"
    commit(engine, state, "pause", action_id="other-action-001")
    with pytest.raises(EngineError) as error:
        engine.execute_confirmed_action("owner-a", proposal["proposal"]["id"], proposal["_meta"]["approval_token"])
    assert error.value.code == "version_conflict"


def test_concurrent_confirmations_spend_exactly_once(engine, state):
    state = commit(engine, state, "resume")["campaign"]
    p = engine.propose_action("owner-a", state["id"], "spend-action-001", state["version"], "spend_mp", {"cost": 7})
    def execute(_):
        return engine.execute_confirmed_action("owner-a", p["proposal"]["id"], p["_meta"]["approval_token"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(execute, range(8)))
    assert all(result == results[0] for result in results)
    assert results[0]["campaign"]["character"]["mp"] == 48
    assert engine.audit("owner-a", state["id"])["event_count"] == 3


def test_ownership_and_cross_account_approval(engine, state):
    proposal = engine.propose_action("owner-a", state["id"], "resume-action-01", 1, "resume", {})
    for operation in [lambda: engine.get_campaign("owner-b", state["id"]),
                      lambda: engine.audit("owner-b", state["id"]),
                      lambda: engine.propose_action("owner-b", state["id"], "resume-action-01", 1, "resume", {}),
                      lambda: engine.execute_confirmed_action("owner-b", proposal["proposal"]["id"], proposal["_meta"]["approval_token"])]:
        with pytest.raises(EngineError) as error:
            operation()
        assert error.value.status == 404
    assert engine.list_campaigns("owner-b") == []


def test_database_reopen_preserves_state_and_pending_approval(engine, state):
    proposal = engine.propose_action("owner-a", state["id"], "resume-action-01", 1, "resume", {})
    reopened = Engine(Store(engine.store.path))
    reopened.store.initialize()
    assert reopened.get_campaign("owner-a", state["id"]) == state
    assert reopened.pending_approval("owner-a", state["id"])["approval"]["proposal"] == proposal["proposal"]
    assert reopened.execute_confirmed_action("owner-a", proposal["proposal"]["id"], proposal["_meta"]["approval_token"])["campaign"]["version"] == 2


def test_six_scene_ceiling_vital_surge_and_freeze(engine, state):
    state = commit(engine, state, "resume")["campaign"]
    state = commit(engine, state, "spend_mp", {"cost": 20})["campaign"]
    for n in range(6):
        result = commit(engine, state, "record_scene", {"scene_id": f"scene-{n:05d}"})
        state = result["campaign"]
    ch = state["character"]
    assert (ch["level"], ch["xp"], ch["xp_total"], ch["xp_next"]) == (2, 0, 100, 140)
    assert result["event"]["cinematic_milestone_xp"] == 100
    assert ch["mp"] == ch["mp_max"]
    assert ch["sta"] == 60
    assert state["paused"] and state["level_up_freeze"]
    with pytest.raises(EngineError):
        commit(engine, state, "resume")
    raised = commit(engine, state, "spend_attribute", {"attribute": "INT"})["campaign"]
    assert raised["character"]["attributes"]["INT"] == 7
    assert raised["character"]["mp_max"] == 65 and raised["character"]["mp"] == 55
    assert raised["fictional_time_seconds"] == 0 and raised["level_up_freeze"]


def test_large_xp_carries_and_awards_each_level_once(engine, state):
    state = commit(engine, state, "resume")["campaign"]
    state = commit(engine, state, "award_xp", {"amount": 500, "reward_id": "reward-large-01"})["campaign"]
    ch = state["character"]
    assert (ch["level"], ch["xp"], ch["xp_total"], ch["xp_next"]) == (4, 80, 500, 220)
    assert ch["skill_points"] == ch["talent_points"] == ch["attribute_points"] == 3
    assert state["advancement"]["pending_levels"] == [2, 3, 4]


@pytest.mark.parametrize("kind,payload", [("spend_mp", {"cost": -1}), ("spend_mp", {"cost": True}),
    ("roll_check", {"dc": 11.5, "modifier": 0}), ("roll_dice", {"sides": 20, "count": 1000000}),
    ("roll_check", {"dc": 11, "modifier": 0, "script": "anything"}), ("patch_state", {})])
def test_invalid_input_is_atomic(engine, state, kind, payload):
    state = commit(engine, state, "resume")["campaign"]
    with pytest.raises(EngineError):
        commit(engine, state, kind, payload)
    assert engine.get_campaign("owner-a", state["id"]) == state


def test_rarity_hidden_on_hud_and_fixed_after_reveal(engine, state):
    state = commit(engine, state, "resume")["campaign"]
    engine.dice = Dice(lambda _: 9970)
    state = commit(engine, state, "roll_rarity", {"candidate_id": "candidate-001"})["campaign"]
    assert "natural" not in json.dumps(state)
    audit = engine.audit("owner-a", state["id"], show_rolls=True)
    assert audit["events"][-1]["roll"]["natural"] == 9971
    assert not engine.audit("owner-a", state["id"])["raw_rolls_included"]
    with pytest.raises(EngineError) as error:
        commit(engine, state, "roll_rarity", {"candidate_id": "candidate-001"})
    assert error.value.code == "candidate_fixed"


def test_event_tampering_detected(engine, state):
    with engine.store.transaction() as db:
        db.execute("UPDATE events_v1 SET event=? WHERE campaign_id=?", ('{}', state["id"]))
    assert engine.audit("owner-a", state["id"])["integrity_valid"] is False


def test_ui_preferences_persist_without_game_changes(engine, state):
    prefs = {"panels": ["skills"], "details": ["ability-fixture"], "hud_hidden": True}
    engine.set_view_preferences("owner-a", prefs)
    assert Engine(Store(engine.store.path)).get_view_preferences("owner-a") == prefs
    assert engine.get_campaign("owner-a", state["id"]) == state
    assert engine.audit("owner-a", state["id"])["event_count"] == 1


@pytest.mark.parametrize("tab", ["world", "log"])
def test_world_subtab_preferences_are_owned_and_do_not_change_campaign(engine, state, tab):
    prefs = {"panels": ["world"], "details": [], "hud_hidden": False, "world_tab": tab}
    engine.set_view_preferences("owner-a", prefs)
    assert Engine(Store(engine.store.path)).get_view_preferences("owner-a") == prefs
    assert engine.get_view_preferences("owner-b") != prefs
    assert engine.get_campaign("owner-a", state["id"]) == state
    assert engine.audit("owner-a", state["id"])["event_count"] == 1


@pytest.mark.parametrize("tab", ["all", None, False, [], {}])
def test_invalid_world_subtab_preserves_saved_preferences(engine, tab):
    prefs = {"panels": ["world"], "details": [], "hud_hidden": False, "world_tab": "log"}
    engine.set_view_preferences("owner-a", prefs)
    with pytest.raises(EngineError, match="world_tab"):
        engine.set_view_preferences("owner-a", {**prefs, "world_tab": tab})
    assert engine.get_view_preferences("owner-a") == prefs


@pytest.mark.parametrize("tab", ["summons", "combat"])
def test_combat_subtab_preferences_are_owned_and_do_not_change_campaign(engine, state, tab):
    prefs = {"panels": ["summons"], "details": [], "hud_hidden": False, "combat_tab": tab, "world_tab": "log"}
    engine.set_view_preferences("owner-a", prefs)
    assert Engine(Store(engine.store.path)).get_view_preferences("owner-a") == prefs
    assert engine.get_view_preferences("owner-b") != prefs
    assert engine.get_campaign("owner-a", state["id"]) == state
    assert engine.audit("owner-a", state["id"])["event_count"] == 1


@pytest.mark.parametrize("tab", ["all", None, False, [], {}])
def test_invalid_combat_subtab_preserves_saved_preferences(engine, tab):
    prefs = {"panels": ["summons"], "details": [], "hud_hidden": False, "combat_tab": "combat"}
    engine.set_view_preferences("owner-a", prefs)
    with pytest.raises(EngineError, match="combat_tab"):
        engine.set_view_preferences("owner-a", {**prefs, "combat_tab": tab})
    assert engine.get_view_preferences("owner-a") == prefs


@pytest.mark.parametrize("tab", ["combat", "reactions", "passives", "utility"])
def test_skill_subtab_preferences_are_owned_and_do_not_change_campaign(engine, state, tab):
    prefs = {"panels": ["skills"], "details": ["ability-fixture"], "hud_hidden": False,
             "equipment_tab": "inventory", "skills_tab": tab}
    engine.set_view_preferences("owner-a", prefs)
    assert Engine(Store(engine.store.path)).get_view_preferences("owner-a") == prefs
    assert engine.get_view_preferences("owner-b") != prefs
    assert engine.get_campaign("owner-a", state["id"]) == state
    assert engine.audit("owner-a", state["id"])["event_count"] == 1


@pytest.mark.parametrize("tab", ["all", None, False, [], {}])
def test_invalid_skill_subtab_preserves_saved_preferences(engine, tab):
    prefs = {"panels": ["skills"], "details": [], "hud_hidden": False, "skills_tab": "utility"}
    engine.set_view_preferences("owner-a", prefs)
    with pytest.raises(EngineError, match="skills_tab"):
        engine.set_view_preferences("owner-a", {**prefs, "skills_tab": tab})
    assert engine.get_view_preferences("owner-a") == prefs


def test_inventory_subtab_preferences_are_owned_and_do_not_change_campaign(engine, state):
    prefs = {"panels": ["equipment"], "details": ["item-inventory-fixture"],
             "hud_hidden": False, "equipment_tab": "inventory"}
    engine.set_view_preferences("owner-a", prefs)
    assert Engine(Store(engine.store.path)).get_view_preferences("owner-a") == prefs
    assert engine.get_view_preferences("owner-b") != prefs
    assert engine.get_campaign("owner-a", state["id"]) == state
    assert engine.audit("owner-a", state["id"])["event_count"] == 1


@pytest.mark.parametrize("tab", ["bag", None, False, [], {}])
def test_invalid_inventory_subtab_does_not_replace_saved_preferences(engine, tab):
    prefs = {"panels": ["equipment"], "details": [], "hud_hidden": False,
             "equipment_tab": "equipment"}
    engine.set_view_preferences("owner-a", prefs)
    with pytest.raises(EngineError) as error:
        engine.set_view_preferences("owner-a", {**prefs, "equipment_tab": tab})
    assert error.value.code == "invalid_preferences"
    assert engine.get_view_preferences("owner-a") == prefs
