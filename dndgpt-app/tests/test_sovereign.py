import copy
import hashlib
from pathlib import Path

import pytest

from app.chat_game import ChatGame, apply_changes
from app.engine import EngineError
from app.game_profiles import AGE, SOVEREIGN, compose, rule_source
from app.mcp_server import rules_page
from app.rules import Dice
from app.sovereignty import initial, validate
from .test_server import tool


def fixture_state(engine):
    s = ChatGame(engine).create("owner-a", "Sovereign fixture", "sovereign-create", True, SOVEREIGN)
    s.update(phase="adventure", paused=False)
    s["sovereignty"]["domain"].update(name="The wandering fortress", description="A functioning mobile fortress.",
                                    limits={"max_formations": 5, "max_strength": 1000},
                                    capabilities=[{"id": "workshop", "name": "Workshop", "description": "Refit constructs."}])
    s["sovereignty"]["commanders"] = [{"id": "general", "name": "The first commander", "level": 1,
                                      "xp": 0, "xp_total": 0, "status": "active", "abilities": []}]
    s["sovereignty"]["fronts"] = [{"id": "crossing", "name": "Hold the crossing", "objective": "Control the crossing",
                                  "target_progress": 2, "player_progress": 0, "enemy_progress": 0,
                                  "terrain_defense": 0, "status": "active"}]
    s["sovereignty"]["formations"] = [
        {"id": "guard", "name": "Fortress guard", "side": "player", "strength": 100, "maximum_strength": 100,
         "attack": 4, "defense": 12, "power": 4, "armor": 4, "morale": 100, "commander_id": "general",
         "front_id": "crossing", "xp_total": 0, "veterancy": 0, "status": "active"},
        {"id": "raiders", "name": "Raiding force", "side": "enemy", "strength": 100, "maximum_strength": 100,
         "attack": 4, "defense": 12, "power": 4, "armor": 4, "morale": 100,
         "front_id": "crossing", "xp_total": 0, "veterancy": 0, "status": "active"}]
    return s


def milestone():
    return {"id": "fortress-two", "title": "Restore the fortress", "target_level": 2,
            "objectives": [{"id": "power", "text": "Restore the core", "status": "pending"},
                           {"id": "road", "text": "Secure the crossing", "status": "pending"}],
            "choices": [{"id": key, "name": key.title(), "description": "Unlock " + key,
                         "capabilities": [{"id": key, "name": key.title(), "description": "Recorded development"}]}
                        for key in ("mobility", "production", "defense")]}


def test_rules_are_composed_without_rewriting_shared_source():
    base = rule_source(AGE)
    s = rule_source(SOVEREIGN)
    creation = rules_page("rulebook", 0, "sovereign-creation", SOVEREIGN)["content"]
    assert "Starting Sovereign Evolution on the Signature/Title turn" in creation
    assert "choose ONE free in addition to the Signature and Title selections" in creation
    assert "Level 2 upgrade available" in creation
    text = s["content"]
    from app.game_profiles import RULES
    module = (RULES / "sovereign/system.txt").read_text(encoding="utf-8") + "\n\n"
    assert text.count(module) == 1
    restored = text.replace(module, "", 1)
    for op in reversed(s["replacements"]):
        for edit in reversed(op["edits"]):
            start = edit["new_start"]
            assert restored[start:start + len(edit["new"])] == edit["new"]
            restored = restored[:start] + edit["old"] + restored[start + len(edit["new"]):]
    assert restored == base["content"]
    assert s["base_sha256"] == base["source_sha256"]
    assert hashlib.sha256(restored.encode()).hexdigest() == base["source_sha256"]
    assert "every EPIC, LEGENDARY or UNIQUE" in text
    assert "Sovereign ownership and progression" not in base["content"]
    with pytest.raises(ValueError, match="anchor changed"):
        compose("Changed source", [{"id": "test", "old": "Missing", "new": "New"}])


def test_starting_sovereign_kit_is_real_and_distinct_from_personal_powers(engine):
    from app.sovereignty import complete_sovereign, sovereign_kit_check
    state = fixture_state(engine)
    state["character"]["rarity"] = "UNIQUE"
    state["abilities"] = [{"id": role, "name": "Recorded "+role+" power", "scope": "sovereign", "sovereign_role": role,
                           "rarity": "UNIQUE", "activation": "Passive",
                           "mechanics": "A concrete test capability.", "flavor_text": "The domain answers."}
                          for role in ("domain", "general", "army")]
    complete_sovereign(state)
    assert sovereign_kit_check(state)["ready"]
    for key, value in (("scope", "personal"), ("flavor_text", ""), ("parent_id", "other-power"), ("rarity", "COMMON")):
        broken = copy.deepcopy(state)
        broken["abilities"][1][key] = value
        assert sovereign_kit_check(broken)["missing_roles"] == ["general"]
        with pytest.raises(EngineError, match="sovereign powers"):
            complete_sovereign(broken)
    token = copy.deepcopy(state); token["abilities"] = token["abilities"][:1]
    with pytest.raises(EngineError):
        complete_sovereign(token)
    from app.standard_rules import class_kit_check
    for power in state["abilities"]:
        power["source"] = "Class"
    assert "1 passive" in class_kit_check(state)["missing"]


@pytest.mark.parametrize("game", [AGE, SOVEREIGN])
def test_selected_rules_checklist_is_one_page_and_sections_are_lossless(game):
    hardener = rules_page("hardener", 0, game_id=game)
    assert hardener["next_offset"] is None
    import json
    assert len(json.dumps(hardener, ensure_ascii=False)) < 10000
    assert hardener["game_id"] == game
    if game == SOVEREIGN:
        assert "sovereign-progression" in rules_page("index", 0, game_id=game)["content"]
        from app.rule_sections import sections
        source = rule_source(game)["content"]
        for key in ("sovereign-creation", "sovereign-progression", "sovereign-warfare", "sovereign-dashboard", "33"):
            expected = sections(source)[key]
            parts, offset = [], 0
            while True:
                result = rules_page("rulebook", offset, key, game)
                parts.append(result["content"])
                if result["next_offset"] is None:
                    break
                offset = result["next_offset"]
            assert "".join(parts) == source[expected["start"]:expected["end"]]


def test_lists_and_dashboard_are_isolated_without_mutation(engine):
    chat = ChatGame(engine)
    a = chat.create("owner-a", "Ordinary adventure", "ordinary-create")
    b = chat.create("owner-a", "Sovereign adventure", "sovereign-create", game_id=SOVEREIGN)
    chat.create("owner-b", "Other owner", "other-owner-create", game_id=SOVEREIGN)
    assert [r["id"] for r in engine.list_campaigns("owner-a")] == [a["id"]]
    assert [r["id"] for r in engine.list_campaigns("owner-a", SOVEREIGN)] == [b["id"]]
    for _ in range(3):
        assert engine.dashboard("owner-a", game_id=SOVEREIGN)["campaign"] is None
        assert engine.dashboard("owner-a", b["id"])["game_id"] == SOVEREIGN
    assert engine.get_campaign("owner-a", b["id"])["version"] == 1
    with pytest.raises(EngineError, match="different game"):
        engine.dashboard("owner-a", b["id"], AGE)
    with pytest.raises(EngineError):
        engine.get_campaign("owner-b", b["id"])
    with pytest.raises(EngineError):
        apply_changes(b, {"game_id": AGE})


def test_mcp_routes_rules_by_campaign_and_rejects_conflicting_game(web):
    created = tool(web, "create_chat_game", {"name": "Rules routing fixture", "action_id": "mcp-sovereign-create", "game_id": SOVEREIGN})
    cid = created["structuredContent"]["campaign"]["id"]
    result = tool(web, "read_rules", {"campaign_id": cid, "document": "rulebook", "section": "sovereign-creation"})
    assert result["structuredContent"]["game_id"] == SOVEREIGN
    assert "eight" in result["structuredContent"]["content"]
    wrong = tool(web, "read_rules", {"campaign_id": cid, "game_id": AGE})
    assert wrong["isError"] and wrong["structuredContent"]["error"] == "game_mismatch"
    assert tool(web, "list_campaigns", {})["structuredContent"]["campaigns"] == []
    assert len(tool(web, "list_campaigns", {"game_id": SOVEREIGN})["structuredContent"]["campaigns"]) == 1


def test_independent_progression_is_once_only_and_does_not_level_player(engine):
    state = fixture_state(engine)
    awards = [{"id": "mission-general", "kind": "commander", "target_id": "general", "amount": 270, "reason": "Completed a difficult expedition"},
              {"id": "mission-guard", "kind": "formation", "target_id": "guard", "amount": 260, "reason": "Protected the expedition"}]
    next_state = apply_changes(state, {"sovereign_awards": awards})
    assert next_state["character"] == state["character"]
    assert next_state["sovereignty"]["commanders"][0]["level"] == 3
    assert next_state["sovereignty"]["commanders"][0]["xp"] == 20
    assert next_state["sovereignty"]["formations"][0]["veterancy"] == 2
    assert apply_changes(next_state, {"sovereign_awards": awards}) == next_state
    with pytest.raises(EngineError):
        apply_changes(next_state, {"sovereign_awards": [{**awards[0], "amount": 300}]})


def test_domain_milestone_is_fixed_and_development_advances_once(engine):
    state = fixture_state(engine)
    published = apply_changes(state, {"sovereignty": {"domain": {"next_milestone": milestone()}}})
    changed = milestone(); changed["objectives"].append({"id": "errand", "text": "One more errand", "status": "pending"})
    with pytest.raises(EngineError, match="fixed"):
        apply_changes(published, {"sovereignty": {"domain": {"next_milestone": changed}}})
    with pytest.raises(EngineError, match="Finish"):
        apply_changes(published, {"sovereign_development": {"milestone_id": "fortress-two", "choice_id": "mobility"}})
    done = milestone()
    for objective in done["objectives"]: objective["status"] = "done"
    request = {"milestone_id": "fortress-two", "choice_id": "mobility"}
    result = apply_changes(published, {"sovereignty": {"domain": {"next_milestone": done}}, "sovereign_development": request})
    assert result["sovereignty"]["domain"]["level"] == 2
    assert result["sovereignty"]["developments"][0]["choice"]["id"] == "mobility"
    assert result["character"]["level"] == 1
    with pytest.raises(EngineError): apply_changes(result, {"sovereign_development": request})


def foundation_request(state, role):
    target = state["sovereignty"]["domain"] if role == "domain" else state["sovereignty"]["commanders" if role == "general" else "formations"][0]
    field = "capabilities" if role == "domain" else "abilities"
    base = {"id": role, "name": role.title(), "scope": "sovereign", "sovereign_role": role,
            "activation": "Passive", "rarity": "UNIQUE", "mechanics": "The original permanent foundation.", "upgrades": []}
    state["abilities"] = [base]
    state["sovereignty"]["ascension_earned"] = 1
    evolution_id = role+"-upgrade"
    capability = {"id": role+"-capability", "name": "A lasting capability", "description": "A new standing defensive capability.",
                  "activation": "Passive", "duration": "Permanent", "source_evolution_id": evolution_id}
    parent = {**base, "mechanics": "The combined foundation now includes the standing defense.",
              "upgrades": [{"id": evolution_id, "name": "Permanent improvement", "change_display": "Gain a standing defense.",
                            "sovereign_changes": [{"target_id": target["id"], "capability_id": capability["id"]}]}]}
    changed = {**target, field: [*target.get(field, []), capability]}
    strategy = {"domain": changed} if role == "domain" else {"commanders" if role == "general" else "formations":
               [changed, *state["sovereignty"]["commanders" if role == "general" else "formations"][1:]]}
    return {"upsert": {"abilities": [parent]}, "sovereignty": strategy,
            "spend_sovereign_evolution": {"ability_id": role, "evolution_id": evolution_id}}


@pytest.mark.parametrize("role", ["domain", "general", "army"])
def test_level_credit_guarantees_permanent_change_on_actual_foundation(engine, role):
    state = fixture_state(engine)
    request = foundation_request(state, role)
    leveled = apply_changes(state, {"character": {"level": 2}})
    assert leveled["sovereignty"]["ascension_earned"] == 2
    spent = apply_changes(state, request)
    assert spent["sovereignty"]["ascension_spent"] == [role+"-upgrade"]
    assert spent["character"]["skill_points"] == 0
    with pytest.raises(EngineError):
        apply_changes(spent, request)


@pytest.mark.parametrize("defect", ["timed", "active", "missing_target", "unchanged", "wrong_foundation", "no_combined_rules"])
def test_temporary_or_unapplied_sovereign_upgrades_are_rejected(engine, defect):
    state = fixture_state(engine)
    request = foundation_request(state, "domain")
    capability = request["sovereignty"]["domain"]["capabilities"][-1]
    if defect == "timed": capability["duration"] = "3 rounds"
    if defect == "active": capability["activation"] = "Active"
    if defect == "missing_target": request["upsert"]["abilities"][0]["upgrades"][0]["sovereign_changes"][0]["target_id"] = "imaginary-city"
    if defect == "unchanged": request.pop("sovereignty")
    if defect == "wrong_foundation": state["abilities"][0]["activation"] = "Active"
    if defect == "no_combined_rules": request["upsert"]["abilities"][0]["mechanics"] = state["abilities"][0]["mechanics"]
    original = copy.deepcopy(state)
    with pytest.raises(EngineError):
        apply_changes(state, request)
    assert state == original


def test_regular_free_credit_cannot_replace_guaranteed_sovereign_credit(engine):
    state = fixture_state(engine); request = foundation_request(state, "domain")
    state["reward_credits"] = {"earned": 1, "spent": []}
    request["spend_evolution_credit"] = request.pop("spend_sovereign_evolution")
    with pytest.raises(EngineError, match="permanent Sovereign progression choice"):
        apply_changes(state, request)


def orders():
    return {"front_id": "crossing", "phase_id": "first-engagement", "orders": [
        {"id": "guard", "stance": "attack", "target_id": "raiders"},
        {"id": "raiders", "stance": "attack", "target_id": "guard"}]}


def test_battle_has_simultaneous_recorded_losses_and_no_reroll(engine):
    state = fixture_state(engine)
    # 20 to hit, 3 pressure, twice; low morale checks. Both attacks use starting strength.
    values = iter([19, 2, 19, 2, 0, 0])
    result = apply_changes(state, {"fictional_time_seconds": 60, "sovereign_battle": orders()}, dice=Dice(lambda n: next(values)))
    report = result["sovereignty"]["battle_reports"][0]
    assert report["phases"][0]["losses"] == {"guard": 15, "raiders": 15}
    assert [f["strength"] for f in result["sovereignty"]["formations"]] == [85, 85]
    assert report["phases"][0]["attacks"][0]["d20"] == 20
    assert result["sovereignty"]["formations"][0]["xp_total"] == 10
    with pytest.raises(EngineError, match="already recorded"):
        apply_changes(result, {"fictional_time_seconds": 120, "sovereign_battle": orders()}, dice=Dice())


@pytest.mark.parametrize("bad", ["missing_orders", "own_target", "change_stats", "no_time", "frozen"])
def test_battle_requires_preparation_legal_orders_and_active_time(engine, bad):
    state = fixture_state(engine)
    request = orders()
    changes = {"fictional_time_seconds": 60, "sovereign_battle": request}
    if bad == "missing_orders": request["orders"].pop()
    if bad == "own_target": request["orders"][0]["target_id"] = "guard"
    if bad == "change_stats":
        forces = copy.deepcopy(state["sovereignty"]["formations"]); forces[0]["power"] = 20
        changes["sovereignty"] = {"formations": forces}
    if bad == "no_time": changes.pop("fictional_time_seconds")
    if bad == "frozen": state["level_up_freeze"] = True
    with pytest.raises(EngineError): apply_changes(state, changes, dice=Dice())


def test_standing_operation_waits_for_fictional_time(engine):
    state = fixture_state(engine)
    op = {"id": "scout", "name": "Scout the crossing", "commander_id": "general", "formation_ids": ["guard"],
          "objective": "Find a safe route", "mandate": "Scout and return; avoid fighting", "started_at": 0, "due_at": 600, "status": "active"}
    started = apply_changes(state, {"sovereignty": {"operations": [op]}})
    done = {**op, "status": "completed", "outcome": "Located the old bridge"}
    with pytest.raises(EngineError, match="elapsed fictional time"):
        apply_changes(started, {"sovereignty": {"operations": [done]}})
    result = apply_changes(started, {"fictional_time_seconds": 600, "sovereignty": {"operations": [done]}})
    assert result["sovereignty"]["operations"][0]["status"] == "completed"


def test_shared_tooltip_and_copyable_prompt_keep_separate_rows():
    root = Path(__file__).resolve().parents[2]
    prompt = (root / "docs/INTELLIGENT_STORY_UI_PROMPT.txt").read_text(encoding="utf-8")
    assert len(prompt) < 5000
    assert "TOOLTIP ROWS" in prompt and "ALL FOUR SIDES" in prompt
    for game in (AGE, SOVEREIGN):
        assert "separate block/grid rows" in rule_source(game)["content"]


def seed_playing(engine):
    from app import records
    from app.storage import canonical
    from app.chat_game import snapshot
    prepared = fixture_state(engine)
    with engine.store.transaction() as db:
        raw = engine._get(db, "owner-a", prepared["id"])
        raw.update(phase="adventure", paused=False, version=2, sovereignty=prepared["sovereignty"])
        engine._append(db, raw, {"kind": "test_fixture_seed"})
        records.update(db, "campaigns_v1", {"id": raw["id"]}, {"version": 2, "data": canonical(raw)})
        snapshot(db, raw)
    return engine.get_campaign("owner-a", raw["id"])


def test_actual_save_battle_retry_is_identical_and_audit_is_valid(engine):
    state = seed_playing(engine)
    values = iter([19, 2, 19, 2, 0, 0])
    engine.dice = Dice(lambda n: next(values))
    game = ChatGame(engine)
    arguments = ("owner-a", state["id"], "battle-save-retry", state["version"], "Resolve the ordered battle phase",
                 {"fictional_time_seconds": 60, "sovereign_battle": orders()})
    first = game.update(*arguments)
    assert game.update(*arguments) == first
    assert first["campaign"]["version"] == state["version"] + 1
    assert engine.audit("owner-a", state["id"])["integrity_valid"]
    assert len(first["campaign"]["sovereignty"]["battle_reports"]) == 1


def test_sovereign_export_restore_preserves_identity_progression_and_source(engine):
    from app.campaign_archive import CampaignArchive
    state = seed_playing(engine)
    game = ChatGame(engine)
    awarded = game.update("owner-a", state["id"], "sovereign-export-award", state["version"], "Completed expedition",
                          {"sovereign_awards": [{"id": "expedition", "kind": "commander", "target_id": "general",
                                                 "amount": 100, "reason": "Returned from the expedition"}]})["campaign"]
    service = CampaignArchive(engine)
    archive = service.export("owner-a", state["id"])["archive"]
    restored = service.restore("owner-a", archive, "sovereign-restore", True)["campaign"]
    assert restored["id"] != state["id"] and restored["paused"]
    assert restored["game_id"] == SOVEREIGN
    assert restored["sovereignty"] == awarded["sovereignty"]
    assert len(engine.list_campaigns("owner-a", SOVEREIGN)) == 2
    assert engine.list_campaigns("owner-a", AGE) == []
    assert engine.get_campaign("owner-a", state["id"])["version"] == awarded["version"]


def test_legacy_unlabelled_campaigns_stay_in_original_game(engine):
    from app import records
    from app.storage import canonical
    original = ChatGame(engine).create("owner-a", "Legacy fixture", "legacy-game-create")
    with engine.store.transaction() as db:
        raw = engine._get(db, "owner-a", original["id"])
        raw.pop("game_id"); raw.pop("game_rules_version")
        records.update(db, "campaigns_v1", {"id": raw["id"]}, {"data": canonical(raw)})
    assert engine.get_campaign("owner-a", original["id"])["game_id"] == AGE
    assert len(engine.list_campaigns("owner-a", AGE)) == 1
    assert engine.list_campaigns("owner-a", SOVEREIGN) == []


def test_quest_and_sovereign_credits_cannot_pay_for_same_upgrade(engine):
    state = fixture_state(engine)
    state["abilities"] = [{"id": "command", "scope": "sovereign", "rarity": "UNIQUE", "upgrades": []}]
    state["sovereignty"]["ascension_earned"] = 1
    state["reward_credits"] = {"earned": 1, "spent": []}
    request = {"ability_id": "command", "evolution_id": "same"}
    with pytest.raises(EngineError, match="one funding source"):
        apply_changes(state, {"upsert": {"abilities": [{**state["abilities"][0], "upgrades": [{"id": "same"}]}]},
                              "spend_evolution_credit": request, "spend_sovereign_evolution": request})


def test_long_progression_ledger_is_compact_and_portable(engine):
    from app.chat_game import bounded_json
    state = fixture_state(engine)
    for i in range(550):
        state = apply_changes(state, {"sovereign_awards": [{"id": "achievement-" + str(i), "kind": "formation",
            "target_id": "guard", "amount": 1, "reason": "A recorded training accomplishment"}]})
    ledger = state["sovereignty"]["award_ledger"]
    assert sum(key.startswith("achievement-") for key in ledger) == 550
    assert all(len(value) == 64 for value in ledger.values())
    bounded_json(state)
    assert state["sovereignty"]["formations"][0]["xp_total"] == 550


def test_class_force_capacity_and_power_ownership_are_enforced(engine):
    state = fixture_state(engine)
    too_many = copy.deepcopy(state["sovereignty"]["formations"])
    too_many[0]["maximum_strength"] = 2000; too_many[0]["strength"] = 1500
    with pytest.raises(EngineError, match="capacity"):
        apply_changes(state, {"sovereignty": {"formations": too_many}})
    with pytest.raises(EngineError, match="Entity-owned"):
        apply_changes(state, {"upsert": {"abilities": [{"id": "general-power", "scope": "commander"}]}})


@pytest.mark.parametrize("field", ["strength", "side", "status", "target"])
def test_malformed_strategy_values_are_validation_errors(engine, field):
    state = fixture_state(engine)
    if field == "target":
        request = orders(); request["orders"][0]["target_id"] = ["raiders"]
        changes = {"fictional_time_seconds": 60, "sovereign_battle": request}
    else:
        forces = copy.deepcopy(state["sovereignty"]["formations"])
        forces[0][field] = ["wrong type"]
        changes = {"sovereignty": {"formations": forces}}
    with pytest.raises(EngineError) as error:
        apply_changes(state, changes, dice=Dice())
    assert error.value.status == 422


def test_ordinary_update_preserves_passive_foundation_identity(engine):
    state = fixture_state(engine); foundation_request(state, "domain")
    parent = {**state["abilities"][0], "activation": "Active"}
    with pytest.raises(EngineError, match="passive sovereign foundation"):
        apply_changes(state, {"upsert": {"abilities": [parent]}})


def test_legacy_temporary_sovereign_command_counts_as_regular_skill(engine):
    from app.standard_rules import class_kit_check
    from app.sovereignty import sovereign_kit_check
    state = fixture_state(engine); state["character"]["rarity"] = "UNIQUE"
    state["abilities"] = [{"id": "old-command", "source": "Class", "scope": "sovereign", "activation": "Active"}]
    assert "1 active" not in class_kit_check(state)["missing"]
    state["abilities"] += [{"id": role, "name": role.title(), "scope": "sovereign", "sovereign_role": role,
                            "activation": "Passive", "rarity": "UNIQUE", "mechanics": "The existing foundation.",
                            "flavor_text": "The realm endures."} for role in ("domain", "general", "army")]
    assert sovereign_kit_check(state)["ready"]


def test_starting_sovereign_upgrade_is_free_before_any_level_up(engine):
    state = fixture_state(engine)
    assert state["character"]["level"] == 1 and state["sovereignty"]["ascension_earned"] == 1
    request = foundation_request(state, "domain")
    spent = apply_changes(state, request)
    assert len(spent["sovereignty"]["ascension_spent"]) == 1 and spent["character"]["skill_points"] == 0
    next_level = apply_changes(spent, {"character": {"level": 2}})
    assert next_level["sovereignty"]["ascension_earned"] - len(next_level["sovereignty"]["ascension_spent"]) == 1


def test_old_save_receives_missing_starting_upgrade_once_without_changing_its_kit(engine):
    from app.sovereignty import STARTING_EVOLUTION
    state = fixture_state(engine)
    state["sovereignty"]["award_ledger"].pop(STARTING_EVOLUTION)
    state["sovereignty"]["ascension_earned"] = 0
    after = apply_changes(state, {"notes": "Record existing draft"})
    assert after["sovereignty"]["ascension_earned"] == 1
    assert after["abilities"] == state["abilities"] and after["character"] == state["character"]
    assert apply_changes(after, {"notes": "Another save"})["sovereignty"]["ascension_earned"] == 1


def test_two_already_applied_creation_overrides_are_accounted_without_reapplying_or_spending_level_two(engine):
    from app.sovereignty import STARTING_EVOLUTION
    domain, army = fixture_state(engine), fixture_state(engine)
    domain = apply_changes(domain, foundation_request(domain, "domain"))
    army = apply_changes(army, foundation_request(army, "army"))
    state = copy.deepcopy(domain)
    state["abilities"] += army["abilities"]
    state["sovereignty"]["formations"] = army["sovereignty"]["formations"]
    state["creation"]["bonus_sovereign_selected_ids"] = ["domain-upgrade", "army-upgrade"]
    state["sovereignty"]["award_ledger"].pop(STARTING_EVOLUTION)
    state["sovereignty"].update(ascension_earned=0, ascension_spent=[])
    after = apply_changes(state, {"notes": "Preserve both previously chosen creation upgrades"})
    assert after["abilities"] == state["abilities"]
    assert after["sovereignty"]["domain"] == state["sovereignty"]["domain"]
    assert after["sovereignty"]["formations"] == state["sovereignty"]["formations"]
    assert after["sovereignty"]["ascension_earned"] == 2
    assert set(after["sovereignty"]["ascension_spent"]) == {"domain-upgrade", "army-upgrade"}
    next_level = apply_changes(after, {"character": {"level": 2}})
    assert next_level["sovereignty"]["ascension_earned"] - len(next_level["sovereignty"]["ascension_spent"]) == 1
