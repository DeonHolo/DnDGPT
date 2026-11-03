import copy

import pytest

from app.chat_game import ChatGame, apply_changes
from app.engine import EngineError
from app.game_profiles import AGE, SOVEREIGN, rule_source
from app.personal_powers import summary
from app.rules import RARITIES
from app.sovereign_play import PROFILE, growth
from app.sovereignty import complete_sovereign
from .test_personal_powers import core_powers, upgrade_request
from .test_sovereign import fixture_state, orders


def body(mode="bound"):
    return {"mode": mode, "form": "Living dungeon heart", "description": "A rooted mineral intelligence.",
            "primary_attribute": "INT", "movement": "Fixed core; manifestations act in integrated holdings.",
            "manipulation": "Works through its recorded stone manifestations.",
            "communication": "Speaks through owned chambers.", "perception": "Senses disturbances in owned rooms.",
            "vulnerability": "The exposed core can be attacked.", "core_location": "The buried heart chamber",
            "equipment_slots": {"Head": "Crown socket", "Chest": "Core shell",
                                "Main Hand": "Manifestation focus", "Artifact": "Heart relic"}}


def embodied_state(engine, rarity="RARE", mode="bound"):
    state = fixture_state(engine)
    state["creation"].update(sovereign_ruleset=PROFILE, sovereign_body=body(mode))
    state["sovereignty"]["ascension_earned"] = 2
    state["character"]["rarity"] = rarity
    if mode == "bound":
        state["character"].update(movement=0, movement_meters=0, movement_mm=0)
    state["abilities"] = [{**power, "rarity": rarity} for power in core_powers()]
    state["abilities"] += [{"id": role, "name": role.title(), "scope": "sovereign", "sovereign_role": role,
                            "activation": "Passive", "rarity": rarity, "mechanics": "The actual working foundation.",
                            "flavor_text": "The stone answers.", "upgrades": []} for role in ("domain", "general", "army")]
    state["sovereignty"]["domain"].update(
        name="The buried citadel", description="A working fortress around the sovereign's core.",
        holdings=[{"id": "keep", "name": "The old keep", "description": "The starting domain.",
                   "status": "integrated", "integration_basis": "The class awakens in its actual home."}],
        zones=[{"id": "heart", "name": "Heart chamber", "description": "The core's physical room.", "connections": ["gate"]},
               {"id": "gate", "name": "Outer gate", "description": "A real chokepoint.", "connections": ["heart"]}],
        assets=[{"id": "core", "name": "Dungeon heart", "description": "The actual character.",
                 "zone_id": "heart", "character_core": True},
                {"id": "door", "name": "Iron gate", "description": "A physical barrier.",
                 "zone_id": "gate", "hp": 30, "hp_max": 30, "defense": 14}],
        encounters=[{"id": "raid", "name": "Hold the gate", "situation": "Raiders approach the keep.",
                     "status": "active", "zone_ids": ["gate", "heart"],
                     "objectives": [{"id": "stop", "text": "Repel the raid", "status": "pending"}]}])
    return state


def test_new_campaign_has_matching_two_pick_defaults(engine):
    state = ChatGame(engine).create("owner-a", "New embodied", "embodied-defaults", True, SOVEREIGN)
    assert state["creation"]["sovereign_ruleset"] == PROFILE
    assert state["sovereignty"]["ascension_earned"] == 2
    assert state["personal_progression"]["upgrades_available"] == 2
    assert growth(state)["sovereign_per_level"] == 2
    leveled = copy.deepcopy(state)
    leveled.update(phase="adventure", paused=False)
    after = apply_changes(leveled, {"character": {"level": 4}})
    assert after["sovereignty"]["ascension_earned"] == 8
    assert summary(after)["upgrades_available"] == 9  # opening 2 + six normal + one major


@pytest.mark.parametrize("rarity", RARITIES)
@pytest.mark.parametrize("mode", ["mobile", "bound", "distributed"])
def test_every_grade_and_body_can_complete_without_unique_override(engine, rarity, mode):
    state = embodied_state(engine, rarity, mode)
    complete_sovereign(state)
    broken = copy.deepcopy(state)
    broken["abilities"][-1]["rarity"] = "COMMON" if rarity != "COMMON" else "RARE"
    with pytest.raises(EngineError, match="sovereign powers"):
        complete_sovereign(broken)


def test_future_growth_request_needs_no_approval_or_counter_edit_even_paused(engine):
    state = embodied_state(engine)
    state.update(paused=True, level_up_freeze=True)
    request = {"creation": {"sovereign_growth": {"sovereign_per_level": 3},
                            "sovereign_growth_reason": "The player requests three future permanent developments per level."}}
    after = apply_changes(state, request)
    assert growth(after)["sovereign_per_level"] == 3
    assert after["sovereignty"] == state["sovereignty"]
    assert after["personal_powers"] == state["personal_powers"]
    assert after["character"] == state["character"]
    assert after["paused"] and after["level_up_freeze"] and after["fictional_time_seconds"] == 0
    assert apply_changes(after, request) == after
    with pytest.raises(EngineError, match="explicit request"):
        apply_changes(state, {"creation": {"sovereign_growth": {"sovereign_per_level": 3}}})
    with pytest.raises(EngineError, match="starting rewards"):
        apply_changes(state, {"creation": {"sovereign_growth": {"sovereign_start": 3},
                                          "sovereign_growth_reason": "Change future rate"}})


def test_legacy_campaign_can_change_future_rate_without_migration(engine):
    state = fixture_state(engine)
    state["creation"].pop("sovereign_ruleset", None)
    state["sovereignty"]["ascension_earned"] = 1
    after = apply_changes(state, {"creation": {"sovereign_growth": {"sovereign_per_level": 2},
                                              "sovereign_growth_reason": "Player asks for two per future level."}})
    assert "sovereign_ruleset" not in after["creation"]
    assert after["sovereignty"] == state["sovereignty"]
    gained = apply_changes(after, {"character": {"level": 2}})
    assert gained["sovereignty"]["ascension_earned"] == 3


def test_custom_starting_counts_configure_once_without_changing_other_creation_fields(engine):
    state = ChatGame(engine).create("owner-a", "Custom counts", "custom-counts", True, SOVEREIGN)
    after = apply_changes(state, {"creation": {"sovereign_growth": {"personal_start": 3, "sovereign_start": 3}}})
    assert after["creation"]["sovereign_ruleset"] == PROFILE
    assert after["personal_powers"]["earned"] == after["sovereignty"]["ascension_earned"] == 3
    assert apply_changes(after, {"creation": {"name_note": "Keep draft"}})["sovereignty"] == after["sovereignty"]


def two_developments(state):
    parent = copy.deepcopy(next(row for row in state["abilities"] if row["id"] == "domain"))
    domain = copy.deepcopy(state["sovereignty"]["domain"])
    for identity, cap_id in (("domain-upgrade", "domain-capability"), ("second-upgrade", "second-capability")):
        parent["upgrades"].append({"id": identity, "name": "Development "+identity, "rarity": "RARE",
                                   "change_display": "Gain a concrete standing defense.",
                                   "sovereign_changes": [{"target_id": domain["id"], "capability_id": cap_id}]})
        domain["capabilities"].append({"id": cap_id, "name": "Capability "+identity,
                                       "description": "A lasting actual owner capability.", "activation": "Passive",
                                       "duration": "Permanent", "source_evolution_id": identity})
    parent["mechanics"] += " Both actual standing defenses are integrated."
    return {"upsert": {"abilities": [parent]}, "sovereignty": {"domain": domain},
            "spend_sovereign_evolution": [{"ability_id": "domain", "evolution_id": identity}
                                          for identity in ("domain-upgrade", "second-upgrade")]}


def test_two_developments_on_one_foundation_save_together_and_keep_history(engine):
    state = embodied_state(engine)
    request = two_developments(state)
    after = apply_changes(state, request)
    assert after["sovereignty"]["ascension_spent"] == ["domain-upgrade", "second-upgrade"]
    assert len(next(row for row in after["abilities"] if row["id"] == "domain")["upgrades"]) == 2
    assert len(after["sovereignty"]["domain"]["capabilities"]) == 3
    with pytest.raises(EngineError):
        apply_changes(after, request)
    assert state["sovereignty"]["ascension_spent"] == []


def test_permanent_development_can_unlock_actual_active_owner_technique(engine):
    state = embodied_state(engine)
    request = two_developments(state)
    cap = request["sovereignty"]["domain"]["capabilities"][-1]
    cap.update(activation="Action", permanent_unlock=True, mechanics="Spend the recorded action and 8 MP to fire the installed lance.")
    assert apply_changes(state, request)["sovereignty"]["ascension_spent"]
    cap["cooldown_remaining"] = 2  # Use recovery is distinct from the lifetime of the acquired technique.
    assert apply_changes(state, request)["sovereignty"]["ascension_spent"]
    cap["remaining_rounds"] = 3
    with pytest.raises(EngineError, match="lasting foundation"):
        apply_changes(state, request)


def test_quest_and_personal_refinements_share_one_parent_and_one_save(engine):
    state = embodied_state(engine)
    state["reward_credits"] = {"earned": 1, "spent": []}
    request = upgrade_request(state, [("personal-0", "personal-one"), ("personal-0", "quest-one")])
    request["spend_personal_upgrades"] = [{"ability_id": "personal-0", "upgrade_id": "personal-one"}]
    request["spend_evolution_credit"] = {"ability_id": "personal-0", "evolution_id": "quest-one"}
    after = apply_changes(state, request)
    assert after["personal_powers"]["spent"] == ["personal-one"]
    assert after["reward_credits"]["spent"] == ["quest-one"]
    request["spend_personal_upgrades"].append({"ability_id": "personal-0", "upgrade_id": "quest-one"})
    with pytest.raises(EngineError):
        apply_changes(state, request)


def test_bound_body_has_zero_movement_and_only_its_real_equipment_slots(engine):
    state = embodied_state(engine)
    for change in ({"movement_mm": 6000}, {"movement": 6}):
        with pytest.raises(EngineError, match="zero ordinary locomotion"):
            apply_changes(state, {"character": change})
    item = {"id": "relic", "name": "Heart relic", "rarity": "RARE"}
    with pytest.raises(EngineError, match="actual equipment"):
        apply_changes(state, {"upsert": {"inventory": [item]}, "equipment": {"Feet": "relic"}})
    after = apply_changes(state, {"upsert": {"inventory": [item]}, "equipment": {"Artifact": "relic"}})
    assert after["character"]["movement_mm"] == 0
    assert state["inventory"] == []


@pytest.mark.parametrize("defect", ["unfinished", "moving_finish", "duplicate_hp", "missing_zone", "reopen"])
def test_tactical_records_preserve_finite_objectives_and_one_core_health_pool(engine, defect):
    state = embodied_state(engine)
    domain = copy.deepcopy(state["sovereignty"]["domain"])
    if defect == "unfinished": domain["encounters"][0].update(status="completed", outcome="Claimed victory")
    if defect == "moving_finish": domain["encounters"][0]["objectives"][0]["text"] = "Also conquer another keep"
    if defect == "duplicate_hp": domain["assets"][0].update(hp=100, hp_max=100, defense=20)
    if defect == "missing_zone": domain["assets"][1]["zone_id"] = "imaginary-gate"
    if defect == "reopen":
        state["sovereignty"]["domain"]["encounters"][0].update(status="completed", outcome="The raid was repelled.")
        state["sovereignty"]["domain"]["encounters"][0]["objectives"][0]["status"] = "done"
    before = copy.deepcopy(state)
    with pytest.raises(EngineError):
        apply_changes(state, {"sovereignty": {"domain": domain}})
    assert state == before


def test_delegated_character_xp_is_once_only_and_levels_both_development_tracks(engine):
    state = embodied_state(engine)
    state["character"].update(hp=1, mp=2)
    award = {"id": "repelled-raid-ruler", "kind": "character", "target_id": state["id"],
             "amount": 100, "reason": "The authorized defense decisively repelled the raid."}
    after = apply_changes(state, {"sovereign_awards": [award]})
    assert after["character"]["level"] == 2 and after["level_up_freeze"] and not after["paused"]
    assert after["character"]["hp"] == after["character"]["hp_max"]
    assert after["character"]["skill_points"] == after["character"]["talent_points"] == 0
    assert after["sovereignty"]["ascension_earned"] == 4
    assert summary(after)["upgrades_available"] == 4
    resumed = copy.deepcopy(after); resumed["level_up_freeze"] = False
    assert apply_changes(resumed, {"sovereign_awards": [award]})["character"] == after["character"]
    with pytest.raises(EngineError, match="also add it manually"):
        apply_changes(state, {"sovereign_awards": [award], "character": {"xp": 100}})


def test_tactical_default_requires_explicit_fast_resolution_for_abstract_phases(engine):
    state = embodied_state(engine)
    with pytest.raises(EngineError, match="resolution=fast"):
        apply_changes(state, {"sovereign_battle": orders(), "fictional_time_seconds": 60})


def test_effective_book_has_no_retired_acquisition_boards_or_automatic_unique():
    book = rule_source(SOVEREIGN)["content"]
    assert "NORMAL RARITY IS THE CREATION DEFAULT" in book
    assert "ONE of TWO selected Signature" not in book
    assert "Offer eight mechanically distinct UNIQUE" not in book
    assert "Generate a humanlike bipedal" not in rule_source(SOVEREIGN, "hardener")["content"]
    for phrase in ("five fresh talents", "+1 Skill Point", "four-level 3+2 Breakthrough", "exactly three Class Breakthrough offers"):
        assert phrase not in book
    assert rule_source(AGE)["source_sha256"] == "94ec7b0882418a00fc6140c09fa725984be02aaa3d70f9cf7664fcb55399a529"


def prepared_campaign(engine):
    game = ChatGame(engine)
    created = game.create("owner-a", "Portable bound core", "embodied-portable-create", True, SOVEREIGN)
    prepared = embodied_state(engine)
    patch = {key: prepared[key] for key in ("character", "creation", "sovereignty")}
    patch["upsert"] = {"abilities": prepared["abilities"]}
    current = game.update("owner-a", created["id"], "embodied-portable-seed", 1,
                          "Prepare a rare bound character and actual defenses", patch)["campaign"]
    return game, current


def test_real_save_batches_two_developments_with_retry_owner_and_version_guards(engine):
    game, state = prepared_campaign(engine)
    patch = two_developments(state)
    first = game.update("owner-a", state["id"], "embodied-two-picks", state["version"], "Choose both developments", patch)
    assert first["campaign"]["sovereignty"]["ascension_spent"] == ["domain-upgrade", "second-upgrade"]
    assert game.update("owner-a", state["id"], "embodied-two-picks", state["version"], "Choose both developments", patch) == first
    with pytest.raises(EngineError):
        game.update("owner-b", state["id"], "embodied-other-owner", first["campaign"]["version"], "Unauthorized", patch)
    with pytest.raises(EngineError):
        game.update("owner-a", state["id"], "embodied-stale", state["version"], "Stale selection", patch)
    assert engine.get_campaign("owner-a", state["id"])["version"] == first["campaign"]["version"]


def test_real_paused_growth_change_needs_no_proposal_and_keeps_earned_state(engine):
    from app import records
    from app.storage import canonical
    game, state = prepared_campaign(engine)
    # A deliberately paused/frozen local fixture, without advancing its fictional clock.
    with engine.store.transaction() as db:
        raw = engine._get(db, "owner-a", state["id"])
        raw.update(phase="adventure", paused=True, level_up_freeze=True)
        records.update(db, "campaigns_v1", {"id": state["id"]}, {"data": canonical(raw)})
    request = {"creation": {"sovereign_growth": {"sovereign_per_level": 3},
                            "sovereign_growth_reason": "The player explicitly asks for three future selections per level."}}
    result = game.update("owner-a", state["id"], "embodied-future-rate", state["version"], "Change future growth", request)
    after = result["campaign"]
    assert "proposal" not in result and after["version"] == state["version"] + 1
    assert after["paused"] and after["level_up_freeze"] and after["fictional_time_seconds"] == 0
    assert after["sovereignty"] == raw["sovereignty"] and after["character"] == raw["character"]
    assert growth(after)["sovereign_per_level"] == 3


def test_bound_body_scene_and_both_developments_survive_portable_restore(engine):
    from app.campaign_archive import CampaignArchive
    game, state = prepared_campaign(engine)
    state = game.update("owner-a", state["id"], "embodied-portable-picks", state["version"],
                        "Apply both actual developments", two_developments(state))["campaign"]
    archive = CampaignArchive(engine)
    restored = archive.restore("owner-a", archive.export("owner-a", state["id"])["archive"],
                               "embodied-restore", True)["campaign"]
    assert restored["id"] != state["id"] and restored["paused"]
    assert restored["creation"] == state["creation"]
    assert restored["sovereignty"] == state["sovereignty"]
    assert restored["abilities"] == state["abilities"]
    assert restored["character"] == state["character"]
    assert engine.get_campaign("owner-a", state["id"])["version"] == state["version"]
