"""2024 character sheets and atomic party saves, separate from homebrew mechanics.

The GM adjudicates the fiction. This module validates sheet structure and derives
standard arithmetic; it is not a complete tabletop rules adjudicator.
"""
import copy
import json
import math
import uuid
from contextlib import nullcontext

from . import records
from .engine import fail, identifier, public_state, safe_event
from .storage import canonical

GAME = "dnd-2024"
RULES = "5.2.1"
ATTRIBUTES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
SKILLS = {"Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT", "Athletics": "STR",
          "Deception": "CHA", "History": "INT", "Insight": "WIS", "Intimidation": "CHA",
          "Investigation": "INT", "Medicine": "WIS", "Nature": "INT", "Perception": "WIS",
          "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT", "Sleight of Hand": "DEX",
          "Stealth": "DEX", "Survival": "WIS"}
HIT_DICE = {"Barbarian": 12, "Bard": 8, "Cleric": 8, "Druid": 8, "Fighter": 10, "Monk": 8,
            "Paladin": 10, "Ranger": 10, "Rogue": 8, "Sorcerer": 6, "Warlock": 8, "Wizard": 6}
CASTERS = {"Bard": "CHA", "Cleric": "WIS", "Druid": "WIS", "Paladin": "CHA", "Ranger": "WIS",
           "Sorcerer": "CHA", "Warlock": "CHA", "Wizard": "INT"}
SAVES = {"Barbarian": ["STR", "CON"], "Bard": ["DEX", "CHA"], "Cleric": ["WIS", "CHA"],
         "Druid": ["INT", "WIS"], "Fighter": ["STR", "CON"], "Monk": ["STR", "DEX"],
         "Paladin": ["WIS", "CHA"], "Ranger": ["STR", "DEX"], "Rogue": ["DEX", "INT"],
         "Sorcerer": ["CON", "CHA"], "Warlock": ["WIS", "CHA"], "Wizard": ["INT", "WIS"]}
PREREQUISITES = {"Barbarian": ("STR",), "Bard": ("CHA",), "Cleric": ("WIS",), "Druid": ("WIS",),
                 "Fighter": ("STR|DEX",), "Monk": ("DEX", "WIS"), "Paladin": ("STR", "CHA"),
                 "Ranger": ("DEX", "WIS"), "Rogue": ("DEX",), "Sorcerer": ("CHA",),
                 "Warlock": ("CHA",), "Wizard": ("INT",)}
SLOT_TABLE = [[], [2], [3], [4, 2], [4, 3], [4, 3, 2], [4, 3, 3], [4, 3, 3, 1],
              [4, 3, 3, 2], [4, 3, 3, 3, 1], [4, 3, 3, 3, 2], [4, 3, 3, 3, 2, 1],
              [4, 3, 3, 3, 2, 1], [4, 3, 3, 3, 2, 1, 1], [4, 3, 3, 3, 2, 1, 1],
              [4, 3, 3, 3, 2, 1, 1, 1], [4, 3, 3, 3, 2, 1, 1, 1],
              [4, 3, 3, 3, 2, 1, 1, 1, 1], [4, 3, 3, 3, 3, 1, 1, 1, 1],
              [4, 3, 3, 3, 3, 2, 1, 1, 1], [4, 3, 3, 3, 3, 2, 2, 1, 1]]


def integer(value, label, low=0, high=1000000):
    if type(value) is not int or not low <= value <= high:
        fail(422, "invalid_dnd_sheet", f"{label} must be an integer from {low} to {high}")
    return value


def words(value, label, maximum=20000):
    if type(value) is not str or len(value) > maximum:
        fail(422, "invalid_dnd_sheet", f"{label} must be text of at most {maximum} characters")
    return value


def modifier(score):
    return (score - 10) // 2


def names(value, allowed, label):
    if type(value) is not list or any(type(x) is not str or x not in allowed for x in value) or len(set(value)) != len(value):
        fail(422, "invalid_dnd_sheet", f"Choose valid, distinct {label}")
    return value


def slots_for(classes):
    effective = sum(row["level"] if row["name"] in {"Bard", "Cleric", "Druid", "Sorcerer", "Wizard"}
                    else math.ceil(row["level"] / 2) if row["name"] in {"Paladin", "Ranger"} else 0 for row in classes)
    return SLOT_TABLE[min(20, effective)]


def normalize_sheet(value):
    from .chat_game import bounded_json
    from .dnd_reference import catalog, class_features, parent_key
    bounded_json(value)
    if type(value) is not dict:
        fail(422, "invalid_dnd_sheet", "Supply a complete character sheet object")
    allowed = {"id", "name", "species", "species_description", "species_choices", "background", "classes", "attributes",
               "base_attributes", "background_boosts", "ability_method", "hp", "hp_max", "temp_hp", "armor_class", "speed",
               "initiative_bonus", "size", "saving_throw_proficiencies", "skill_proficiencies", "expertise", "skill_bonuses",
               "save_bonuses", "features", "attacks", "spells", "spellcasting", "inventory", "currency", "languages",
               "armor_training", "weapon_proficiencies", "tool_proficiencies", "feats", "story_summary", "appearance",
               "alignment", "traits", "bonds", "ideals", "flaws", "inspiration", "exhaustion", "death_saves",
               "hit_dice_used", "conditions", "controller", "role", "xp", "advancement_history", "portrait_url",
               "source_library", "notes", "level", "class_name", "proficiency_bonus", "ability_modifiers",
               "saving_throws", "skills", "passive_perception", "hit_dice", "rules_version"}
    if value.keys() - allowed:
        fail(422, "invalid_dnd_sheet", "Unknown character sheet fields: " + ", ".join(sorted(value.keys() - allowed)))
    sheet = copy.deepcopy(value)
    for key in ("name", "species", "background"):
        if not words(sheet.get(key), key, 128).strip():
            fail(422, "incomplete_dnd_sheet", "Choose a name, species and background")
    for kind, key in (("species", "species"), ("backgrounds", "background")):
        if not any(row["name"].casefold() == sheet[key].casefold() for row in catalog()[kind]):
            fail(422, "unsupported_dnd_option", f"{sheet[key]} is outside the installed SRD {kind}; choose an available option")
    classes = sheet.get("classes")
    if type(classes) is not list or not 1 <= len(classes) <= 12:
        fail(422, "invalid_dnd_sheet", "Include at least one class and its level")
    seen = set()
    for row in classes:
        if type(row) is not dict or row.keys() - {"name", "level", "subclass"} or type(row.get("name")) is not str or row["name"] not in HIT_DICE or row["name"] in seen:
            fail(422, "invalid_dnd_sheet", "Use distinct SRD classes with name, level and optional subclass")
        seen.add(row["name"])
        integer(row.get("level"), "class level", 1, 20)
        if row.get("subclass"):
            base = next(x for x in catalog()["classes"] if x["name"] == row["name"] and not x.get("subclass_of"))
            available = [x["name"] for x in catalog()["classes"] if parent_key(x.get("subclass_of")) == base["key"]]
            if row["subclass"] not in available or row["level"] < 3:
                fail(422, "unsupported_dnd_option", "Choose an installed subclass when the class reaches level 3")
    level = integer(sum(row["level"] for row in classes), "total level", 1, 20)
    attrs = sheet.get("attributes")
    if type(attrs) is not dict or set(attrs) != set(ATTRIBUTES):
        fail(422, "invalid_dnd_sheet", "Use exactly STR, DEX, CON, INT, WIS and CHA")
    for key, score in attrs.items():
        integer(score, key, 1, 30)
    if len(classes) > 1:
        for row in classes:
            if any(max(attrs[key] for key in alternative.split("|")) < 13 for alternative in PREREQUISITES[row["name"]]):
                fail(422, "multiclass_prerequisite", "Meet the ability prerequisites of every class before multiclassing")
    if sheet.get("ability_method") == "standard-array":
        base, boosts = sheet.get("base_attributes"), sheet.get("background_boosts")
        eligible = {"Acolyte": {"INT", "WIS", "CHA"}, "Criminal": {"DEX", "CON", "INT"},
                    "Sage": {"CON", "INT", "WIS"}, "Soldier": {"STR", "DEX", "CON"}}[sheet["background"].title()]
        if (type(base) is not dict or set(base) != set(ATTRIBUTES) or any(type(v) is not int for v in base.values()) or sorted(base.values()) != [8, 10, 12, 13, 14, 15]
                or type(boosts) is not dict or not set(boosts) <= eligible
                or any(type(x) is not int or not 0 <= x <= 2 for x in boosts.values())
                or sum(boosts.values()) != 3 or level == 1 and any(attrs[k] != base[k] + boosts.get(k, 0) for k in ATTRIBUTES)):
            fail(422, "invalid_ability_assignment", "Use the standard array and three legal background ability increases")
    pb = 2 + (level - 1) // 4
    mods = {key: modifier(score) for key, score in attrs.items()}
    sheet.update(level=level, class_name=" / ".join(f'{r["name"]} {r["level"]}' for r in classes),
                 proficiency_bonus=pb, ability_modifiers=mods, rules_version=RULES)
    sheet.setdefault("id", "hero-" + uuid.uuid4().hex)
    identifier(sheet["id"], "character id")
    sheet.setdefault("saving_throw_proficiencies", SAVES[classes[0]["name"]])
    names(sheet["saving_throw_proficiencies"], ATTRIBUTES, "saving throw proficiencies")
    for key in ("skill_proficiencies", "expertise"):
        sheet.setdefault(key, [])
        names(sheet[key], SKILLS, key.replace("_", " "))
    if not set(sheet["expertise"]) <= set(sheet["skill_proficiencies"]):
        fail(422, "invalid_dnd_sheet", "Expertise applies to a proficient skill")
    for key, allowed_names in (("skill_bonuses", SKILLS), ("save_bonuses", ATTRIBUTES)):
        sheet.setdefault(key, {})
        if type(sheet[key]) is not dict or set(sheet[key]) - set(allowed_names):
            fail(422, "invalid_dnd_sheet", "Unknown skill or saving throw bonus")
        for bonus in sheet[key].values():
            integer(bonus, "bonus", -100, 100)
    sheet["saving_throws"] = {k: mods[k] + (pb if k in sheet["saving_throw_proficiencies"] else 0) + sheet["save_bonuses"].get(k, 0) for k in ATTRIBUTES}
    sheet["skills"] = {k: mods[a] + pb * (2 if k in sheet["expertise"] else 1 if k in sheet["skill_proficiencies"] else 0) + sheet["skill_bonuses"].get(k, 0) for k, a in SKILLS.items()}
    sheet["passive_perception"] = 10 + sheet["skills"]["Perception"]
    default_hp = HIT_DICE[classes[0]["name"]] + mods["CON"]
    default_hp += sum((r["level"] - (1 if i == 0 else 0)) * max(1, HIT_DICE[r["name"]] // 2 + 1 + mods["CON"]) for i, r in enumerate(classes))
    sheet.setdefault("hp_max", max(1, default_hp))
    integer(sheet["hp_max"], "maximum HP", 1)
    sheet.setdefault("hp", sheet["hp_max"])
    integer(sheet["hp"], "current HP", 0, sheet["hp_max"])
    for key, default, low, high in (("temp_hp", 0, 0, 1000000), ("armor_class", 10 + mods["DEX"], 0, 100),
                                    ("speed", 30, 0, 10000), ("initiative_bonus", mods["DEX"], -100, 100),
                                    ("xp", 0, 0, 1000000000), ("exhaustion", 0, 0, 6)):
        sheet.setdefault(key, default)
        integer(sheet[key], key, low, high)
    sheet.setdefault("inspiration", False)
    if type(sheet["inspiration"]) is not bool:
        fail(422, "invalid_dnd_sheet", "Heroic inspiration is true or false")
    sheet.setdefault("death_saves", {"successes": 0, "failures": 0})
    if type(sheet["death_saves"]) is not dict or set(sheet["death_saves"]) != {"successes", "failures"}:
        fail(422, "invalid_dnd_sheet", "Record death save successes and failures")
    for value in sheet["death_saves"].values():
        integer(value, "death saves", 0, 3)
    dice = {}
    for row in classes:
        die = "d" + str(HIT_DICE[row["name"]])
        dice[die] = dice.get(die, 0) + row["level"]
    used = sheet.setdefault("hit_dice_used", {})
    if type(used) is not dict or set(used) - set(dice):
        fail(422, "invalid_dnd_sheet", "Record spent Hit Dice by their die type")
    sheet["hit_dice"] = {die: {"maximum": count, "used": integer(used.get(die, 0), "spent Hit Dice", 0, count)} for die, count in dice.items()}
    for key in ("features", "attacks", "spells", "inventory", "feats", "advancement_history"):
        sheet.setdefault(key, [])
        if type(sheet[key]) is not list or any(type(row) is not dict for row in sheet[key]):
            fail(422, "invalid_dnd_sheet", f"{key} must be a list of records")
        for row in sheet[key]:
            if key in {"features", "inventory"}:
                identifier(row.get("id"), key + " id")
            if key != "spells" and (type(row.get("name")) is not str or not row["name"].strip()):
                fail(422, "invalid_dnd_sheet", f"Each {key} record needs a name")
            if key == "features" and "uses" in row:
                uses = row["uses"]
                if type(uses) is not dict or not {"maximum", "remaining"} <= uses.keys():
                    fail(422, "invalid_dnd_sheet", "Feature uses need maximum and remaining")
                maximum = integer(uses["maximum"], "maximum feature uses")
                integer(uses["remaining"], "remaining feature uses", 0, maximum)
        if key in {"features", "inventory"} and len({r["id"] for r in sheet[key]}) != len(sheet[key]):
            fail(422, "invalid_dnd_sheet", f"Use distinct {key} IDs")
    existing = {f.get("id"): f for f in sheet["features"]}
    for feature in class_features(classes):
        existing[feature["id"]] = {**feature, **existing.get(feature["id"], {})}
        existing[feature["id"]]["level_progression"] = feature["level_progression"]
    sheet["features"] = list(existing.values())
    for key in ("conditions", "languages", "armor_training", "weapon_proficiencies", "tool_proficiencies", "species_choices"):
        sheet.setdefault(key, [])
        if type(sheet[key]) is not list or any(type(x) is not str for x in sheet[key]):
            fail(422, "invalid_dnd_sheet", f"{key} must be a list of names")
    sheet.setdefault("currency", {})
    if type(sheet["currency"]) is not dict or sheet["currency"].keys() - {"cp", "sp", "ep", "gp", "pp"}:
        fail(422, "invalid_dnd_sheet", "Use the five D&D coin denominations")
    for amount in sheet["currency"].values():
        integer(amount, "currency")
    for key in ("story_summary", "appearance", "alignment", "traits", "bonds", "ideals", "flaws", "notes", "species_description"):
        sheet.setdefault(key, "")
        words(sheet[key], key)
    sheet.setdefault("controller", "player")
    sheet.setdefault("role", "hero")
    if sheet["controller"] not in {"player", "gm"} or sheet["role"] not in {"hero", "companion"}:
        fail(422, "invalid_dnd_sheet", "Choose a player/GM controller and hero/companion role")
    spellcasting = sheet.setdefault("spellcasting", {})
    if type(spellcasting) is not dict or spellcasting.keys() - {"ability", "class_abilities", "class_stats", "slots", "pact_slots", "concentration", "notes"}:
        fail(422, "invalid_dnd_sheet", "Use spellcasting ability, slots, pact_slots and concentration")
    caster = next((row for row in classes if row["name"] in CASTERS), None)
    if caster:
        spellcasting.setdefault("ability", CASTERS[caster["name"]])
    if "ability" in spellcasting and spellcasting["ability"] not in ATTRIBUTES:
        fail(422, "invalid_dnd_sheet", "Choose a spellcasting ability")
    class_abilities = spellcasting.setdefault("class_abilities", {})
    if type(class_abilities) is not dict or set(class_abilities) - {r["name"] for r in classes} or any(v not in ATTRIBUTES for v in class_abilities.values()):
        fail(422, "invalid_dnd_sheet", "Record a valid casting ability for each caster class")
    spellcasting["class_stats"] = []
    for row in classes:
        if row["name"] in CASTERS or row["name"] in class_abilities:
            ability = class_abilities.get(row["name"], CASTERS.get(row["name"], spellcasting.get("ability", "INT")))
            spellcasting["class_stats"].append({"class_name": row["name"], "ability": ability,
                                               "save_dc": 8+pb+mods[ability], "attack_bonus": pb+mods[ability]})
    capacity = slots_for(classes)
    previous_slots = spellcasting.get("slots", [])
    if type(previous_slots) is not list:
        fail(422, "invalid_dnd_sheet", "Spell slots must be a list")
    by_level = {}
    for row in previous_slots:
        if type(row) is not dict or row.keys() - {"level", "maximum", "used"} or row.get("level") in by_level:
            fail(422, "invalid_dnd_sheet", "Use unique spell slot levels")
        integer(row.get("level"), "spell slot level", 1, len(capacity))
        if row.get("maximum", capacity[row["level"]-1]) != capacity[row["level"]-1]:
            fail(422, "invalid_dnd_sheet", "Slot maximum must match class progression")
        by_level[row["level"]] = integer(row.get("used", 0), "spent spell slots", 0, capacity[row["level"]-1])
    spellcasting["slots"] = [{"level": i+1, "maximum": count, "used": by_level.get(i+1, 0)} for i, count in enumerate(capacity)]
    warlock = next((r for r in classes if r["name"] == "Warlock"), None)
    if warlock:
        wl = warlock["level"]
        count, slot_level = (1 if wl == 1 else 2 if wl < 11 else 3 if wl < 17 else 4), min(5, (wl+1)//2)
        pact = spellcasting.get("pact_slots", {})
        if type(pact) is not dict or pact.get("maximum", count) != count or pact.get("level", slot_level) != slot_level:
            fail(422, "invalid_dnd_sheet", "Pact slots must match Warlock progression")
        spellcasting["pact_slots"] = {"level": slot_level, "maximum": count, "used": integer(pact.get("used", 0), "spent pact slots", 0, count)}
    elif spellcasting.get("pact_slots"):
        fail(422, "invalid_dnd_sheet", "Pact slots require Warlock levels")
    if spellcasting.get("concentration") is not None:
        words(spellcasting["concentration"], "concentration", 256)
    for spell in sheet["spells"]:
        match = next((s for s in catalog()["spells"] if s["key"] == spell.get("key")), None)
        if match is None:
            fail(422, "unsupported_dnd_option", "Choose spells from the installed 2024 SRD catalogue")
        spell.update(name=match["name"], level=match["level"], concentration=match["concentration"],
                     ritual=match["ritual"], casting_time=match["casting_time"], description=match["desc"],
                     higher_level=match.get("higher_level", ""))
        if type(spell.get("prepared", False)) is not bool:
            fail(422, "invalid_dnd_sheet", "A spell's prepared marker is true or false")
    return sheet


def character_summary(sheet):
    return {**copy.deepcopy(sheet), "ancestry": sheet["species"], "background": sheet["background"],
            "xp_total": sheet["xp"], "xp_next": 1000, "scene_counter": 0, "def": sheet["armor_class"]}


def public_dnd_state(result):
    # GM content lives in Library, not in campaign/world/metadata sent to a browser.
    result["rules_check"] = {"current_profile": True, "game": GAME, "complete": bool(result.get("party"))}
    if result.get("party"):
        hero = next((s for s in result["party"] if s["id"] == result.get("hero_id")), result["party"][0])
        result["character"] = character_summary(hero)
    return result


class DndGame:
    def __init__(self, engine):
        self.engine, self.store = engine, engine.store

    def create(self, owner, name, action_id, disposable=False):
        from .chat_game import text
        identifier(action_id, "action_id")
        text(name, "campaign name", 80)
        if not name.strip() or type(disposable) is not bool:
            fail(422, "invalid_dnd_campaign", "Supply a campaign name and a boolean disposable flag")
        request = canonical({"mode": "chat", "name": name, "disposable": disposable, "game_id": GAME})
        with self.store.transaction() as db:
            prior = records.get(db, "creations_v1", {"owner": owner, "action_id": action_id})
            if prior:
                if prior["request"] != request:
                    fail(409, "idempotency_conflict", "Reuse the original new campaign arguments")
                result = json.loads(prior["result"])
                if result.get("_campaign_deleted"):
                    fail(410, "campaign_deleted", "This campaign has been deleted")
                return result
            state = {"id": "chat-" + uuid.uuid4().hex, "name": name.strip(), "version": 1, "mode": "chat",
                     "game_id": GAME, "game_rules_version": RULES, "rules_version": RULES, "rules_profile": GAME,
                     "phase": "character_draft", "paused": True, "disposable": disposable, "party": [], "hero_id": None,
                     "party_mode": "party", "level_up_freeze": False, "equipment": {}, "funds": {}, "world": {},
                     "creation": {}, "advancement": {}, "rarity_candidates": {}, "last_event": None,
                     "fictional_time_seconds": 0, "current_location": "Character creation", "opening_preview": "", "notes": "",
                     "adventure": {}, "continuity": {}, "campaign_preferences": {"focus": "mixed", "dialogue": "normal"},
                     "character": {"name": name.strip(), "class_name": "Unassigned", "level": 1, "attributes": dict.fromkeys(ATTRIBUTES, 10),
                                   "hp": 0, "hp_max": 1, "xp": 0, "xp_total": 0, "xp_next": 1000, "scene_counter": 0},
                     **{key: [] for key in ("abilities", "conditions", "summons", "enemies", "inventory", "supplies", "quest_log", "world_log", "generation_ledger")}}
            records.insert(db, "campaigns_v1", {"id": state["id"], "owner": owner, "version": 1, "data": canonical(state)})
            self.engine._append(db, state, {"kind": "create_dnd_game", "action_id": action_id})
            records.update(db, "campaigns_v1", {"id": state["id"]}, {"data": canonical(state)})
            from .chat_game import snapshot
            snapshot(db, state)
            result = public_state(state)
            records.insert(db, "creations_v1", {"owner": owner, "action_id": action_id,
                           "campaign_id": state["id"], "request": request, "result": canonical(result)})
            return result

    def update(self, owner, campaign_id, action_id, expected_version, summary, changes, begin_adventure=False, *, _db=None, _state=None):
        from .chat_game import bounded_json, merge_world, snapshot, text
        from .library import Library
        identifier(action_id, "action_id")
        integer(expected_version, "expected version", 1)
        text(summary, "summary", 2000)
        if not summary.strip() or type(changes) is not dict or type(begin_adventure) is not bool:
            fail(422, "invalid_dnd_update", "Supply a summary, change object and boolean begin_adventure")
        bounded_json(changes)
        if len(canonical(changes).encode()) > 250000:
            fail(422, "invalid_dnd_update", "A change batch exceeds 250000 bytes")
        allowed = {"party", "party_upsert", "party_remove", "hero_id", "party_mode", "name", "current_location", "opening_preview", "notes",
                   "world", "continuity", "adventure", "upsert", "remove", "replace", "fictional_time_seconds", "campaign_preferences", "begin_adventure"}
        if changes.keys() - allowed:
            fail(422, "protected_field", "Use D&D party sheets and campaign progress fields; game identity is fixed")
        if "begin_adventure" in changes:
            if type(changes["begin_adventure"]) is not bool:
                fail(422, "invalid_dnd_update", "begin_adventure must be boolean")
            begin_adventure = begin_adventure or changes["begin_adventure"]
        request = canonical({"expected_version": expected_version, "summary": summary, "changes": changes, "begin_adventure": begin_adventure})
        with (nullcontext(_db) if _db is not None else self.store.transaction()) as db:
            state = _state if _state is not None else self.engine._get(db, owner, campaign_id)
            if state.get("game_id") != GAME:
                fail(409, "game_mismatch", "Use the selected campaign's rules and save format")
            prior = records.get(db, "chat_updates_v1", {"campaign_id": campaign_id, "action_id": action_id})
            if prior:
                if prior["request"] != request:
                    fail(409, "idempotency_conflict", "Reuse the original turn save arguments")
                return json.loads(prior["result"])
            if state["version"] != expected_version:
                fail(409, "version_conflict", f"Current version is {state['version']}; read before saving again")
            projected = copy.deepcopy(state)
            if "party" in changes and ({"party_upsert", "party_remove"} & changes.keys()):
                fail(422, "invalid_dnd_update", "Replace the party or edit named members in one save")
            party = changes.get("party", projected["party"])
            if type(party) is not list or len(party) > 8:
                fail(422, "invalid_dnd_update", "A party contains at most eight character sheets")
            by_id = {s["id"]: copy.deepcopy(s) for s in party if type(s) is dict and "id" in s}
            if len(by_id) != len(party):
                fail(422, "invalid_dnd_update", "Each party member needs a distinct character ID")
            if type(changes.get("party_upsert", [])) is not list or type(changes.get("party_remove", [])) is not list:
                fail(422, "invalid_dnd_update", "Party edits must be lists")
            for patch in changes.get("party_upsert", []):
                if type(patch) is not dict or type(patch.get("id")) is not str:
                    fail(422, "invalid_dnd_update", "A party patch needs its character ID")
                by_id[patch["id"]] = merge_world(by_id.get(patch["id"], {}), patch)
            for key in changes.get("party_remove", []):
                if type(key) is not str:
                    fail(422, "invalid_dnd_update", "Remove party members by their character IDs")
                by_id.pop(key, None)
            if len(by_id) > 8:
                fail(422, "invalid_dnd_update", "A party contains at most eight character sheets")
            if not by_id and state["phase"] == "adventure":
                fail(422, "invalid_dnd_update", "Keep the adventuring party's character records, including downed members")
            projected["party"] = [normalize_sheet(sheet) for sheet in by_id.values()]
            projected["hero_id"] = changes.get("hero_id", projected.get("hero_id")) or next(iter(by_id), None)
            if projected["hero_id"] is not None and type(projected["hero_id"]) is not str:
                fail(422, "invalid_dnd_update", "Choose the hero by character ID")
            if projected["party"] and projected["hero_id"] not in by_id:
                fail(422, "invalid_dnd_update", "The lead character must be in the party")
            projected["party_mode"] = changes.get("party_mode", projected["party_mode"])
            if projected["party_mode"] not in {"solo", "party"}:
                fail(422, "invalid_dnd_update", "Choose Solo or Party")
            if projected["party_mode"] == "solo" and len(projected["party"]) > 1:
                fail(422, "invalid_dnd_update", "Solo uses one character; choose Party for companions")
            for key in ("name", "current_location", "opening_preview", "notes"):
                if key in changes:
                    projected[key] = words(changes[key], key)
            for key in ("world", "continuity", "campaign_preferences"):
                if key in changes:
                    if type(changes[key]) is not dict:
                        fail(422, "invalid_dnd_update", f"{key} must be an object")
                    projected[key] = merge_world(projected.get(key, {}), changes[key])
            if "continuity" in changes:
                from .continuity import validate_continuity
                validate_continuity(projected["continuity"])
            if "campaign_preferences" in changes:
                from .campaign_focus import validate_preferences
                validate_preferences(projected["campaign_preferences"])
            if "adventure" in changes:
                ref = changes["adventure"]
                if type(ref) is not dict or ref.keys() - {"id", "version", "current_section", "visited", "completed", "public_notes", "status", "title", "setting"}:
                    fail(422, "invalid_adventure_progress", "Save the adventure reference and public progress, keeping GM text in Library")
                old_ref = projected["adventure"] if ref.get("id", projected["adventure"].get("id")) == projected["adventure"].get("id") else {}
                ref = merge_world(old_ref, ref)
                entry = Library(self.engine)._get(db, owner, ref.get("id"), ref.get("version"))
                if entry["kind"] != "adventure":
                    fail(422, "adventure_required", "Select an adventure from your private library")
                ref.update(version=entry["version"], title=entry["content"]["title"], setting=entry["content"]["setting"])
                section_ids = {s["id"] for s in entry["content"]["sections"]}
                if ref.get("current_section") and ref["current_section"] not in section_ids:
                    fail(422, "invalid_adventure_progress", "Choose an existing adventure section")
                for key in ("visited", "completed"):
                    if type(ref.get(key, [])) is not list or any(x not in section_ids for x in ref.get(key, [])):
                        fail(422, "invalid_adventure_progress", "Track progress using existing section IDs")
                projected["adventure"] = ref
            groups = {"quest_log", "world_log", "enemies", "summons", "conditions"}
            if set(changes.get("replace", {})) & (set(changes.get("upsert", {})) | set(changes.get("remove", {}))):
                fail(422, "invalid_dnd_update", "Replace a collection or edit its individual entries")
            for op in ("replace", "upsert", "remove"):
                batch = changes.get(op, {})
                if type(batch) is not dict or batch.keys() - groups:
                    fail(422, "invalid_dnd_update", "Store character features, equipment and spells in their sheet; campaign collections are quests, logs and encounters")
                for group, rows in batch.items():
                    if type(rows) is not list:
                        fail(422, "invalid_dnd_update", "Collection changes must be lists")
                    data = {} if op == "replace" else {r["id"]: r for r in projected[group]}
                    seen = set()
                    for row in rows:
                        key = row if op == "remove" else row.get("id") if type(row) is dict else None
                        if type(key) is not str or not key or key in seen:
                            fail(422, "invalid_dnd_update", "Use distinct stable record IDs")
                        seen.add(key)
                        if op == "remove":
                            data.pop(key, None)
                        else:
                            data[key] = {**data.get(key, {}), **copy.deepcopy(row)}
                    projected[group] = list(data.values())
            time = changes.get("fictional_time_seconds", state["fictional_time_seconds"])
            integer(time, "fictional time", 0, 10**12)
            if time < state["fictional_time_seconds"] or state["phase"] != "adventure" and time != 0:
                fail(422, "invalid_dnd_time", "Continue time from the saved scene after the adventure starts")
            if state["paused"] and state["phase"] == "adventure" and time != state["fictional_time_seconds"]:
                fail(423, "paused", "Resume the paused campaign before advancing fictional time")
            projected["fictional_time_seconds"] = time
            if begin_adventure:
                if state["phase"] == "adventure":
                    fail(409, "wrong_phase", "This adventure has already started")
                if not projected["party"] or not projected["opening_preview"].strip() or not projected["adventure"]:
                    fail(422, "incomplete_dnd_start", "Save the party, adventure reference and opening scene together before starting")
                if any(not s["story_summary"].strip() or not s["inventory"] for s in projected["party"]):
                    fail(422, "incomplete_dnd_start", "Complete each character's story and starting equipment")
                adventure = Library(self.engine)._get(db, owner, projected["adventure"]["id"], projected["adventure"]["version"])["content"]
                start, end = adventure.get("starting_level", 1), adventure.get("ending_level", 20)
                if any(not start <= s["level"] <= end for s in projected["party"]):
                    fail(422, "adventure_level_mismatch", f"This adventure supports character levels {start}–{end}; choose an appropriate sheet or revise the adventure")
                projected.update(phase="adventure", paused=False)
            if projected["party"]:
                projected["character"] = character_summary(next(s for s in projected["party"] if s["id"] == projected["hero_id"]))
            if len(canonical(projected).encode()) > 2000000:
                fail(422, "invalid_dnd_update", "Saved campaign exceeds 2000000 bytes")
            projected["version"] += 1
            event = self.engine._append(db, projected, {"kind": "chat_update", "action_id": action_id, "summary": summary})
            records.update(db, "campaigns_v1", {"id": campaign_id, "owner": owner}, {"version": projected["version"], "data": canonical(projected)})
            snapshot(db, projected)
            result = {"campaign": public_state(projected), "event": safe_event(event)}
            records.insert(db, "chat_updates_v1", {"campaign_id": campaign_id, "action_id": action_id, "request": request, "result": canonical(result)})
            return result
