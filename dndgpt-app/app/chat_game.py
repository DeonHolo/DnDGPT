"""ChatGPT adjudicates; this module stores bounded, owned, retry-safe records."""
from __future__ import annotations

import copy
import json
import math
import uuid

from .engine import fail, identifier, public_state, safe_event
from .rules import ATTRIBUTES, EQUIPMENT_SLOTS, derived
from .storage import canonical
from .version import RULES_VERSION
from . import records

COLLECTIONS = {"abilities", "conditions", "summons", "enemies", "inventory", "supplies",
               "quest_log", "world_log", "generation_ledger"}
TEXT_FIELDS = {"name", "current_location", "opening_preview", "notes"}
OBJECT_FIELDS = {"world", "creation", "advancement", "funds"}
CHARACTER_TEXT = {"name", "class_name", "rarity", "title", "background", "biography", "appearance"}
CHARACTER_NUMBERS = {"level", "xp", "xp_total", "xp_next", "scene_counter", "attribute_points",
                     "skill_points", "talent_points", "hp", "hp_max", "mp", "mp_max", "sta",
                     "sta_max", "defense", "physical_defense", "magical_defense", "initiative",
                     "movement", "movement_meters", "movement_mm", "def", "carry_capacity_kg"}
CHARACTER_OBJECTS = {"class_details", "talent_web", "progression"}
CHAT_OPERATIONS = {"confirm_chat_character": (), "start_chat_adventure": (),
                   "correct_chat_state": ("changes", "reason")}


def number(value, name, low=0, high=1000000000):
    if type(value) is not int or not low <= value <= high:
        fail(422, "invalid_chat_update", f"{name} must be an integer in {low}..{high}")


def text(value, name, maximum=20000, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or len(value) > maximum:
        fail(422, "invalid_chat_update", f"{name} must be text of at most {maximum} characters")


def bounded_json(value, depth=0):
    if depth > 12:
        fail(422, "invalid_chat_update", "Record nesting exceeds 12 levels")
    if type(value) is dict:
        if len(value) > 500 or any(type(k) is not str or len(k) > 128 for k in value):
            fail(422, "invalid_chat_update", "Invalid object keys")
        for item in value.values():
            bounded_json(item, depth + 1)
    elif type(value) is list:
        if len(value) > 1000:
            fail(422, "invalid_chat_update", "A list exceeds 1000 entries")
        for item in value:
            bounded_json(item, depth + 1)
    elif type(value) is str:
        text(value, "record text", 50000)
    elif value is not None and type(value) not in (bool, int, float):
        fail(422, "invalid_chat_update", "Records must contain JSON values")
    elif (type(value) is int and abs(value) > 10**12 or
          type(value) is float and (not math.isfinite(value) or abs(value) > 10**12)):
        fail(422, "invalid_chat_update", "Non-finite or oversized number")


def validate_changes(changes):
    if type(changes) is not dict or not changes:
        fail(422, "invalid_chat_update", "changes must be a nonempty object")
    bounded_json(changes)
    if len(canonical(changes).encode()) > 250000:
        fail(422, "invalid_chat_update", "A change batch exceeds 250000 bytes")
    allowed = TEXT_FIELDS | OBJECT_FIELDS | {"character", "equipment", "fictional_time_seconds",
                                           "level_up_freeze", "upsert", "remove", "replace"}
    if set(changes) - allowed:
        fail(422, "protected_field", "Unknown or server-controlled state field")
    for key in TEXT_FIELDS & changes.keys():
        text(changes[key], key)
    for key in OBJECT_FIELDS & changes.keys():
        if type(changes[key]) is not dict:
            fail(422, "invalid_chat_update", f"{key} must be an object")
    if "fictional_time_seconds" in changes:
        number(changes["fictional_time_seconds"], "fictional_time_seconds", high=10**12)
    if "level_up_freeze" in changes and type(changes["level_up_freeze"]) is not bool:
        fail(422, "invalid_chat_update", "level_up_freeze must be boolean")
    ch = changes.get("character", {})
    if type(ch) is not dict or set(ch) - (CHARACTER_TEXT | CHARACTER_NUMBERS | CHARACTER_OBJECTS | {"attributes"}):
        fail(422, "invalid_chat_update", "Unknown character field")
    for key in CHARACTER_TEXT & ch.keys():
        text(ch[key], key, nullable=key in {"title", "background"})
    for key in CHARACTER_NUMBERS & ch.keys():
        number(ch[key], key, 1 if key in {"level", "xp_next"} else 0)
    for key in CHARACTER_OBJECTS & ch.keys():
        if type(ch[key]) is not dict:
            fail(422, "invalid_chat_update", f"{key} must be an object")
    if "attributes" in ch:
        if type(ch["attributes"]) is not dict or set(ch["attributes"]) - set(ATTRIBUTES):
            fail(422, "invalid_chat_update", "Unknown attribute")
        for key, value in ch["attributes"].items():
            number(value, key, 1, 1000000)
    if "equipment" in changes:
        equipment = changes["equipment"]
        if type(equipment) is not dict or set(equipment) - set(EQUIPMENT_SLOTS):
            fail(422, "invalid_chat_update", "Unknown equipment slot")
        for value in equipment.values():
            if value is not None and (type(value) is not str or not 1 <= len(value) <= 128):
                fail(422, "invalid_chat_update", "Equipment must reference an inventory ID or null")
    for operation in ("upsert", "remove", "replace"):
        groups = changes.get(operation, {})
        if type(groups) is not dict or set(groups) - COLLECTIONS:
            fail(422, "invalid_chat_update", "Unknown collection")
        for rows in groups.values():
            if type(rows) is not list:
                fail(422, "invalid_chat_update", "Collection changes must be lists")
            ids = []
            for row in rows:
                key = row if operation == "remove" else row.get("id") if type(row) is dict else None
                if type(key) is not str or not 1 <= len(key) <= 128 or not key.strip():
                    fail(422, "invalid_chat_update", "Each record needs a stable 1..128 character id")
                if operation != "remove":
                    for field in ("name", "rarity", "group", "activation", "status", "status_reason", "simple", "description"):
                        if field in row:
                            text(row[field], field)
                    for field in ("evolutions", "imprints"):
                        if field in row and (type(row[field]) is not list or any(type(child) is not dict for child in row[field])):
                            fail(422, "invalid_chat_update", f"{field} must be a list of records")
                ids.append(key)
            if len(set(ids)) != len(ids):
                fail(422, "invalid_chat_update", "Duplicate record IDs in a collection batch")
    if set(changes.get("replace", {})) & (set(changes.get("upsert", {})) | set(changes.get("remove", {}))):
        fail(422, "invalid_chat_update", "Do not replace and edit the same collection")


def apply_changes(state, changes, *, correction=False):
    validate_changes(changes)
    projected = copy.deepcopy(state)
    for key in TEXT_FIELDS | OBJECT_FIELDS | {"fictional_time_seconds", "level_up_freeze"}:
        if key in changes:
            projected[key] = copy.deepcopy(changes[key])
    for key, value in changes.get("character", {}).items():
        if key == "attributes":
            projected["character"][key].update(value)
        else:
            projected["character"][key] = copy.deepcopy(value)
    projected["equipment"].update(changes.get("equipment", {}))
    for group, rows in changes.get("replace", {}).items():
        projected[group] = copy.deepcopy(rows)
    for group, rows in changes.get("upsert", {}).items():
        records = {row["id"]: row for row in projected[group]}
        for row in rows:
            records[row["id"]] = {**records.get(row["id"], {}), **copy.deepcopy(row)}
        projected[group] = list(records.values())
    for group, ids in changes.get("remove", {}).items():
        projected[group] = [row for row in projected[group] if row["id"] not in ids]
    ch = projected["character"]
    for resource in ("hp", "mp", "sta"):
        if ch[resource] > ch[resource + "_max"]:
            fail(422, "invalid_chat_update", f"{resource} exceeds its recorded maximum")
    inventory = {row["id"] for row in projected["inventory"]}
    if any(item is not None and item not in inventory for item in projected["equipment"].values()):
        fail(422, "invalid_chat_update", "Equipped items must exist in inventory")
    if not correction:
        if projected["fictional_time_seconds"] < state["fictional_time_seconds"]:
            fail(422, "time_reversal", "Use an approved correction to move fictional time backwards")
        if state["phase"] != "adventure" and projected["fictional_time_seconds"] != 0:
            fail(423, "adventure_not_authorized", "No fictional time before adventure authorization")
        if state["phase"] == "ready" and changes.keys() - {"opening_preview", "world", "notes", "current_location"}:
            fail(423, "character_confirmed", "Review a correction to change a confirmed character before play")
        if state["phase"] == "adventure" and state["paused"]:
            fail(423, "paused", "Resume explicitly or review a correction while paused")
    if len(canonical(projected).encode()) > 2000000:
        fail(422, "invalid_chat_update", "Saved record exceeds 2000000 bytes")
    return projected


def apply_lifecycle(state, kind, payload):
    if state.get("mode") != "chat":
        fail(422, "chat_mode_required", "This action is only for a fresh chat-led game")
    if kind == "confirm_chat_character":
        if state["phase"] != "character_draft":
            fail(409, "wrong_phase", "Character is already confirmed")
        ch = state["character"]
        if not ch["name"].strip() or ch["class_name"] == "Unassigned" or not ch["class_name"].strip():
            fail(422, "incomplete_character", "Prepare the character and class before confirmation")
        state["phase"] = "ready"
    elif kind == "start_chat_adventure":
        if state["phase"] != "ready" or not state["opening_preview"].strip():
            fail(409, "opening_required", "Confirm the character and prepare an opening preview first")
        state["phase"], state["paused"] = "adventure", False
    elif kind == "correct_chat_state":
        text(payload.get("reason"), "reason", 2000)
        if not payload["reason"].strip():
            fail(422, "invalid_chat_update", "A correction needs a reason")
        state.update(apply_changes(state, payload.get("changes"), correction=True))
        if state["phase"] != "adventure" and state["fictional_time_seconds"] != 0:
            fail(423, "adventure_not_authorized", "Corrections cannot start an adventure")
    elif kind == "pause":
        state["paused"] = True
    elif kind == "resume":
        if state["phase"] != "adventure":
            fail(423, "adventure_not_authorized", "Use the separate start adventure confirmation")
        state["paused"] = False
    else:
        fail(422, "chat_gm_adjudicates", "Use saved random tools and save_chat_update for chat-led mechanics")
    return {"kind": kind, "reason": payload.get("reason")}


def snapshot(db, state):
    records.insert(db, "chat_versions_v1", {"campaign_id": state["id"], "version": state["version"],
                                           "data": canonical(state)})


class ChatGame:
    def __init__(self, engine):
        self.engine, self.store = engine, engine.store

    def create(self, owner, name, action_id, disposable=False):
        identifier(action_id, "action_id")
        text(name, "name", 80)
        if not name.strip() or type(disposable) is not bool:
            fail(422, "invalid_chat_update", "A game needs a name and boolean disposable flag")
        request = canonical({"mode": "chat", "name": name, "disposable": disposable})
        with self.store.transaction() as db:
            prior = records.get(db, "creations_v1", {"owner": owner, "action_id": action_id})
            if prior:
                if prior["request"] != request:
                    fail(409, "idempotency_conflict", "action_id already has different arguments")
                return json.loads(prior["result"])
            attributes = dict.fromkeys(ATTRIBUTES, 5)
            stats = derived(attributes)
            character = {"name": name.strip(), "class_name": "Unassigned", "rarity": "COMMON",
                         "attributes": attributes, **stats, "level": 1, "xp": 0, "xp_total": 0,
                         "xp_next": 100, "scene_counter": 0, "attribute_points": 0,
                         "skill_points": 0, "talent_points": 0, "title": None, "background": None,
                         **{key: stats[key + "_max"] for key in ("hp", "mp", "sta")}}
            state = {"id": "chat-" + uuid.uuid4().hex, "name": name.strip(), "version": 1,
                     "mode": "chat", "rules_version": RULES_VERSION, "phase": "character_draft",
                     "paused": True, "disposable": disposable, "character": character,
                     "level_up_freeze": False, "equipment": dict.fromkeys(EQUIPMENT_SLOTS),
                     **{key: [] for key in COLLECTIONS}, "world": {}, "creation": {}, "funds": {},
                     "current_location": "Character creation", "opening_preview": "", "notes": "",
                     "fictional_time_seconds": 0, "advancement": {}, "rarity_candidates": {}, "last_event": None}
            records.insert(db, "campaigns_v1", {"id": state["id"], "owner": owner, "version": 1, "data": canonical(state)})
            self.engine._append(db, state, {"kind": "create_chat_game", "action_id": action_id})
            records.update(db, "campaigns_v1", {"id": state["id"]}, {"data": canonical(state)})
            snapshot(db, state)
            result = public_state(state)
            records.insert(db, "creations_v1", {"owner": owner, "action_id": action_id,
                                               "request": request, "result": canonical(result)})
            return result

    def update(self, owner, campaign_id, action_id, expected_version, summary, changes):
        identifier(action_id, "action_id")
        number(expected_version, "expected_version", 1)
        text(summary, "summary", 2000)
        if not summary.strip():
            fail(422, "invalid_chat_update", "A save needs a summary")
        validate_changes(changes)
        request = canonical({"expected_version": expected_version, "summary": summary, "changes": changes})
        with self.store.transaction() as db:
            state = self.engine._get(db, owner, campaign_id)
            if state.get("mode") != "chat":
                fail(422, "chat_mode_required", "Existing campaigns cannot be converted or changed by this tool")
            prior = records.get(db, "chat_updates_v1", {"campaign_id": campaign_id, "action_id": action_id})
            if prior:
                if prior["request"] != request:
                    fail(409, "idempotency_conflict", "action_id already has different arguments")
                return json.loads(prior["result"])
            if state["version"] != expected_version:
                fail(409, "version_conflict", f"Current version is {state['version']}; read before saving again")
            state = apply_changes(state, changes)
            state["version"] += 1
            event = self.engine._append(db, state, {"kind": "chat_update", "action_id": action_id, "summary": summary})
            records.update(db, "campaigns_v1", {"id": campaign_id, "owner": owner},
                           {"version": state["version"], "data": canonical(state)})
            snapshot(db, state)
            result = {"campaign": public_state(state), "event": safe_event(event)}
            records.insert(db, "chat_updates_v1", {"campaign_id": campaign_id, "action_id": action_id,
                                                  "request": request, "result": canonical(result)})
            return result

    def version(self, owner, campaign_id, version):
        number(version, "version", 1)
        with self.store.transaction() as db:
            state = self.engine._get(db, owner, campaign_id)
            if state.get("mode") != "chat":
                fail(422, "chat_mode_required", "History is only available for chat-led games")
            row = records.get(db, "chat_versions_v1", {"campaign_id": campaign_id, "version": version})
            if row is None:
                fail(404, "not_found", "Saved version not found")
            return {"campaign": public_state(json.loads(row["data"])), "current_version": state["version"], "historical": True}
