"""Exercise the actual authenticated tools, lifecycle, and immutable equipment draw."""
import copy
from collections import Counter
from itertools import product

import pytest

from app.outfitting import BUDGETS, SUPPORT, TIERS, slot_pool, starting_outfit
from app.rules import EQUIPMENT_SLOTS
from .test_server import tool

SLOT_PREFERENCES = [
    {"slot": "Artifact", "weight": 3, "basis": "The chosen Warden channels its boundary-keeper tradition through an implement"},
    {"slot": "Ring 1", "weight": 2, "basis": "A seal ring fits the chosen class's warding magic"},
]


def prepare(web, game_id="age-of-convergence", rarity="COMMON"):
    state = tool(web, "create_chat_game", {"name": "Disposable direct-play fixture",
                 "action_id": "direct-create", "disposable": True, "game_id": game_id})["structuredContent"]["campaign"]
    state = tool(web, "save_chat_update", {"campaign_id": state["id"], "action_id": "class-selected",
                 "expected_version": state["version"], "summary": "Actual class choice",
                 "changes": {"character": {"class_name": "Door Warden", "rarity": rarity}}})["structuredContent"]["campaign"]
    draw = {"campaign_id": state["id"], "action_id": "starting-outfit-" + state["id"],
            "rolls": [{"label": "Starting equipment", "kind": "outfitting", "class_rarity": rarity,
                       "slot_preferences": SLOT_PREFERENCES}]}
    receipt = tool(web, "roll_game_random", draw)
    assert not receipt.get("isError"), receipt
    plan = receipt["structuredContent"]["results"][0]["result"]
    items = [{"id": f"outfit-{i}", "name": f"Fixture {row['role']}", "rarity": row["rarity"],
              "effects": ["Recorded equipment effect for this disposable test"], "weight_kg": 1}
             for i, row in enumerate(plan["items"])]
    changes = {"character": {"name": "Fixture Warden", "class_name": "Door Warden",
               "background": "Keeper of the boundary", "attributes": {"STR": 7, "LCK": 9},
               "story_summary": "The boundary keeper's chosen training shapes how they guard the crossing."},
               "opening_preview": "At the crossing, a messenger waits for your decision.",
               "current_location": "Fixture crossing", "upsert": {"inventory": items},
               "equipment": dict(zip((r["slot"] for r in plan["items"]), [r["id"] for r in items])),
               "creation": {"outfitting": {"action_id": draw["action_id"], **plan,
                                           "item_ids": [r["id"] for r in items]}}}
    args = {"campaign_id": state["id"], "action_id": "direct-finish", "expected_version": state["version"],
            "summary": "Complete actual choices, story, equipment and opening", "changes": changes,
            "begin_adventure": True}
    return state, draw, receipt, args


def test_final_choices_open_the_adventure_in_one_idempotent_save(web):
    draft, draw, receipt, args = prepare(web)
    result = tool(web, "save_chat_update", args)
    assert not result.get("isError"), result
    state = result["structuredContent"]["campaign"]
    assert state["phase"] == "adventure" and not state["paused"]
    assert state["version"] == draft["version"] + 1 and state["fictional_time_seconds"] == 0
    assert state["character"]["story_summary"] == args["changes"]["character"]["story_summary"]
    assert len(state["inventory"]) == 4
    public_item = receipt["structuredContent"]["results"][0]["result"]["items"][0]
    assert "roll" not in public_item and "slot_roll" not in public_item
    audit = tool(web, "get_game_roll", {"action_id": draw["action_id"], "show_rolls": True})
    assert "slot_roll" in audit["structuredContent"]["results"][0]["result"]["items"][0]
    reopened = tool(web, "render_dashboard", {"campaign_id": state["id"]})
    assert not reopened["_meta"].get("approval")
    assert tool(web, "save_chat_update", args)["structuredContent"] == result["structuredContent"]
    assert tool(web, "roll_game_random", draw)["structuredContent"] == receipt["structuredContent"]
    assert tool(web, "get_campaign", {"campaign_id": state["id"]})["structuredContent"]["campaign"] == state


@pytest.mark.parametrize("missing", ["story", "equipment", "background", "opening", "slot"])
def test_incomplete_creation_is_atomic_without_requesting_player_approval(web, missing):
    draft, _, _, args = prepare(web)
    if missing == "story":
        args["changes"]["character"].pop("story_summary")
    elif missing == "equipment":
        args["changes"]["equipment"] = {}
    elif missing == "background":
        args["changes"]["character"].pop("background")
    elif missing == "slot":
        equipment = args["changes"]["equipment"]
        other = next(slot for slot in EQUIPMENT_SLOTS if slot not in equipment)
        equipment[other] = equipment.pop(next(iter(equipment)))
    else:
        args["changes"].pop("opening_preview")
    result = tool(web, "save_chat_update", args)
    assert result.get("isError")
    state = tool(web, "get_campaign", {"campaign_id": draft["id"]})["structuredContent"]["campaign"]
    assert state == draft


def test_retired_approvals_are_not_proposed_and_outfit_cannot_be_redrawn(web):
    draft, draw, _, _ = prepare(web)
    for kind in ("confirm_chat_character", "start_chat_adventure"):
        result = tool(web, "propose_action", {"campaign_id": draft["id"], "action_id": "old-" + kind,
                      "expected_version": draft["version"], "kind": kind, "payload": {}})
        assert not result.get("isError"), result
        handoff = result["structuredContent"]
        assert handoff["approval_required"] is False and handoff["committed"] is False
        assert handoff["next_action"]["arguments"]["changes"] == {"begin_adventure": True}
        assert not tool(web, "render_dashboard", {"campaign_id": draft["id"]})["_meta"].get("approval")
    changed = copy.deepcopy(draw)
    changed["action_id"] = "another-outfit"
    assert tool(web, "roll_game_random", changed).get("isError")
    changed = copy.deepcopy(draw)
    changed["rolls"][0]["slot_preferences"][0]["weight"] = 2
    assert tool(web, "roll_game_random", changed)["structuredContent"]["error"] == "idempotency_conflict"
    assert tool(web, "roll_game_random", {**draw, "rolls": [*draw["rolls"],
        {**draw["rolls"][0], "label": "Second outfit"}]}).get("isError")


def test_cached_tool_shape_and_retired_start_handoff_complete_saved_draft(web):
    draft, _, _, args = prepare(web)
    prepared = tool(web, "save_chat_update", {**args, "action_id": "prepare-final-build", "begin_adventure": False})
    before = prepared["structuredContent"]["campaign"]
    assert before["phase"] == "character_draft" and before["paused"]
    handoff = tool(web, "propose_action", {"campaign_id": draft["id"], "action_id": "cached-start",
                   "expected_version": before["version"], "kind": "start_chat_adventure", "payload": {}})
    assert not handoff.get("isError"), handoff
    direct = handoff["structuredContent"]["next_action"]["arguments"]
    # Exactly the old five-field tool schema: no new top-level flag is required.
    assert set(direct) == {"campaign_id", "action_id", "expected_version", "summary", "changes"}
    assert tool(web, "get_campaign", {"campaign_id": draft["id"]})["structuredContent"]["campaign"] == before
    result = tool(web, "save_chat_update", direct)
    assert not result.get("isError"), result
    after = result["structuredContent"]["campaign"]
    assert after["phase"] == "adventure" and not after["paused"]
    assert after["version"] == before["version"] + 1 and after["fictional_time_seconds"] == 0
    assert after["abilities"] == before["abilities"] and after["inventory"] == before["inventory"]
    assert tool(web, "save_chat_update", direct)["structuredContent"] == result["structuredContent"]
    equivalent = {**direct, "changes": {}, "begin_adventure": True}
    assert tool(web, "save_chat_update", equivalent)["structuredContent"] == result["structuredContent"]


@pytest.mark.parametrize("flag", [1, "true", None, False])
def test_nested_start_is_explicit_boolean_and_keeps_incomplete_draft_atomic(web, flag):
    draft, _, _, _ = prepare(web)
    result = tool(web, "save_chat_update", {"campaign_id": draft["id"], "action_id": "bad-start",
                  "expected_version": draft["version"], "summary": "Cannot start incomplete choices",
                  "changes": {"begin_adventure": flag}})
    assert result.get("isError")
    assert tool(web, "get_campaign", {"campaign_id": draft["id"]})["structuredContent"]["campaign"] == draft


def test_retired_start_handoff_retains_ownership_and_version_guards(web, tokens):
    draft, _, _, _ = prepare(web)
    args = {"campaign_id": draft["id"], "action_id": "stale-start", "expected_version": 1,
            "kind": "start_chat_adventure", "payload": {}}
    assert tool(web, "propose_action", args)["structuredContent"]["error"] == "version_conflict"
    web.headers["Authorization"] = "Bearer " + tokens(subject="user-b")
    assert tool(web, "propose_action", {**args, "expected_version": draft["version"]}).get("isError")


def test_sovereign_starting_gift_and_cached_start_work_together_without_approvals(web, engine):
    from .test_sovereign import fixture_state
    _, _, _, args = prepare(web, "sovereign-system", "UNIQUE")
    strategy = fixture_state(engine)["sovereignty"]
    parents = [{"id": role, "name": role.title(), "scope": "sovereign", "sovereign_role": role,
                "activation": "Passive", "rarity": "UNIQUE", "mechanics": "The existing permanent foundation.",
                "flavor_text": "The realm remembers."} for role in ("domain", "general", "army")]
    regular = [{"id": str(i), "name": "Fixture skill "+str(i), "activation": activation,
                "source": "Class", "group": group, "rarity": "UNIQUE"}
               for i, (activation, group) in enumerate([(a, "Combat") for a in
                   ("Active", "Passive", "Reaction", "Free action")] + [("Active", "Utility")]*2)]
    args["changes"].update(sovereignty=strategy)
    args["changes"]["upsert"]["abilities"] = parents + regular
    ready = tool(web, "save_chat_update", {**args, "action_id": "complete-sovereign-build", "begin_adventure": False})
    assert not ready.get("isError"), ready
    before = ready["structuredContent"]["campaign"]
    cap = {"id": "standing-workshop", "name": "Standing workshop", "description": "The workshop permanently refits two constructs.",
           "source_evolution_id": "starting-gift", "activation": "Passive", "duration": "Permanent"}
    parent = {**parents[0], "mechanics": "The permanent domain includes a workshop that refits two constructs.",
              "upgrades": [{"id": "starting-gift", "name": "Workshop expansion", "change_display": cap["description"],
                            "sovereign_changes": [{"target_id": "domain", "capability_id": cap["id"]}]}]}
    start = {"campaign_id": before["id"], "action_id": "sovereign-cached-start", "expected_version": before["version"],
             "summary": "Apply the chosen free starting evolution and open the saved first scene",
             "changes": {"begin_adventure": True, "upsert": {"abilities": [parent]},
                         "spend_sovereign_evolution": {"ability_id": "domain", "evolution_id": "starting-gift"},
                         "sovereignty": {"domain": {"capabilities": [*strategy["domain"]["capabilities"], cap]}}}}
    result = tool(web, "save_chat_update", start)
    assert not result.get("isError"), result
    after = result["structuredContent"]["campaign"]
    assert after["phase"] == "adventure" and not after["paused"] and after["fictional_time_seconds"] == 0
    assert after["character"]["level"] == 1 and after["character"]["skill_points"] == 0
    assert after["sovereignty"]["ascension_spent"] == ["starting-gift"]
    assert not tool(web, "render_dashboard", {"campaign_id": after["id"]})["_meta"].get("approval")
    assert tool(web, "save_chat_update", start)["structuredContent"] == result["structuredContent"]
    leveled = tool(web, "save_chat_update", {"campaign_id": after["id"], "action_id": "sovereign-level-two",
                   "expected_version": after["version"], "summary": "Fixture Level 2 progression",
                   "changes": {"character": {"level": 2}}})["structuredContent"]["campaign"]
    assert leveled["sovereignty"]["ascension_earned"] - len(leveled["sovereignty"]["ascension_spent"]) == 1


def test_outfit_context_is_validated_before_any_other_roll(engine):
    from app.chat_game import ChatGame
    from app.engine import EngineError
    from app.game_random import GameRandom
    from app.rules import Dice
    game = ChatGame(engine)
    state = game.create("owner-a", "Disposable outfit validation", "outfit-validation", True)
    box = GameRandom(engine.store, Dice(lambda _: pytest.fail("Invalid batch consumed randomness")), engine)
    rows = [{"label": "Other legal roll", "kind": "dice", "sides": 20},
            {"label": "Outfit", "kind": "outfitting", "class_rarity": "COMMON"}]
    with pytest.raises(EngineError) as error:
        box.roll("owner-a", "starting-outfit-" + state["id"], rows, state["id"])
    assert error.value.code == "class_required"
    state = game.update("owner-a", state["id"], "save-picked-class", state["version"],
                        "Actual class selected", {"character": {"class_name": "Fixture class"}})["campaign"]
    rows[-1]["class_rarity"] = "UNIQUE"
    with pytest.raises(EngineError) as error:
        box.roll("owner-a", "starting-outfit-" + state["id"], rows, state["id"])
    assert error.value.code == "rarity_mismatch"
    rows[-1]["class_rarity"] = "COMMON"
    with pytest.raises(EngineError) as error:
        box.roll("owner-a", "starting-outfit-" + state["id"], rows, state["id"])
    assert error.value.code == "slot_preferences_required"


def test_advancement_selection_can_finish_and_continue_in_same_save(web):
    _, _, _, args = prepare(web)
    state = tool(web, "save_chat_update", args)["structuredContent"]["campaign"]
    freeze = {"campaign_id": state["id"], "action_id": "level-earned", "expected_version": state["version"],
              "summary": "Earned level; real choices pending", "changes": {"level_up_freeze": True,
              "character": {"level": 2, "attribute_points": 1, "skill_points": 1, "talent_points": 1}}}
    state = tool(web, "save_chat_update", freeze)["structuredContent"]["campaign"]
    follow = {"campaign_id": state["id"], "action_id": "chosen-and-continue", "expected_version": state["version"],
              "summary": "Apply selected attribute, bank other tracks and continue ordered travel",
              "changes": {"character": {"attributes": {"STR": 9}, "attribute_points": 0},
                          "advancement": {"skill": "banked", "talent": "banked"},
                          "level_up_freeze": False, "fictional_time_seconds": 60}}
    result = tool(web, "save_chat_update", follow)
    assert not result.get("isError"), result
    state = result["structuredContent"]["campaign"]
    assert not state["level_up_freeze"] and not state["paused"]
    assert state["fictional_time_seconds"] == 60 and state["character"]["skill_points"] == 1
    assert tool(web, "save_chat_update", follow)["structuredContent"] == result["structuredContent"]


def test_all_equipment_draw_boundaries_fit_budget_and_rarity_floors():
    class Draws:
        def __init__(self, values):
            self.values = iter(values)
        def roll(self, sides):
            return next(self.values) if sides == 100 else 1

    for rarity, values in product(TIERS, product((1, 20, 21, 75, 76, 100), repeat=4)):
        plan = starting_outfit(rarity, Draws(values), SLOT_PREFERENCES)
        assert plan["budget"] == BUDGETS[rarity]
        assert sum(item["cost"] for item in plan["items"]) + 6 + plan["unspent"] == plan["budget"]
        assert plan["unspent"] >= 0 and len(plan["items"]) == 4
        assert all(TIERS.index(row["rarity"]) >= TIERS.index(SUPPORT[rarity]) for row in plan["items"][1:])
        if rarity == "UNIQUE":
            assert plan["items"][0]["rarity"] in {"LEGENDARY", "UNIQUE"}


class SlotTicket:
    def __init__(self, ticket):
        self.ticket = ticket

    def roll(self, sides):
        if sides == 100:
            return 1
        ticket, self.ticket = self.ticket or 1, None
        assert 1 <= ticket <= sides
        return ticket


def test_every_slot_can_receive_the_highest_grade_item():
    pool = slot_pool(SLOT_PREFERENCES)
    ticket = 1
    for candidate in pool:
        plan = starting_outfit("UNIQUE", SlotTicket(ticket), SLOT_PREFERENCES)
        assert plan["items"][0]["slot"] == candidate["slot"]
        assert plan["items"][0]["rarity"] == "UNIQUE"
        assert len({row["slot"] for row in plan["items"]}) == 4
        ticket += candidate["weight"]
    assert {row["slot"] for row in pool} == set(EQUIPMENT_SLOTS)


def test_weighted_slot_probabilities_and_exclusions_are_exact():
    preferences = SLOT_PREFERENCES + [{"slot": "Chest", "weight": 0, "basis": "The selected form cannot wear a chest item"}]
    pool = slot_pool(preferences)
    counts = Counter(starting_outfit("UNIQUE", SlotTicket(ticket), preferences)["items"][0]["slot"]
                     for ticket in range(1, sum(row["weight"] for row in pool) + 1))
    assert counts == Counter({row["slot"]: row["weight"] for row in pool})
    assert "Chest" not in counts


@pytest.mark.parametrize("preferences", [
    [], [{"slot": "Unknown", "weight": 3, "basis": "Unknown slot"}],
    [{"slot": "Chest", "weight": True, "basis": "Boolean"}],
    [{"slot": "Chest", "weight": 4, "basis": "Overweight"}],
    [{"slot": "Chest", "weight": -1, "basis": "Negative"}],
    [{"slot": "Chest", "weight": 3, "basis": " "}],
    [SLOT_PREFERENCES[0], SLOT_PREFERENCES[0]],
    [{"slot": "Chest", "weight": 1, "basis": "No class/story weighting"}],
    [{"slot": slot, "weight": 0, "basis": "Excluded"} for slot in EQUIPMENT_SLOTS],
])
def test_invalid_slot_plans_are_rejected_before_a_batch_draw(preferences):
    from app.game_random import GameRandom
    with pytest.raises(ValueError):
        GameRandom.validate([{"label": "Other roll", "kind": "dice", "sides": 20},
                             {"label": "Outfit", "kind": "outfitting", "class_rarity": "UNIQUE",
                              "slot_preferences": preferences}])


def test_only_four_compatible_slots_still_complete_without_a_one_sided_die():
    preferences = [{"slot": slot, "weight": 3 if index == 0 else int(index < 4),
                    "basis": "Fixture form's actual compatible slots"}
                   for index, slot in enumerate(EQUIPMENT_SLOTS)]
    from app.rules import Dice
    plan = starting_outfit("COMMON", Dice(lambda _: 0), preferences)
    assert {row["slot"] for row in plan["items"]} == set(EQUIPMENT_SLOTS[:4])


def test_legacy_outfit_receipt_replays_without_a_new_slot_plan(engine):
    from app.chat_game import ChatGame
    from app.game_random import GameRandom
    from app.rules import Dice
    from app.storage import canonical
    from app import records
    state = ChatGame(engine).create("owner-a", "Disposable legacy receipt", "legacy-outfit-fixture", True)
    action = "starting-outfit-" + state["id"]
    rows = [{"label": "Outfit", "kind": "outfitting", "class_rarity": "COMMON"}]
    legacy = {"action_id": action, "results": [{**rows[0], "result": {
        "items": [{"role": "Class focus or weapon", "rarity": "COMMON", "roll": 53}]}}]}
    with engine.store.transaction() as db:
        records.insert(db, "game_rolls_v1", {"owner": "owner-a", "action_id": action,
            "campaign_id": state["id"], "request": canonical({"campaign_id": state["id"], "rolls": rows}),
            "result": canonical(legacy)})
    box = GameRandom(engine.store, Dice(lambda _: pytest.fail("Redrew a legacy receipt")), engine)
    assert box.roll("owner-a", action, rows, state["id"]) == GameRandom.public(legacy)
