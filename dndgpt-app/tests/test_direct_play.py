"""Exercise the actual authenticated tools, lifecycle, and immutable equipment draw."""
import copy
from itertools import product

import pytest

from app.outfitting import BUDGETS, SUPPORT, TIERS, starting_outfit
from .test_server import tool


def prepare(web):
    state = tool(web, "create_chat_game", {"name": "Disposable direct-play fixture",
                 "action_id": "direct-create", "disposable": True})["structuredContent"]["campaign"]
    state = tool(web, "save_chat_update", {"campaign_id": state["id"], "action_id": "class-selected",
                 "expected_version": state["version"], "summary": "Actual class choice",
                 "changes": {"character": {"class_name": "Door Warden"}}})["structuredContent"]["campaign"]
    draw = {"campaign_id": state["id"], "action_id": "starting-outfit-" + state["id"],
            "rolls": [{"label": "Starting equipment", "kind": "outfitting", "class_rarity": "COMMON"}]}
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
               "equipment": dict(zip(("Main Hand", "Chest", "Feet", "Neck"), [r["id"] for r in items])),
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
    reopened = tool(web, "render_dashboard", {"campaign_id": state["id"]})
    assert not reopened["_meta"].get("approval")
    assert tool(web, "save_chat_update", args)["structuredContent"] == result["structuredContent"]
    assert tool(web, "roll_game_random", draw)["structuredContent"] == receipt["structuredContent"]
    assert tool(web, "get_campaign", {"campaign_id": state["id"]})["structuredContent"]["campaign"] == state


@pytest.mark.parametrize("missing", ["story", "equipment", "background", "opening"])
def test_incomplete_creation_is_atomic_without_requesting_player_approval(web, missing):
    draft, _, _, args = prepare(web)
    if missing == "story":
        args["changes"]["character"].pop("story_summary")
    elif missing == "equipment":
        args["changes"]["equipment"] = {}
    elif missing == "background":
        args["changes"]["character"].pop("background")
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
        assert result.get("isError") and result["structuredContent"]["error"] == "creation_approval_retired"
    changed = copy.deepcopy(draw)
    changed["action_id"] = "another-outfit"
    assert tool(web, "roll_game_random", changed).get("isError")
    assert tool(web, "roll_game_random", {**draw, "rolls": [*draw["rolls"],
        {**draw["rolls"][0], "label": "Second outfit"}]}).get("isError")


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
            assert sides == 100
            return next(self.values)

    for rarity, values in product(TIERS, product((1, 20, 21, 75, 76, 100), repeat=4)):
        plan = starting_outfit(rarity, Draws(values))
        assert plan["budget"] == BUDGETS[rarity]
        assert sum(item["cost"] for item in plan["items"]) + 6 + plan["unspent"] == plan["budget"]
        assert plan["unspent"] >= 0 and len(plan["items"]) == 4
        assert all(TIERS.index(row["rarity"]) >= TIERS.index(SUPPORT[rarity]) for row in plan["items"][1:])
        if rarity == "UNIQUE":
            assert plan["items"][0]["rarity"] in {"LEGENDARY", "UNIQUE"}
