"""D&D integration acceptance using disposable sheets, packs and real MCP transport."""
import copy
import json

import pytest

from app.chat_game import ChatGame
from app.dnd5e import GAME, DndGame, normalize_sheet
from app.dnd_reference import catalog, lookup
from app.engine import EngineError
from app.library import Library
from app.adventure_library import read_section
from .test_server import tool


def sheet(name="Mira", kind="Fighter", level=1):
    return {"id": "test-"+name.lower().replace(" ", "-"), "name": name, "species": "Elf",
            "background": "Sage" if kind == "Wizard" else "Soldier", "classes": [{"name": kind, "level": level}],
            "attributes": {"STR": 16, "DEX": 14, "CON": 14, "INT": 16 if kind == "Wizard" else 10, "WIS": 13, "CHA": 13},
            "story_summary": "A returning expedition scout searching the old road for a missing friend.",
            "species_description": "An elf with ash-brown skin and silver-flecked eyes.",
            "skill_proficiencies": ["Athletics", "Perception", "Survival", "Intimidation"],
            "inventory": [{"id": "test-staff", "name": "Quarterstaff", "quantity": 1, "equipped": True, "description": "A sturdy wooden staff."}],
            "armor_class": 14, "currency": {"gp": 15},
            "attacks": [{"name": "Quarterstaff", "ability": "STR", "proficient": True, "damage": "1d6 + 3", "damage_type": "Bludgeoning", "range": "5 ft"}],
            "spells": [{"key": "srd-2024_fire-bolt", "prepared": True}, {"key": "srd-2024_magic-missile", "prepared": True}] if kind == "Wizard" else []}


def adventure(title="The Broken Waystone"):
    return {"title": title, "setting": "Forgotten Realms", "region": "Sword Coast", "adventure_type": "original",
            "summary": "A missing scout's trail leads to an abandoned roadside shrine.", "starting_level": 1, "ending_level": 5,
            "references": [{"url": "https://www.dndbeyond.com/resources/2037-the-forgotten-realms", "title": "Official setting introduction"}],
            "sections": [{"id": "arrival", "title": "The old road", "player_summary": "A broken shrine beside the road.",
                          "content": "PRIVATE_TEST_SECRET: a watcher waits behind the shrine. An original disposable test plot.", "links": ["shrine"]},
                         {"id": "shrine", "title": "The shrine", "content": "Rescue the missing scout. The road opens once the threat is cleared.", "links": []}]}


def prepared(engine):
    game = ChatGame(engine)
    state = game.create("owner-a", "D&D test", "create-dnd-fixture", True, GAME)
    pack = Library(engine).save("owner-a", "save-dnd-pack", "adventure", adventure())["entry"]
    changes = {"party": [sheet(), {**sheet("Iria", "Wizard"), "controller": "gm", "role": "companion"}],
               "hero_id": "test-mira", "party_mode": "party", "adventure": {"id": pack["id"], "version": pack["version"], "current_section": "arrival"},
               "opening_preview": "Mira and Iria arrive at the old road.", "current_location": "The old road"}
    return game, state, pack, changes


def test_complete_party_draft_start_and_one_batched_turn(engine):
    game, state, pack, changes = prepared(engine)
    draft = game.update("owner-a", state["id"], "draft-party-one", 1, "Prepared party", changes)["campaign"]
    assert draft["phase"] == "character_draft" and draft["paused"]
    assert set(draft["character"]["attributes"]) == {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
    assert "mp" not in draft["character"]
    started = game.update("owner-a", state["id"], "start-party-one", 2, "Let's go", {}, True)["campaign"]
    assert started["phase"] == "adventure" and not started["paused"]
    patch = {"party_upsert": [{"id": "test-mira", "hp": 8}, {"id": "test-iria", "spellcasting": {"slots": [{"level": 1, "used": 1}]}}],
             "fictional_time_seconds": 6, "continuity": {"last_action": "Crossed the broken bridge", "outcome": "The party reaches the shrine"},
             "adventure": {"current_section": "shrine", "visited": ["arrival", "shrine"]}}
    turn = game.update("owner-a", state["id"], "party-turn-one", 3, "Crossed the bridge", patch)
    retry = game.update("owner-a", state["id"], "party-turn-one", 3, "Crossed the bridge", patch)
    assert turn == retry
    result = turn["campaign"]
    assert result["version"] == 4 and result["party"][0]["hp"] == 8
    assert result["party"][1]["spellcasting"]["slots"][0] == {"level": 1, "maximum": 2, "used": 1}
    assert engine.audit("owner-a", state["id"])["integrity_valid"]
    assert "PRIVATE_TEST_SECRET" not in json.dumps(result)
    assert "PRIVATE_TEST_SECRET" in read_section(Library(engine), "owner-a", pack["id"], "arrival")["section"]["content"]


def test_library_is_owned_versioned_idempotent_and_campaign_copies_do_not_sync(engine):
    library = Library(engine)
    original = sheet(); original.pop("id")
    first = library.save("owner-a", "save-library-one", "character", original)
    assert library.save("owner-a", "save-library-one", "character", original) == first
    entry = first["entry"]
    game = ChatGame(engine)
    copies = []
    for n in range(2):
        state = game.create("owner-a", "Run "+str(n), "new-library-run-"+str(n), True, GAME)
        copy_sheet = copy.deepcopy(entry["content"]);copy_sheet["id"] = "copy-character-"+str(n)
        copies.append(game.update("owner-a", state["id"], "copy-library-run-"+str(n), 1, "Copied character", {"party": [copy_sheet]})["campaign"])
    game.update("owner-a", copies[0]["id"], "damage-copy-one", 2, "Revise this run", {"party_upsert": [{"id": "copy-character-0", "hp": 1}]})
    revised = {**entry["content"], "name": "Mira revised"}
    library.save("owner-a", "revise-library-one", "character", revised, entry["id"], 1)
    assert library.get("owner-a", entry["id"], 1)["content"]["name"] == "Mira"
    assert engine.get_campaign("owner-a", copies[1]["id"])["party"][0]["hp"] == entry["content"]["hp"]
    assert library.list("owner-b") == []
    with pytest.raises(EngineError) as exc:
        library.get("owner-b", entry["id"])
    assert exc.value.status == 404


@pytest.mark.parametrize("kind", list(__import__("app.dnd5e", fromlist=["HIT_DICE"]).HIT_DICE))
def test_every_installed_class_has_valid_level_one_sheet(kind):
    value = normalize_sheet(sheet(kind=kind))
    assert value["level"] == 1 and value["features"]
    assert value["proficiency_bonus"] == 2 and value["ability_modifiers"]["STR"] == 3
    assert value["saving_throws"]["STR"] == 3 + (2 if "STR" in value["saving_throw_proficiencies"] else 0)


def test_slot_progression_pact_slots_and_multiclass_are_separate():
    wizard = normalize_sheet(sheet(kind="Wizard", level=20))
    assert [s["maximum"] for s in wizard["spellcasting"]["slots"]] == [4, 3, 3, 3, 3, 2, 2, 1, 1]
    warlock = normalize_sheet(sheet(kind="Warlock", level=5))
    assert warlock["spellcasting"]["slots"] == []
    assert warlock["spellcasting"]["pact_slots"] == {"level": 3, "maximum": 2, "used": 0}
    mixed = sheet(kind="Wizard", level=3); mixed["classes"].append({"name": "Paladin", "level": 3})
    result = normalize_sheet(mixed)
    assert result["level"] == 6 and [s["maximum"] for s in result["spellcasting"]["slots"]] == [4, 3, 2]
    assert result["hit_dice"] == {"d6": {"maximum": 3, "used": 0}, "d10": {"maximum": 3, "used": 0}}


@pytest.mark.parametrize("patch", [
    {"party_upsert": [{"id": "test-mira", "hp": 999}]},
    {"party_upsert": [{"id": "test-iria", "spellcasting": {"slots": [{"level": 1, "used": 9}]}}]},
    {"party_upsert": [{"id": "test-mira", "attributes": {"LCK": 20}}]},
    {"game_id": "sovereign-system"}, {"fictional_time_seconds": -1},
    {"party_mode": "solo"}, {"upsert": {"abilities": []}},
    {"adventure": {"id": "somebody-elses-pack"}}])
def test_invalid_batch_is_atomic(engine, patch):
    game, state, pack, changes = prepared(engine)
    current = game.update("owner-a", state["id"], "prepare-invalid-fixture", 1, "Prepare", changes)["campaign"]
    with pytest.raises(EngineError):
        game.update("owner-a", state["id"], "invalid-batch-one", 2, "Invalid fixture", patch)
    assert engine.get_campaign("owner-a", state["id"]) == current


def test_rules_search_exact_name_source_scope_and_pagination():
    result = lookup("spells", "fireball", detail=True)
    assert result["name"] == "Fireball" and result["source"]["document"] == "srd-2024"
    assert lookup("spells", "NONEXISTENT SPELL") ["count"] == 0
    with pytest.raises(EngineError):
        lookup("spells", filters={"environment": "forest"})
    result = lookup("rules", "Concentration")
    assert result["results"]
    assert lookup("rules", key=str(result["results"][0]["page"]), detail=True)["source"] == "Official SRD 5.2.1"
    for kind, rows in catalog().items():
        if isinstance(rows, list):
            assert all(r["document"]["key"] == "srd-2024" for r in rows)


def test_mcp_selected_rules_library_scope_and_character_copy_retry(web, tokens):
    new = tool(web, "create_chat_game", {"name": "Quickplay test", "action_id": "mcp-dnd-selected", "disposable": True, "game_id": GAME})
    assert not new.get("isError"), new
    state = new["structuredContent"]["campaign"]
    assert state["game_id"] == GAME
    rules = tool(web, "read_rules", {"document": "hardener", "campaign_id": state["id"]})["structuredContent"]
    assert rules["game_rules_version"] == "5.2.1" and "2024 execution checklist" in rules["content"]
    index = tool(web, "read_rules", {"document": "index", "campaign_id": state["id"]})
    assert not index.get("isError"), index
    assert "creation |" in index["structuredContent"]["content"]
    assert "World preview:" not in index["structuredContent"]["content"]
    saved = tool(web, "save_dnd_character", {"action_id": "transport-character-save", "sheet": sheet()})
    assert not saved.get("isError"), saved
    entry = saved["structuredContent"]["entry"]
    args = {"campaign_id": state["id"], "action_id": "transport-copy-sheet", "expected_version": 1,
            "entries": [{"id": entry["id"], "version": 1}], "party_mode": "solo"}
    copied = tool(web, "add_dnd_characters", args)
    assert not copied.get("isError"), copied
    assert tool(web, "add_dnd_characters", args)["structuredContent"] == copied["structuredContent"]
    denied = web.post("/mcp", headers={"Authorization": "Bearer "+tokens(subject="user-b"), "Accept": "application/json, text/event-stream"},
                      json={"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "read_dnd_character", "arguments": {"entry_id": entry["id"]}}}).json()["result"]
    assert denied["isError"]


def test_campaign_export_restore_has_party_but_no_gm_pack(engine):
    from app.campaign_archive import CampaignArchive
    game, state, pack, changes = prepared(engine)
    game.update("owner-a", state["id"], "export-dnd-party", 1, "Prepare", changes, True)
    service = CampaignArchive(engine)
    data = service.export("owner-a", state["id"])
    assert "PRIVATE_TEST_SECRET" not in json.dumps(data)
    archive = data["archive"]
    restored = service.restore("owner-a", archive, "restore-dnd-party", True)
    assert restored["campaign"]["party"] == archive["campaign"]["party"]
    assert restored["campaign"]["paused"] and restored["campaign"]["id"] != state["id"]
