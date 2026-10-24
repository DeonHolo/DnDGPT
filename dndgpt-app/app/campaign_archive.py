"""Portable current snapshots. Restore creates a distinct paused chat-led copy."""
import copy
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone

from . import records
from .chat_game import (COLLECTIONS, OBJECT_FIELDS, TEXT_FIELDS, apply_changes,
                        bounded_json, number, snapshot, text)
from .engine import fail, identifier, public_state
from .storage import canonical

FORMAT = "dndgpt.campaign/1"
MAX_BYTES = 2200000
STATE_FIELDS = {"id", "name", "version", "mode", "rules_version", "rules_profile", "phase", "paused",
                "game_id", "game_rules_version",
                "disposable", "character", "level_up_freeze", "equipment", "current_location", "opening_preview",
                "notes", "fictional_time_seconds", "world", "creation", "advancement", "funds",
                "rarity_candidates", "last_event", "continuity", "restored_from"} | COLLECTIONS
STATE_FIELDS |= {"sovereignty", "quest_settlements", "reward_credits", "event_tracking"}


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate_archive(archive):
    if type(archive) is not dict or archive.keys() != {"format", "exported_at", "campaign", "sha256"}:
        fail(422, "invalid_archive", "Choose a DnDGPT campaign export")
    source = archive["campaign"]
    if type(source) is not dict or source.keys() - STATE_FIELDS:
        fail(422, "invalid_archive", "Unsupported campaign fields")
    bounded_json(source)
    text(archive["exported_at"], "exported_at", 80)
    if len(canonical(archive).encode()) > MAX_BYTES or archive["format"] != FORMAT:
        fail(422, "invalid_archive", "Unsupported or oversized campaign export")
    checksum = archive["sha256"]
    if (type(checksum) is not str or len(checksum) != 64 or not checksum.isascii()
            or not secrets.compare_digest(digest(source), checksum)):
        fail(422, "archive_checksum", "Campaign export is damaged or its checksum does not match")
    required = (STATE_FIELDS - {"continuity", "restored_from", "rules_profile", "game_id", "game_rules_version", "sovereignty",
                               "quest_settlements", "reward_credits", "event_tracking"})
    if not required <= source.keys() or source["mode"] != "chat":
        fail(422, "invalid_archive", "Only complete chat-led campaign snapshots can be restored")
    if type(source["phase"]) is not str or source["phase"] not in {"character_draft", "ready", "adventure"}:
        fail(422, "invalid_archive", "Invalid saved campaign phase")
    if any(type(source[key]) is not bool for key in ("paused", "disposable", "level_up_freeze")):
        fail(422, "invalid_archive", "Invalid saved campaign flags")
    number(source["version"], "source version", 1)
    number(source["fictional_time_seconds"], "fictional_time_seconds", high=10**12)
    for key in ("id", "rules_version"):
        text(source[key], key, 128)
    text(archive["exported_at"], "exported_at", 80)
    if "rules_profile" in source:
        text(source["rules_profile"], "rules_profile", 128)
    from .game_profiles import validate_game, game_id
    try:
        validate_game(game_id(source), source.get("game_rules_version", "1.0"))
    except ValueError as error:
        fail(422, "invalid_archive", str(error))
    if type(source["rarity_candidates"]) is not dict or not (source["last_event"] is None or type(source["last_event"]) is dict):
        fail(422, "invalid_archive", "Invalid saved campaign records")
    for roll in source["rarity_candidates"].values():
        if (type(roll) is not dict or type(roll.get("enhanced")) is not bool or
                roll.get("final_rarity") not in ("COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY", "UNIQUE")):
            fail(422, "invalid_archive", "Invalid recorded rarity")
    character = source["character"]
    required_character = {"name", "class_name", "rarity", "attributes", "level", "xp", "xp_next", "scene_counter",
                          "attribute_points", "skill_points", "talent_points", "hp", "hp_max", "mp", "mp_max", "def"}
    if type(character) is not dict or not required_character <= character.keys():
        fail(422, "invalid_archive", "The saved character is incomplete")
    attributes = character["attributes"]
    if (type(attributes) is not dict or not {"STR", "INT", "CHA", "LCK"} <= attributes.keys()
            or len(attributes.keys() & {"DEX", "AGI"}) != 1):
        fail(422, "invalid_archive", "The saved attributes are incomplete")
    changes = {key: source[key] for key in TEXT_FIELDS | OBJECT_FIELDS if key in source}
    changes.update(character=character, equipment=source["equipment"],
                   fictional_time_seconds=source["fictional_time_seconds"],
                   level_up_freeze=source["level_up_freeze"], replace={key: source[key] for key in COLLECTIONS})
    projected = apply_changes(source, changes, correction=True)
    if source["phase"] != "adventure" and source["fictional_time_seconds"] != 0:
        fail(422, "invalid_archive", "An unstarted adventure cannot have elapsed gameplay time")
    return projected


class CampaignArchive:
    def __init__(self, engine):
        self.engine, self.store = engine, engine.store

    def export(self, owner, campaign_id):
        with self.store.transaction() as db:
            state = self.engine._get(db, owner, campaign_id)
            if state.get("mode") != "chat":
                fail(422, "chat_mode_required", "Portable exports support chat-led campaigns")
            archive = {"format": FORMAT, "exported_at": datetime.now(timezone.utc).isoformat(),
                       "campaign": copy.deepcopy(state), "sha256": digest(state)}
            if len(canonical(archive).encode()) > MAX_BYTES:
                fail(422, "archive_too_large", "This campaign exceeds the portable snapshot size limit")
            return {"archive": archive, "filename": "dndgpt-" + state["id"] + "-v" + str(state["version"]) + ".json",
                    "contains": "Current snapshot, recorded outcomes and continuity; server history stays with the source campaign"}

    def preview(self, archive):
        source = validate_archive(archive)
        character = source["character"]
        return {"source_name": source["name"], "source_version": source["version"],
                "character_name": character["name"], "class_name": character["class_name"],
                "location": source["current_location"], "phase": source["phase"],
                "abilities": len(source["abilities"]), "inventory_items": len(source["inventory"]),
                "level_up_freeze": source["level_up_freeze"], "restored_paused": True,
                "overwrites_existing": False, "sha256": archive["sha256"],
                "notice": "Restore makes a separate paused campaign. The checksum checks file integrity, not the authenticity of player-supplied data."}

    def restore(self, owner, archive, action_id, confirm_restore):
        identifier(action_id, "action_id")
        if confirm_restore is not True:
            fail(403, "approval_required", "Review the import and explicitly confirm creating a paused copy")
        source = validate_archive(archive)
        request = "restore:" + digest(archive)
        with self.store.transaction() as db:
            prior = records.get(db, "creations_v1", {"owner": owner, "action_id": action_id})
            if prior:
                if prior["request"] != request:
                    fail(409, "idempotency_conflict", "action_id already has different arguments")
                result = json.loads(prior["result"])
                if result.get("_campaign_deleted"):
                    fail(410, "campaign_deleted", "The restored campaign was deleted")
                return result
            state = copy.deepcopy(source)
            state.update(id="chat-" + uuid.uuid4().hex, name=source["name"][:69] + " (restored)",
                         version=1, paused=True, disposable=False, last_event=None,
                         restored_from={"campaign_id": source["id"], "version": source["version"],
                                        "sha256": archive["sha256"]})
            records.insert(db, "campaigns_v1", {"id": state["id"], "owner": owner, "version": 1, "data": canonical(state)})
            self.engine._append(db, state, {"kind": "restore_chat_campaign", "action_id": action_id,
                                           "summary": "Restored a portable snapshot as a separate paused campaign"})
            records.update(db, "campaigns_v1", {"id": state["id"], "owner": owner}, {"data": canonical(state)})
            snapshot(db, state)
            result = {"campaign": public_state(state), "restored": True}
            records.insert(db, "creations_v1", {"owner": owner, "action_id": action_id, "campaign_id": state["id"],
                                               "request": request, "result": canonical(result)})
            return result
