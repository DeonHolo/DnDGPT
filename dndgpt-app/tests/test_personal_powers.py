from app.sovereign_play import PROFILE as EMBODIED_PROFILE
import copy

import pytest

from app.chat_game import ChatGame, apply_changes
from app.engine import EngineError, public_state
from app.game_profiles import AGE, SOVEREIGN, rule_source
from app.personal_powers import PROFILE, kit_check, summary
from .test_sovereign import fixture_state, foundation_request
from .test_server import tool


def core_powers():
    return [{"id": "personal-"+str(i), "name": name, "source": "Class", "scope": "personal",
             "rarity": "UNIQUE", "flavor_text": "A test-only sovereign power.",
             "mechanics_display": "A complete, broad test capability with its actual timing and costs.",
             "simple": "A recorded personal power.", "upgrades": []}
            for i, name in enumerate(("Living shell", "Iron sweep", "The open way", "Distant senses"))]


def playing(engine):
    state = fixture_state(engine)
    state["abilities"] = core_powers()
    state["personal_powers"]["earned"] = 0  # Opening refinements were banked/spent in this isolated fixture.
    return state


def upgrade_request(state, entries):
    parents = {row["id"]: copy.deepcopy(row) for row in state["abilities"]}
    for key, upgrade in entries:
        parent = parents[key]
        parent.setdefault("upgrades", []).append({"id": upgrade, "name": "A useful development "+upgrade,
                                                  "rarity": "RARE", "change_display": "Gain a new practical application."})
        parent["mechanics_display"] += " The new practical application "+upgrade+" is integrated."
    return {"upsert": {"abilities": [parents[key] for key in dict(entries)]},
            "spend_personal_upgrades": [{"ability_id": key, "upgrade_id": upgrade} for key, upgrade in entries]}


def test_four_substantial_powers_without_activation_quotas(engine):
    state = ChatGame(engine).create("owner-a", "Four powers", "four-create", True, SOVEREIGN, sovereign_ruleset=EMBODIED_PROFILE)
    assert state["personal_powers"]["profile"] == PROFILE
    assert state["personal_progression"]["upgrades_available"] == 2
    state["abilities"] = core_powers()
    assert kit_check(state)["missing"] == []
    # Four automatic/triggered capabilities need no forced attack/reaction/utility card taxonomy.
    for power in state["abilities"]:
        power["activation"] = "Automatic"
    assert kit_check(state)["missing"] == []
    state["abilities"].pop()
    assert kit_check(state)["missing"]
    state["abilities"] = core_powers()+[{**core_powers()[0], "id": "fifth"}]
    assert kit_check(state)["missing"]
    state["creation"].update(personal_power_count=5, personal_power_reason="This class has a distinct physical embodiment.")
    assert kit_check(state)["missing"] == []
    state["creation"]["personal_power_reason"] = ""
    assert kit_check(state)["missing"]


def test_level_growth_is_automatic_separate_and_multi_level(engine):
    state = playing(engine)
    next_state = apply_changes(state, {"character": {"level": 4}, "level_up_freeze": True})
    assert summary(next_state)["upgrades_available"] == 7  # Two per level plus the level-four major refinement.
    assert next_state["sovereignty"]["ascension_earned"] - state["sovereignty"]["ascension_earned"] == 3
    assert next_state["character"]["skill_points"] == next_state["character"]["talent_points"] == 0
    assert apply_changes(next_state, {"notes": "Still selecting"})["personal_powers"] == next_state["personal_powers"]
    for key in ("skill_points", "talent_points"):
        with pytest.raises(EngineError, match="automatically"):
            apply_changes(next_state, {"character": {key: 1}})


def test_two_refinements_can_change_one_parent_in_one_save(engine):
    state = apply_changes(playing(engine), {"character": {"level": 2}})
    request = upgrade_request(state, [("personal-0", "opening-wing"), ("personal-0", "covering-wing")])
    after = apply_changes(state, request)
    assert len(after["abilities"]) == 4
    assert len(after["abilities"][0]["upgrades"]) == 2
    assert after["abilities"][0]["rarity"] == "UNIQUE"
    assert after["abilities"][0]["upgrades"][0]["rarity"] == "RARE"
    assert summary(after)["upgrades_available"] == 0
    with pytest.raises(EngineError):
        apply_changes(after, request)
    assert state["abilities"] == core_powers()


@pytest.mark.parametrize("defect", ["no_funds", "missing_rules", "remove_history", "rarity", "double_funding", "no_parent", "duplicate"])
def test_invalid_personal_upgrade_is_rejected_without_mutation(engine, defect):
    state = apply_changes(playing(engine), {"character": {"level": 2}})
    if defect == "remove_history":
        state["abilities"][0]["upgrades"] = [{"id": "old", "name": "Owned improvement", "change_display": "An actual old benefit."}]
    request = upgrade_request(state, [("personal-0", "new")])
    if defect == "no_funds": state["personal_powers"]["earned"] = 0
    if defect == "missing_rules": request["upsert"]["abilities"][0]["mechanics_display"] = state["abilities"][0]["mechanics_display"]
    if defect == "remove_history": request["upsert"]["abilities"][0]["upgrades"].pop(0)
    if defect == "rarity": request["upsert"]["abilities"][0]["rarity"] = "RARE"
    if defect == "double_funding":
        state["reward_credits"] = {"earned": 1, "spent": []}
        request["spend_evolution_credit"] = {"ability_id": "personal-0", "evolution_id": "new"}
    if defect == "no_parent": request["spend_personal_upgrades"][0]["ability_id"] = "not-owned"
    if defect == "duplicate": request["spend_personal_upgrades"] *= 2
    original = copy.deepcopy(state)
    with pytest.raises(EngineError):
        apply_changes(state, request)
    assert state == original


def test_extra_standalone_power_requires_explicit_exception_and_removal_is_protected(engine):
    state = playing(engine)
    new = {**core_powers()[0], "id": "requested-extra", "name": "An explicitly requested new power"}
    request = {"upsert": {"abilities": [new]}}
    with pytest.raises(EngineError, match="explicit player request"):
        apply_changes(state, request)
    request["personal_power_exception"] = {"ability_ids": [new["id"]], "reason": "The player requested this additional power."}
    after = apply_changes(state, request)
    assert len(after["abilities"]) == 5 and len(after["personal_powers"]["extra_powers"]) == 1
    with pytest.raises(EngineError, match="Preserve owned"):
        apply_changes(after, {"remove": {"abilities": [new["id"]]}})


def test_legacy_read_does_not_migrate_and_banked_points_carry_once(engine):
    state = playing(engine)
    state.pop("personal_powers")
    state["character"].update(level=8, skill_points=3, talent_points=2)
    # Historical skills with older, unnamed child formats remain readable and writable.
    state["abilities"] += [{**core_powers()[0], "id": "old-signature", "upgrades": [{"name": "Old upgrade"}]}]
    original = copy.deepcopy(state)
    assert public_state(state)["personal_progression"]["upgrades_available"] == 5
    assert state == original
    after = apply_changes(state, {"notes": "Continue the established story"})
    assert after["abilities"] == state["abilities"]
    assert summary(after)["upgrades_available"] == 5 and summary(after)["legacy_kit"]
    again = apply_changes(after, {"notes": "A later save"})
    assert again["personal_powers"] == after["personal_powers"]
    preferences = apply_changes(state, {"campaign_preferences": {"focus": "conquest", "dialogue": "minimal"}})
    assert "personal_powers" not in preferences and preferences["character"] == state["character"]


def test_personal_and_sovereign_upgrades_are_separate(engine):
    state = playing(engine)
    changes = foundation_request(state, "domain")
    state["abilities"] += core_powers()
    original = copy.deepcopy(state["personal_powers"])
    after = apply_changes(state, changes)
    assert after["personal_powers"] == original
    assert len(after["sovereignty"]["ascension_spent"]) == 1


def test_transport_retry_and_failed_write_are_atomic(web):
    created = tool(web, "create_chat_game", {"name": "Personal transport", "game_id": SOVEREIGN,
                                            "action_id": "personal-transport-create", "disposable": True, "sovereign_ruleset": EMBODIED_PROFILE})
    state = created["structuredContent"]["campaign"]
    guidance = created["structuredContent"]["standard_play"]
    assert "FOUR substantial" in guidance["class_kits"]
    seeded = tool(web, "save_chat_update", {"campaign_id": state["id"], "action_id": "personal-seed", "expected_version": 1,
                  "summary": "Prepare four personal powers", "changes": {"upsert": {"abilities": core_powers()}}})
    current = seeded["structuredContent"]["campaign"]
    request = {"campaign_id": state["id"], "action_id": "personal-spend", "expected_version": current["version"],
               "summary": "Select two opening refinements", "changes": upgrade_request(current, [("personal-0", "a"), ("personal-1", "b")])}
    first = tool(web, "save_chat_update", request)
    assert not first.get("isError"), first
    assert tool(web, "save_chat_update", request) == first
    now = first["structuredContent"]["campaign"]
    failed = tool(web, "save_chat_update", {**request, "action_id": "personal-overspend", "expected_version": now["version"],
                 "changes": upgrade_request(now, [("personal-2", "c")])})
    assert failed["isError"]
    saved = tool(web, "get_campaign", {"campaign_id": state["id"]})["structuredContent"]["campaign"]
    assert saved["version"] == now["version"] and saved["personal_powers"] == now["personal_powers"]


def test_age_rules_and_acquisition_are_unchanged(engine):
    state = ChatGame(engine).create("owner-a", "Age fixture", "age-personal-check", True, AGE)
    assert "personal_powers" not in state
    state.update(phase="adventure", paused=False)
    assert len(apply_changes(state, {"upsert": {"abilities": core_powers()}})["abilities"]) == 4
    with pytest.raises(EngineError):
        apply_changes(state, {"spend_personal_upgrades": []})
    assert "TALENT WEB" in rule_source(AGE)["content"]
    assert rule_source(AGE)["source_sha256"] == "94ec7b0882418a00fc6140c09fa725984be02aaa3d70f9cf7664fcb55399a529"


def test_export_restore_preserves_paid_refinements_and_allowance(engine):
    from app.campaign_archive import CampaignArchive
    game = ChatGame(engine)
    state = game.create("owner-a", "Portable powers", "personal-portable-create", True, SOVEREIGN, sovereign_ruleset=EMBODIED_PROFILE)
    state = game.update("owner-a", state["id"], "personal-portable-kit", 1, "Record chosen powers",
                        {"upsert": {"abilities": core_powers()}})["campaign"]
    state = game.update("owner-a", state["id"], "personal-portable-spend", state["version"], "Refine the starting powers",
                        upgrade_request(state, [("personal-0", "portable-a"), ("personal-0", "portable-b")]))["campaign"]
    archive = CampaignArchive(engine)
    restored = archive.restore("owner-a", archive.export("owner-a", state["id"])["archive"], "personal-portable-restore", True)["campaign"]
    assert restored["id"] != state["id"] and restored["paused"]
    assert restored["personal_powers"] == state["personal_powers"]
    assert restored["abilities"] == state["abilities"]
    assert restored["personal_progression"]["upgrades_available"] == 0


def test_personal_selection_keeps_frozen_time_and_custom_rules(engine):
    state = apply_changes(playing(engine), {"character": {"level": 2}, "level_up_freeze": True})
    request = upgrade_request(state, [("personal-0", "frozen-improvement")])
    request["fictional_time_seconds"] = 60
    with pytest.raises(EngineError, match="frozen"):
        apply_changes(state, request)
    request.pop("fictional_time_seconds")
    after = apply_changes(state, request)
    assert after["level_up_freeze"] and after["fictional_time_seconds"] == state["fictional_time_seconds"]
    custom = playing(engine)
    custom["creation"]["rules_source"] = "custom"
    revised = apply_changes(custom, {"character": {"talent_points": 1}, "upsert": {"abilities": [{"id": "custom-power", "name": "Custom acquisition"}]}})
    assert revised["character"]["talent_points"] == 1 and len(revised["abilities"]) == 5
