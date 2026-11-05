import copy

import pytest

from app.campaign_archive import CampaignArchive
from app.chat_game import ChatGame
from app.engine import EngineError
from app.game_profiles import SOVEREIGN, SOVEREIGN_LAWS, rule_source
from app.game_random import GameRandom
from app.rules import Dice
from .test_server import tool


def build(mode="bound", paired=False):
    changes = {
        "character": {"name": "The Still Guest", "class_name": "Keeper of reflections", "rarity": "RARE",
                      "story_summary": "A guest woke in the village's empty mirrors."},
        "creation": {
            # Retain the previously published single-identity fixture for compatibility checks.
            "selection_policy": {"class_offers": 12, "other_offers": 6, "picks": 1},
            "sovereign_body": {"mode": mode, "form": "A reflected silhouette",
                "description": "A visible figure in linked reflective surfaces.",
                "reach": "Acts through reflections that bear its handprint.",
                "perception": "Sees out through the glass that holds it.",
                "vulnerability": "Breaking its occupied mirror tears its silhouette.",
                "core_location": "The silver window above the inn"},
            "origin": {"id": "arrival", "name": "An unclaimed invitation", "rarity": "UNCOMMON",
                "history": "Woke when an invitation was held up to the empty window.",
                "effect": "Can leave its reflection on a written invitation.", "upgrades": []},
            "title": {"id": "opener", "name": "The Door Opener", "rarity": "RARE",
                "deed": "Opened the flood-bound inn's mirrored door for its guests.",
                "recognition": "The inn's rescued guests know the name.",
                "effect": "Can open a door by touching its reflected handle.", "upgrades": []}},
        "upsert": {"abilities": [
            {"id": key, "name": name, "rarity": "RARE", "mechanics_display": effect,
             "simple": effect, "flavor_text": "A guest answers from the glass.", "upgrades": []}
            for key, name, effect in (
                ("step", "Borrow a doorway", "Move between reflections that bear your handprint."),
                ("carry", "The other side", "Carry a real object inside its reflection."),
                ("listen", "Last guest", "Hear the last spoken words a mirror reflected."),
                ("turn", "A second face", "Turn an object's reflected face toward someone watching."))]},
        "sovereignty": {"domain": {"name": "The mirrored inn", "description": "An inn linked by marked glass.",
            "capabilities": [{"id": "door", "name": "The shared doorway", "effect": "Guests can cross the marked threshold."}]},
            "formations": [{"id": "moths", "name": "Glass moths", "description": "A drifting cloud of mirrored wings.",
                            "abilities": [{"id": "signal", "name": "Borrowed light", "effect": "Signal by turning reflected light."}],
                            "condition": "Whole", "orders": "Watch the creek"}]},
        "opening_preview": "A guest runs toward the creek as its bridge gives way.",
        "current_location": "The inn window",
    }
    if paired:
        creation = changes["creation"]
        creation["selection_policy"]["picks"] = 2
        creation["origins"] = [creation.pop("origin"), {"id": "silver", "name": "Silver remembers", "rarity": "RARE",
            "history": "The invitation woke a guest in glass silvered from a lost kiln.",
            "effect": "Can retain a reflected flame to warm someone later.", "upgrades": []}]
        creation["titles"] = [creation.pop("title"), {"id": "shelter", "name": "Keeper of the Last Light", "rarity": "UNCOMMON",
            "deed": "Kept a reflected lamp lit while the inn flooded.", "recognition": "The rescued guests remember the light.",
            "effect": "Can shelter a small flame inside an unbroken reflection.", "upgrades": []}]
    return changes


def active(engine, mode="bound"):
    game = ChatGame(engine)
    draft = game.create("owner-a", "Laws fixture", "laws-create", True, SOVEREIGN)
    state = game.update("owner-a", draft["id"], "laws-opening", draft["version"], "Accept the creature", build(mode), True)["campaign"]
    return game, state


@pytest.mark.parametrize("mode", ["bound", "mobile", "distributed"])
def test_creature_with_origin_title_and_unusual_force_starts_without_old_stat_block(engine, mode):
    game, state = active(engine, mode)
    assert state["rules_profile"] == SOVEREIGN_LAWS
    assert state["phase"] == "adventure" and not state["paused"]
    assert state["creation"]["origin"]["effect"] and state["creation"]["title"]["effect"]
    assert len(state["abilities"]) == 4 and state["rules_check"]["ready"]
    assert not {"hp", "mp", "def", "level"}.intersection(state["character"])
    assert not {"level", "limits", "next_milestone"}.intersection(state["sovereignty"]["domain"])
    assert not any(state["equipment"].values())
    assert game.create("owner-a", "Laws fixture", "laws-create", True, SOVEREIGN)["version"] == 1


@pytest.mark.parametrize("edge,draws,expected,outcome", [
    ("even", [0], 1, "threat"), ("even", [2], 3, "cost"), ("even", [5], 6, "clean"),
    ("player", [0, 5], 6, "clean"), ("opposition", [0, 5], 1, "threat")])
def test_real_maneuver_receipt_keeps_one_die_and_retry_never_rerolls(engine, edge, draws, expected, outcome):
    _, state = active(engine)
    values, consumed = iter(draws), []
    def draw(sides):
        consumed.append(sides)
        return next(values)
    random = GameRandom(engine.store, Dice(draw), engine)
    request = [{"kind": "maneuver", "label": "Catch the guest through the bridge reflection", "edge": edge}]
    result = random.roll("owner-a", "laws-maneuver", request, state["id"])
    kept = result["results"][0]["result"]
    assert kept["kept"] == expected and kept["outcome"] == outcome
    assert random.roll("owner-a", "laws-maneuver", request, state["id"]) == result
    assert consumed == [6] * len(draws)
    assert engine.get_campaign("owner-a", state["id"])["version"] == state["version"]
    with pytest.raises(EngineError, match="different roll arguments"):
        random.roll("owner-a", "laws-maneuver", [{**request[0], "edge": "opposition" if edge != "opposition" else "even"}], state["id"])


@pytest.mark.parametrize("scope", ["origin", "title"])
def test_identity_quest_awards_development_once_and_restores_with_its_history(engine, scope):
    game, state = active(engine)
    quest = {"id": "invitation", "quest_schema": 1, "name": "Find the invitation's sender",
        "finish_condition": "Read the sender's true signature.",
        "objectives": [{"id": "read", "text": "Read the original signature", "status": "pending"}],
        "system_reward": {"development": {"scope": scope, "summary": "Carry an invited guest through a reflected door."}}}
    state = game.update("owner-a", state["id"], "laws-quest-open", state["version"], "Take up the trail",
                        {"upsert": {"quest_log": [quest]}})["campaign"]
    origin = copy.deepcopy(state["creation"][scope])
    origin["effect"] += " Can bring an invited guest through a reflected doorway."
    origin["upgrades"] = [{"id": "guest", "name": "An invitation for two", "rarity": "RARE",
                           "effect": "Bring an invited guest through a reflected doorway.", "source": "quest:invitation"}]
    with pytest.raises(EngineError, match="completed quest"):
        game.update("owner-a", state["id"], "laws-too-early", state["version"], "Attempt early reward",
                    {"creation": {scope: origin}})
    quest["objectives"][0]["status"] = "done"
    changes = {"upsert": {"quest_log": [quest]}, "creation": {scope: origin}, "fictional_time_seconds": 50}
    result = game.update("owner-a", state["id"], "laws-quest-close", state["version"], "The signature is found", changes)
    assert game.update("owner-a", state["id"], "laws-quest-close", state["version"], "The signature is found", changes) == result
    saved = result["campaign"]
    assert saved["quest_log"][0]["status"] == "completed"
    assert saved["creation"][scope] == origin
    duplicate = copy.deepcopy(origin)
    duplicate["upgrades"] = [{**origin["upgrades"][0], "id": "twice"}]
    duplicate["upgrades"].insert(0, origin["upgrades"][0])
    with pytest.raises(EngineError, match="once"):
        game.update("owner-a", saved["id"], "laws-duplicate", saved["version"], "Try duplicate reward", {"creation": {scope: duplicate}})
    archive = CampaignArchive(engine)
    restored = archive.restore("owner-a", archive.export("owner-a", saved["id"])["archive"], "laws-restore", True)["campaign"]
    assert restored["creation"][scope] == origin and restored["sovereignty"] == saved["sovereignty"]
    assert restored["paused"] and restored["id"] != saved["id"]
    assert engine.get_campaign("owner-a", saved["id"])["version"] == saved["version"]


def test_authenticated_rules_and_start_follow_new_profile_and_other_modes_remain_scoped(web):
    draft = tool(web, "create_chat_game", {"name": "Laws transport", "action_id": "laws-tool-create", "game_id": SOVEREIGN})["structuredContent"]["campaign"]
    checklist = tool(web, "read_rules", {"campaign_id": draft["id"], "document": "hardener"})["structuredContent"]
    assert checklist["index_request"]["campaign_id"] == draft["id"]
    book = tool(web, "read_rules", checklist["index_request"])["structuredContent"]
    assert "identity | Origin and Title" in book["content"]
    assert "maneuvers | One real roll" in book["content"]
    started = tool(web, "save_chat_update", {"campaign_id": draft["id"], "action_id": "laws-tool-start",
        "expected_version": 1, "summary": "Accept the creature", "changes": {**build(paired=True), "begin_adventure": True}})
    assert not started.get("isError"), started
    assert started["structuredContent"]["campaign"]["phase"] == "adventure"
    assert len(started["structuredContent"]["campaign"]["creation"]["origins"]) == 2
    assert len(started["structuredContent"]["campaign"]["creation"]["titles"]) == 2
    from app.sovereign_play import PROFILE
    old = tool(web, "create_chat_game", {"name": "Archived profile", "action_id": "laws-old-profile", "game_id": SOVEREIGN,
                                         "sovereign_ruleset": PROFILE})["structuredContent"]["campaign"]
    old_book = tool(web, "read_rules", {"campaign_id": old["id"], "document": "index"})["structuredContent"]
    assert "sovereign-creation" in old_book["content"] and old_book["source_sha256"] != book["source_sha256"]
    # An uncertain pre-release creation can be retried after the default profile changes.
    # Preserve its original request shape and return guidance for the recovered save.
    import json
    from app import records
    from app.storage import canonical
    with web.app.state.engine.store.transaction() as db:
        receipt = records.get(db, "creations_v1", {"action_id": "laws-old-profile"})
        request = json.loads(receipt["request"])
        request.pop("sovereign_ruleset")
        records.update(db, "creations_v1", {"owner": receipt["owner"], "action_id": "laws-old-profile"},
                       {"request": canonical(request)})
    replay = tool(web, "create_chat_game", {"name": "Archived profile", "action_id": "laws-old-profile", "game_id": SOVEREIGN})["structuredContent"]
    assert replay["campaign"]["id"] == old["id"] and replay["standard_play"]["resources"] == ["HP", "MP"]
    assert rule_source("age-of-convergence")["source_sha256"] == "94ec7b0882418a00fc6140c09fa725984be02aaa3d70f9cf7664fcb55399a529"


def test_incomplete_identity_and_paused_maneuver_leave_saved_state_intact(engine):
    game = ChatGame(engine)
    draft = game.create("owner-a", "Draft", "laws-incomplete", True, SOVEREIGN)
    changes = build()
    changes["creation"].pop("origin")
    with pytest.raises(EngineError, match="Origin"):
        game.update("owner-a", draft["id"], "laws-incomplete-start", 1, "Incomplete build", changes, True)
    assert engine.get_campaign("owner-a", draft["id"])["version"] == 1
    random = GameRandom(engine.store, Dice(lambda _: pytest.fail("Rolled during creation")), engine)
    with pytest.raises(EngineError, match="active adventure"):
        random.roll("owner-a", "laws-blocked-roll", [{"kind": "maneuver", "label": "Unstarted", "edge": "even"}], draft["id"])


def test_maneuver_and_independent_surprise_share_one_receipt_and_saved_outcome(engine):
    from .test_world_events import pool
    game, state = active(engine)
    draws = iter([4, 99])  # Clean d6 maneuver; contextual d100 surprise does not trigger.
    random = GameRandom(engine.store, Dice(lambda _: next(draws)), engine)
    action = "event-" + state["id"] + "-creek"
    request = [{"kind": "maneuver", "label": "Bring the guest across", "edge": "even"},
               {"kind": "world_event", "label": "The creek route", "context": "frontier",
                "transition_id": "creek", "pool": pool()}]
    rolled = random.roll("owner-a", action, request, state["id"])
    assert rolled["results"][0]["result"]["outcome"] == "clean"
    changes = {"fictional_time_seconds": 60, "current_location": "The far-bank window",
        "event_transition": {"id": "creek", "context": "frontier", "eligible": True, "roll_action_id": action},
        "continuity": {"last_action": "Brought the guest across through the bridge reflection.",
                       "outcome": "The guest reaches the far bank.", "pending_decision": "Follow the guest or return?"}}
    result = game.update("owner-a", state["id"], "laws-crossing", state["version"], "The guest reaches safety", changes)
    assert result["campaign"]["version"] == state["version"] + 1
    assert result["campaign"]["event_tracking"]["last_check"]["outcome"] == "no_event"
    assert game.update("owner-a", state["id"], "laws-crossing", state["version"], "The guest reaches safety", changes) == result
    assert random.roll("owner-a", action, request, state["id"]) == rolled


def test_twelve_independent_class_rolls_and_complete_board_contract(engine):
    game = ChatGame(engine)
    draft = game.create("owner-a", "Twelve classes", "twelve-create", True, SOVEREIGN)
    assert draft["creation"]["selection_policy"] == {"class_offers": 12, "other_offers": 6, "picks": 2}
    draws, used = iter([0, 2000, 5000, 7500, 9000, 9700] * 2), []
    def draw(sides):
        used.append(sides)
        return next(draws)
    random = GameRandom(engine.store, Dice(draw), engine)
    requests = [{"label": "Class concept " + str(n), "kind": "rarity", "luck": 5} for n in range(12)]
    receipt = random.roll("owner-a", "twelve-class-rarities", requests, draft["id"])
    assert used == [10000] * 12
    assert [row["result"]["final_rarity"] for row in receipt["results"]] == ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY", "UNIQUE"] * 2
    assert random.roll("owner-a", "twelve-class-rarities", requests, draft["id"]) == receipt
    board = {"id": "class-board", "kind": "class", "offers": [
        {"id": "class-" + str(n), "name": "Creature concept " + str(n), "rarity": row["result"]["final_rarity"]}
        for n, row in enumerate(receipt["results"])], "selected_ids": [], "complete": False}
    with pytest.raises(EngineError, match="complete board"):
        game.update("owner-a", draft["id"], "three-classes", 1, "Attempt a reduced board",
                    {"creation": {"selection_boards": [{**board, "offers": board["offers"][:3]}]}})
    saved = game.update("owner-a", draft["id"], "twelve-classes", 1, "Offer twelve classes",
                        {"creation": {"selection_boards": [board]}})["campaign"]
    assert len(saved["creation"]["selection_boards"][0]["offers"]) == 12
    assert saved["fictional_time_seconds"] == 0 and len(used) == 12


def test_two_identity_picks_and_six_option_upgrade_boards_start_without_losing_four_laws(engine):
    game = ChatGame(engine)
    draft = game.create("owner-a", "Paired identity", "pairs-create", True, SOVEREIGN)
    changes = build(paired=True)
    board = {"id": "opening-refinements", "kind": "personal", "offers": [
        {"id": "refinement-" + str(n), "name": "New application " + str(n), "rarity": "RARE"} for n in range(6)],
        "selected_ids": ["refinement-0"], "complete": True}
    changes["creation"]["selection_boards"] = [board]
    with pytest.raises(EngineError, match="selected picks"):
        game.update("owner-a", draft["id"], "pairs-one-pick", 1, "Attempt one of two picks", changes, True)
    board["selected_ids"].append("refinement-1")
    law = changes["upsert"]["abilities"][0]
    law["mechanics_display"] += " Carry an invited guest and leave a return reflection."
    law["upgrades"] = [{"id": "refinement-" + str(n), "name": "New application " + str(n), "rarity": "RARE",
                        "effect": effect, "source": "Creation"} for n, effect in enumerate(
                            ("Carry an invited guest.", "Leave a return reflection."))]
    result = game.update("owner-a", draft["id"], "pairs-start", 1, "Choose both identity traits and Titles", changes, True)
    assert game.update("owner-a", draft["id"], "pairs-start", 1, "Choose both identity traits and Titles", changes, True) == result
    state = result["campaign"]
    assert state["phase"] == "adventure" and state["rules_check"]["ready"]
    assert len(state["abilities"]) == 4
    assert len(state["abilities"][0]["upgrades"]) == 2
    assert len(state["creation"]["origins"]) == len(state["creation"]["titles"]) == 2
    assert all(owner["effect"] for scope in ("origins", "titles") for owner in state["creation"][scope])
    archive = CampaignArchive(engine)
    restored = archive.restore("owner-a", archive.export("owner-a", state["id"])["archive"], "pairs-restore", True)["campaign"]
    assert restored["creation"] == state["creation"]


def test_future_offer_preferences_preserve_issued_boards_and_paused_creature(engine):
    game = ChatGame(engine)
    draft = game.create("owner-a", "Offer preferences", "offer-prefs-create", True, SOVEREIGN)
    changes = build(paired=True)
    changes["creation"]["selection_boards"] = [{"id": "old-board", "kind": "personal", "offers": [
        {"id": "old-" + str(n), "name": "Old application " + str(n), "rarity": "RARE"} for n in range(6)],
        "selected_ids": ["old-0", "old-1"], "complete": True}]
    state = game.update("owner-a", draft["id"], "offer-prefs-start", 1, "Choose the creature", changes, True)["campaign"]
    from .conftest import commit
    state = commit(engine, state, "pause")["campaign"]
    saved = game.update("owner-a", state["id"], "offer-prefs-change", state["version"], "Change future offer counts",
        {"creation": {"selection_policy": {"class_offers": 12, "other_offers": 8, "picks": 3}}})["campaign"]
    assert saved["paused"] and saved["fictional_time_seconds"] == state["fictional_time_seconds"]
    assert saved["character"] == state["character"] and saved["abilities"] == state["abilities"]
    assert saved["creation"]["selection_boards"] == state["creation"]["selection_boards"]
    assert saved["rules_check"]["ready"]


def test_advertised_two_pick_identity_reward_applies_both_once_and_preserves_parent_rarity(engine):
    game = ChatGame(engine)
    draft = game.create("owner-a", "Two rewards", "two-rewards-create", True, SOVEREIGN)
    state = game.update("owner-a", draft["id"], "two-rewards-start", 1, "Begin the creature", build(paired=True), True)["campaign"]
    quest = {"id": "lost-glass", "name": "Recover the lost glass", "quest_schema": 1,
             "finish_condition": "The original glass is recovered.",
             "objectives": [{"id": "recover", "text": "Recover the original glass", "status": "pending"}],
             "system_reward": {"development": {"scope": "origin", "summary": "Awaken two new uses of your origin traits.", "picks": 2}}}
    state = game.update("owner-a", state["id"], "two-rewards-offer", state["version"], "Take the quest", {"upsert": {"quest_log": [quest]}})["campaign"]
    origins = copy.deepcopy(state["creation"]["origins"])
    for n, origin in enumerate(origins):
        origin["effect"] += " The recovered glass enables a new use."
        origin["upgrades"] = [{"id": "awakening-" + str(n), "name": "New glass application " + str(n),
            "effect": "Carry a reflected guest." if n == 0 else "Keep a reflected warmth through rain.",
            "rarity": "EPIC", "source": "quest:lost-glass"}]
    quest["objectives"][0]["status"] = "done"
    changes = {"creation": {"origins": origins}, "upsert": {"quest_log": [quest]}}
    result = game.update("owner-a", state["id"], "two-rewards-close", state["version"], "The glass returns", changes)
    assert game.update("owner-a", state["id"], "two-rewards-close", state["version"], "The glass returns", changes) == result
    saved = result["campaign"]
    assert [row["rarity"] for row in saved["creation"]["origins"]] == [row["rarity"] for row in state["creation"]["origins"]]
    assert all(len(row["upgrades"]) == 1 for row in saved["creation"]["origins"])
    assert saved["character"]["rarity"] == state["character"]["rarity"]
    third = copy.deepcopy(origins)
    third[0]["upgrades"].append({**third[0]["upgrades"][0], "id": "third-award"})
    with pytest.raises(EngineError, match="promised development picks once"):
        game.update("owner-a", saved["id"], "two-rewards-third", saved["version"], "Attempt an extra reward", {"creation": {"origins": third}})
