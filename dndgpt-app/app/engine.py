"""Authoritative sandbox engine reused by HTTP and MCP; no AI service calls."""
from __future__ import annotations

import copy
import hashlib
import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from dataclasses import asdict

from .rules import ATTRIBUTES, EQUIPMENT_SLOTS, Dice, TurnBudget, award_xp, derived, integer
from .storage import Store, canonical
from .version import APP_VERSION, RULES_VERSION
from .scenes import SCENE_IDS
from . import combat, gear
from . import records

COMBAT_OPERATIONS = {
    "prepare_combat": ("actors", "order", "obstacles"), "start_combat": (),
    "use_ability": ("actor_id", "ability_id", "target_ids"),
    "combat_move": ("actor_id", "path"), "end_turn": ("actor_id",),
    "manifest_summons": ("actor_id", "ability_id", "placements"),
    "command_summons": ("actor_id", "ability_id", "orders"),
}
GEAR_OPERATIONS = {
    "prepare_loadout": ("loadout",), "equip_item": ("actor_id", "item_id", "slots"),
    "unequip_item": ("actor_id", "item_id"), "retrieve_item": ("actor_id", "item_id"),
    "use_item": ("actor_id", "item_id", "ability_id", "target_ids"),
}
DEVELOPMENT_OPERATIONS = {**COMBAT_OPERATIONS, **GEAR_OPERATIONS}

OPERATIONS = {
    "pause": (), "resume": (),
    "roll_check": ("dc", "modifier", "advantage", "disadvantage"),
    "roll_dice": ("sides", "count"), "roll_rarity": ("candidate_id",),
    "spend_mp": ("cost",), "award_xp": ("amount", "reward_id"),
    "record_scene": ("scene_id",), "spend_attribute": ("attribute",),
    "confirm_chat_character": (), "start_chat_adventure": (),
    "correct_chat_state": ("changes", "reason"),
    **DEVELOPMENT_OPERATIONS,
}


class EngineError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code = status, code
        super().__init__(message)


def fail(status, code, message):
    raise EngineError(status, code, message)


def identifier(value, name):
    if not isinstance(value, str) or not 8 <= len(value) <= 128 or not value.strip():
        fail(422, "invalid_identifier", f"{name} must contain 8..128 characters")
    return value


def safe_event(event):
    result = json.loads(canonical(event))
    if result.get("kind") == "roll_rarity" and "roll" in result:
        roll = result.pop("roll")
        result.update(final_rarity=roll["final_rarity"], enhanced=roll["enhanced"])
    return result


def public_state(state):
    result = json.loads(canonical(state))
    if state.get("mode") == "chat":
        from .standard_rules import class_kit_check, uses_standard_rules
        result["rules_check"] = {"current_profile": uses_standard_rules(state), **class_kit_check(state)}
    result["rarity_candidates"] = {
        key: {"final_rarity": roll["final_rarity"], "enhanced": roll["enhanced"]}
        for key, roll in result["rarity_candidates"].items()}
    if result["last_event"]:
        result["last_event"] = safe_event(result["last_event"])
    from .continuity import resume_brief
    result["resume_brief"] = resume_brief(state)
    return json.loads(canonical(result))


def state_hash(state):
    return hashlib.sha256(canonical({k: v for k, v in state.items()
                                     if k != "last_event"}).encode()).hexdigest()


class Engine:
    def __init__(self, store: Store, dice: Dice | None = None, *, enable_combat=False):
        if type(enable_combat) is not bool:
            raise ValueError("enable_combat must be an explicit boolean")
        self.store = store
        self.dice = dice or Dice()
        self.enable_combat = enable_combat

    def _get(self, db, owner, campaign_id):
        deletion = records.get(db, "campaign_deletions_v1",
                               {"owner": owner, "campaign_id": campaign_id})
        if deletion:
            try:
                phase = json.loads(deletion["data"]).get("phase")
            except (AttributeError, TypeError, json.JSONDecodeError):
                fail(503, "storage_integrity", "Campaign deletion record is invalid")
            if phase in {"deleting", "complete"}:
                fail(410, "campaign_deleted", "This campaign is being deleted or has already been deleted")
        row = records.get(db, "campaigns_v1", {"id": campaign_id, "owner": owner})
        if row is None:
            fail(404, "not_found", "Campaign not found")
        state = json.loads(row["data"])
        if state["version"] != row["version"]:
            fail(409, "integrity_error", "Stored campaign version mismatch")
        return state

    def _append(self, db, state, event):
        rows = records.find(db, "events_v1", {"campaign_id": state["id"]},
                            order="number", descending=True, limit=1)
        last = rows[0] if rows else None
        previous = last["hash"] if last else "0" * 64
        event = {**event, "version": state["version"], "state_sha256": state_hash(state),
                 "utc": datetime.now(timezone.utc).isoformat()}
        digest = hashlib.sha256((previous + canonical(event)).encode()).hexdigest()
        records.insert(db, "events_v1", {"campaign_id": state["id"], "number": state["version"],
                                        "event": canonical(event), "previous_hash": previous, "hash": digest})
        state["last_event"] = event
        return event

    def create_sandbox(self, owner, name, action_id):
        identifier(action_id, "action_id")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            fail(422, "invalid_name", "Sandbox name must contain 1..80 characters")
        request = canonical({"name": name})
        with self.store.transaction() as db:
            prior = records.get(db, "creations_v1", {"owner": owner, "action_id": action_id})
            if prior:
                if prior["request"] != request:
                    fail(409, "idempotency_conflict", "action_id already has different arguments")
                result = json.loads(prior["result"])
                if result.get("_campaign_deleted"):
                    fail(410, "campaign_deleted", "The campaign created by this action was deleted")
                return result
            attributes = dict.fromkeys(ATTRIBUTES, 5)
            stats = derived(attributes)
            character = {"name": name.strip(), "attributes": attributes, **stats,
                         "level": 1, "class_name": "Unassigned sandbox", "rarity": "COMMON",
                         "title": None, "background": None, "xp": 0, "xp_total": 0,
                         "xp_next": 100, "scene_counter": 0, "attribute_points": 0,
                         "skill_points": 0, "talent_points": 0,
                         "hp": stats["hp_max"], "mp": stats["mp_max"],
                         "sta": stats["sta_max"]}
            state = {"id": "sandbox-" + uuid.uuid4().hex, "name": name.strip(),
                     "version": 1, "rules_version": RULES_VERSION, "mode": "sandbox",
                     "paused": True, "level_up_freeze": False, "character": character,
                     "abilities": [], "conditions": [], "summons": [], "enemies": [],
                     "equipment": dict.fromkeys(EQUIPMENT_SLOTS), "inventory": [],
                     "supplies": [], "quest_log": [], "world_log": [],
                     "current_location": "Development sandbox", "fictional_time_seconds": 0,
                     "advancement": {"pending_levels": [], "offers_ready": False},
                     "rarity_candidates": {}, "reward_ids": [], "scene_ids": [],
                     "notes": "Mechanics test sandbox; character creation is not implemented.",
                     "last_event": None}
            records.insert(db, "campaigns_v1", {"id": state["id"], "owner": owner,
                                               "version": 1, "data": canonical(state)})
            self._append(db, state, {"kind": "create_sandbox", "action_id": action_id,
                                     "result": "Created paused sandbox; no gameplay started"})
            records.update(db, "campaigns_v1", {"id": state["id"]}, {"data": canonical(state)})
            result = public_state(state)
            records.insert(db, "creations_v1", {"owner": owner, "action_id": action_id,
                                               "campaign_id": state["id"],
                                               "request": request, "result": canonical(result)})
            return result

    def list_campaigns(self, owner):
        with self.store.transaction() as db:
            rows = records.find(db, "campaigns_v1", {"owner": owner}, order="rowid", descending=True, limit=100)
            deleting = set()
            for row in records.find(db, "campaign_deletions_v1", {"owner": owner}, limit=1000):
                try:
                    phase = json.loads(row["data"]).get("phase")
                except (AttributeError, TypeError, json.JSONDecodeError):
                    fail(503, "storage_integrity", "Campaign deletion record is invalid")
                if phase in {"deleting", "complete"}:
                    deleting.add(row["campaign_id"])
            return [{"id": row["id"], "version": row["version"],
                     "name": json.loads(row["data"])["name"]} for row in rows
                    if row["id"] not in deleting]

    def get_campaign(self, owner, campaign_id):
        with self.store.transaction() as db:
            return public_state(self._get(db, owner, campaign_id))

    def campaign_context(self, owner, campaign_id):
        with self.store.transaction() as db:
            state = self._get(db, owner, campaign_id)
            return {"campaign": public_state(state),
                    "_meta": self.pending_approval(owner, campaign_id, db=db, state=state)}

    def _command(self, kind, payload):
        if (kind not in OPERATIONS or type(payload) is not dict or
                (kind in DEVELOPMENT_OPERATIONS and not self.enable_combat)):
            fail(422, "unsupported_action", "Unsupported action or invalid payload")
        if set(payload) - set(OPERATIONS[kind]):
            fail(422, "unexpected_payload", "Unexpected payload fields")
        try:
            if kind in DEVELOPMENT_OPERATIONS and len(canonical(payload).encode("utf-8")) > 1000000:
                raise ValueError("Combat proposal exceeds the development size limit")
            if kind == "roll_check":
                integer(payload.get("dc"), 1, 40, "dc")
                integer(payload.get("modifier"), -20, 40, "modifier")
                for key in ("advantage", "disadvantage"):
                    if key in payload and type(payload[key]) is not bool:
                        raise ValueError(f"{key} must be boolean")
            elif kind == "roll_dice":
                integer(payload.get("sides"), 2, 10000, "sides")
                integer(payload.get("count"), 1, 20, "count")
            elif kind == "spend_mp":
                integer(payload.get("cost"), 1, 1000, "cost")
            elif kind == "award_xp":
                integer(payload.get("amount"), 1, 10000, "amount")
                identifier(payload.get("reward_id"), "reward_id")
            elif kind in ("roll_rarity", "record_scene"):
                key = "candidate_id" if kind == "roll_rarity" else "scene_id"
                identifier(payload.get(key), key)
            elif kind == "spend_attribute" and payload.get("attribute") not in ATTRIBUTES:
                raise ValueError("Unknown attribute")
        except (ValueError, TypeError) as error:
            fail(422, "invalid_payload", str(error))

    def _sync_loadout(self, state, loadout):
        gear.recalculate(state["character"], loadout)
        projection = gear.calculate(loadout, state["character"]["attributes"])
        state["loadout"] = gear.encode(loadout)
        state["equipment"] = projection["equipment"]
        state["inventory"] = [{**row, "weight_kg": row["weight_grams"] / 1000} for row in projection["items"]]
        state["supplies"] = projection["supplies"]
        state["funds"] = projection["funds"]

    def _sync_combat(self, state):
        player = state["encounter"]["actors"]["player"]
        for resource in ("hp", "mp", "sta"):
            state["character"][resource] = player[resource]
        state["abilities"] = player["abilities"]
        if "loadout" in player:
            self._sync_loadout(state, gear.decode(player["loadout"]))
        state["conditions"] = [row["definition"]["name"] for row in player["conditions"]]
        state["enemies"] = [dict(id=row["id"], name=row["name"], hp=row["hp"], hp_max=row["hp_max"],
                                 **{"def": row["def"]}) for row in state["encounter"]["actors"].values()
                            if row["team"] != player["team"]]
        state["summons"] = [copy.deepcopy(row) for row in state["encounter"]["actors"].values()
                            if row.get("summon", {}).get("owner_id") == "player"]

    def _apply_gear(self, state, kind, payload, preview):
        combat.exact(payload, GEAR_OPERATIONS[kind])
        if not self.enable_combat or state["mode"] != "sandbox":
            raise ValueError("Inventory runtime requires an opted-in development sandbox")
        event = {"kind": kind, "preview": preview}
        if kind == "prepare_loadout":
            if state["version"] != 1 or not state["paused"] or "loadout" in state:
                raise ValueError("Prepare equipment once in a fresh paused sandbox")
            self._sync_loadout(state, gear.decode(payload["loadout"]))
            event["result"] = "Owned development loadout prepared; current resources preserved"
            return event
        if state["paused"] or state["level_up_freeze"]:
            fail(423, "paused", "Campaign paused or frozen; item changes are blocked")
        if state.get("encounter", {}).get("status") == "ready":
            raise ValueError("Start the fixed encounter before changing equipment")
        if state.get("encounter", {}).get("status") == "active":
            state["encounter"], receipt = combat.apply(state["encounter"], kind, payload, self.dice, preview=preview)
            self._sync_combat(state)
            state["fictional_time_seconds"] += receipt["elapsed_seconds"]
            event.update(receipt)
            return event
        if "loadout" not in state:
            raise ValueError("No owned loadout is prepared")
        if payload["actor_id"] != "player":
            raise ValueError("Outside combat only the saved player has an item target context")
        loadout = gear.decode(state["loadout"])
        if kind in ("equip_item", "unequip_item"):
            slots = tuple(combat.rows(payload["slots"], 16)) if kind == "equip_item" else ()
            updated, receipt = gear.change_equipment(loadout, payload["item_id"], slots)
        elif kind == "retrieve_item":
            updated, receipt = gear.retrieve(loadout, payload["item_id"])
        else:
            item, power = gear.find_power(loadout, payload["ability_id"])
            program = power.ability.program
            if item.id != payload["item_id"]:
                raise ValueError("Ability does not belong to that item")
            if (payload["target_ids"] != ["player"] or program.target_kind != "SELF" or program.resolution.kind != "AUTO" or
                    program.cooldown_turns or program.uses_per_encounter is not None or
                    any(effect.kind in ("WARD", "CONDITION", "REMOVE_CONDITION") for effect in program.effects)):
                raise ValueError("This item needs a persistent combat/condition context before activation")
            ch = state["character"]
            player = {**copy.deepcopy(ch), "id": "player", "team": "player", "position": [0, 0, 0], "abilities": [],
                      "loadout": state["loadout"], "imprints": [], "conditions": [], "ward": None, "resistances": {},
                      "reaction_policy": "CONSERVE", "turn": 1, "budget": asdict(TurnBudget(movement_mm=ch["movement_mm"])),
                      "movement_spent_mm": 0,
                      "cooldowns": {}, "uses_turn": {}, "uses_encounter": {}}
            encounter = {"schema": 1, "actors": {"player": player}, "order": ["player"], "active": "player",
                         "round": 1, "status": "active", "obstacles": []}
            result, receipt = combat.apply(encounter, kind, payload, self.dice, preview=preview)
            player = result["actors"]["player"]
            for resource in ("hp", "mp", "sta"):
                ch[resource] = player[resource]
            updated = gear.decode(player["loadout"])
            receipt["elapsed_seconds"] = 6
        self._sync_loadout(state, updated)
        state["fictional_time_seconds"] += receipt["elapsed_seconds"]
        event.update(receipt)
        return event

    def _apply(self, state, kind, payload, *, preview=False):
        from .chat_game import CHAT_OPERATIONS, apply_lifecycle
        if state.get("mode") == "chat" or kind in CHAT_OPERATIONS:
            return apply_lifecycle(state, kind, payload)
        ch = state["character"]
        event = {"kind": kind, "result": kind.replace("_", " ")}
        if kind == "pause":
            state["paused"] = True
            return event
        if kind == "resume":
            if state["level_up_freeze"]:
                fail(423, "advancement_frozen", "Advancement must be resolved before a separate resume")
            state["paused"] = False
            return event
        if kind in GEAR_OPERATIONS:
            try:
                return self._apply_gear(state, kind, payload, preview)
            except (ValueError, TypeError, KeyError) as error:
                fail(422, "invalid_item_action", str(error))
        if kind in COMBAT_OPERATIONS:
            if not self.enable_combat or state["mode"] != "sandbox":
                fail(422, "unsupported_action", "Combat runtime is restricted to opted-in development sandboxes")
            try:
                if kind == "prepare_combat":
                    combat.exact(payload, COMBAT_OPERATIONS[kind])
                    if not state["paused"] or state["level_up_freeze"] or "encounter" in state:
                        raise ValueError("Prepare a scenario once in a fresh paused sandbox")
                    actors = copy.deepcopy(combat.rows(payload["actors"], 32, 2))
                    for actor in actors:
                        if type(actor) is not dict:
                            raise ValueError("Actor must be a declared object")
                        if actor.get("id") == "player":
                            if "loadout" in actor and actor["loadout"] != state.get("loadout"):
                                raise ValueError("Scenario cannot substitute the player's owned equipment")
                            if "loadout" in state:
                                actor["loadout"] = copy.deepcopy(state["loadout"])
                    state["encounter"] = combat.prepare(ch, actors, payload["order"], payload["obstacles"])
                    event["result"] = "Development scenario prepared; no combat started or dice rolled"
                else:
                    if state["paused"] or state["level_up_freeze"]:
                        fail(423, "paused", "Campaign paused or frozen; gameplay changes and rolls are blocked")
                    if "encounter" not in state:
                        raise ValueError("No prepared combat scenario")
                    state["encounter"], receipt = combat.apply(state["encounter"], kind, payload, self.dice, preview=preview)
                    event.update(receipt)
                    state["fictional_time_seconds"] += receipt["elapsed_seconds"]
                self._sync_combat(state)
            except (ValueError, TypeError, KeyError) as error:
                fail(422, "invalid_combat", str(error))
            return event
        if state.get("encounter", {}).get("status") in ("ready", "active"):
            fail(423, "combat_active", "Resolve the prepared encounter before unrelated sandbox mutations")
        if kind == "spend_attribute":
            if not state["level_up_freeze"] or ch["attribute_points"] < 1:
                fail(422, "no_attribute_point", "No frozen advancement Attribute Point available")
            attribute = payload["attribute"]
            if ch["attributes"][attribute] + 2 > 20:
                fail(422, "attribute_cap", "Attribute cap would waste the point")
            ch["attributes"][attribute] += 2
            ch["attribute_points"] -= 1
            gear.recalculate(ch, gear.decode(state["loadout"]) if "loadout" in state else None)
            event.update(attribute=attribute, result="Attribute increased by 2; no resource refill")
            return event
        if state["paused"] or state["level_up_freeze"]:
            fail(423, "paused", "Campaign paused or frozen; gameplay changes and rolls are blocked")
        if kind == "spend_mp":
            if payload["cost"] > ch["mp"]:
                fail(422, "insufficient_mp", "Insufficient MP")
            ch["mp"] -= payload["cost"]
            event["cost"] = payload["cost"]
        elif kind == "roll_check" and not preview:
            event.update(self.dice.check(payload["dc"], payload["modifier"],
                                        payload.get("advantage", False),
                                        payload.get("disadvantage", False)))
            event["result"] = "Success" if event["success"] else "Failure or complication"
        elif kind == "roll_dice" and not preview:
            rolls = [self.dice.roll(payload["sides"]) for _ in range(payload["count"])]
            event.update(rolls=rolls, sides=payload["sides"], total=sum(rolls), rng=self.dice.source)
        elif kind == "roll_rarity":
            key = payload["candidate_id"]
            if key in state["rarity_candidates"]:
                fail(409, "candidate_fixed", "Candidate rarity is already fixed; it cannot be rerolled")
            if not preview:
                roll = self.dice.rarity(ch["attributes"]["LCK"])
                state["rarity_candidates"][key] = roll
                event.update(candidate_id=key, roll=roll, result="Candidate rarity fixed")
        elif kind == "award_xp":
            key = payload["reward_id"]
            if key in state["reward_ids"]:
                fail(409, "reward_counted", "Reward already counted")
            state["reward_ids"].append(key)
            event.update(amount=payload["amount"], reward_id=key,
                         levels=award_xp(state, payload["amount"]))
        elif kind == "record_scene":
            key = payload["scene_id"]
            if key in state["scene_ids"]:
                fail(409, "scene_counted", "Scene already counted")
            state["scene_ids"].append(key)
            ch["scene_counter"] += 1
            ceiling = 6 if ch["level"] <= 4 else 7
            milestone = ch["xp_next"] - ch["xp"] if ch["scene_counter"] >= ceiling else 0
            event.update(scene_id=key, cinematic_milestone_xp=milestone,
                         levels=award_xp(state, milestone) if milestone else [])
        return event

    def propose_action(self, owner, campaign_id, action_id, expected_version, kind, payload):
        identifier(action_id, "action_id")
        try:
            integer(expected_version, 1, 1000000000, "expected_version")
        except ValueError as error:
            fail(422, "invalid_version", str(error))
        self._command(kind, payload)
        request = canonical({"action_id": action_id, "expected_version": expected_version,
                             "kind": kind, "payload": payload})
        with self.store.transaction() as db:
            state = self._get(db, owner, campaign_id)
            old = records.get(db, "proposals_v1", {"campaign_id": campaign_id, "action_id": action_id})
            if old:
                if old["request"] != request:
                    fail(409, "idempotency_conflict", "action_id already has different arguments")
                return {"proposal": json.loads(old["preview"]), "committed": old["result"] is not None,
                        "_meta": {"approval_token": old["approval_token"],
                                  "approval_expires_at": old["created_at"] + 900}}
            if state["version"] != expected_version:
                fail(409, "version_conflict", f"Current version is {state['version']}")
            projected = copy.deepcopy(state)
            effect_preview = self._apply(projected, kind, payload, preview=True)
            proposal_id = "proposal-" + uuid.uuid4().hex
            preview = {"id": proposal_id, "campaign_id": campaign_id, "kind": kind,
                       "action_id": action_id, "expected_version": expected_version,
                       "payload": payload, "character_before": state["character"],
                       "character_after": projected["character"],
                       "random_result": "Not rolled until approval" if kind.startswith("roll_") or kind in DEVELOPMENT_OPERATIONS else None,
                       "requires_confirmation": True}
            if kind in DEVELOPMENT_OPERATIONS:
                preview["combat_preview"] = effect_preview
            if kind == "correct_chat_state":
                from .save_history import changes_between
                preview["field_changes"] = changes_between(state, projected, limit=None, text_limit=None)
            token = secrets.token_urlsafe(32)
            created_at = time.time()
            records.insert(db, "proposals_v1", {"id": proposal_id, "campaign_id": campaign_id,
                                               "owner": owner, "action_id": action_id, "request": request,
                                               "preview": canonical(preview), "approval_token": token,
                                               "created_at": created_at, "result": None})
            return {"proposal": preview, "committed": False,
                    "_meta": {"approval_token": token, "approval_expires_at": created_at + 900}}

    def execute_confirmed_action(self, owner, proposal_id, approval_token):
        with self.store.transaction() as db:
            proposal = records.get(db, "proposals_v1", {"id": proposal_id, "owner": owner})
            if proposal is None:
                fail(404, "not_found", "Proposal not found")
            state = self._get(db, owner, proposal["campaign_id"])
            if not isinstance(approval_token, str) or not secrets.compare_digest(
                    proposal["approval_token"], approval_token):
                fail(403, "approval_required", "Approval token is missing or invalid")
            if proposal["result"]:
                return json.loads(proposal["result"])
            if time.time() - proposal["created_at"] > 900:
                fail(409, "proposal_expired", "Proposal expired; review a new proposal")
            request = json.loads(proposal["request"])
            if state["version"] != request["expected_version"]:
                fail(409, "version_conflict", f"Current version is {state['version']}; review again")
            event = self._apply(state, request["kind"], request["payload"])
            state["version"] += 1
            event = self._append(db, state, {**event, "action_id": request["action_id"]})
            records.update(db, "campaigns_v1", {"id": state["id"], "owner": owner},
                           {"version": state["version"], "data": canonical(state)})
            if state.get("mode") == "chat":
                from .chat_game import snapshot
                snapshot(db, state)
            result = {"campaign": public_state(state), "event": safe_event(event)}
            records.update(db, "proposals_v1", {"id": proposal_id}, {"result": canonical(result)})
            return result

    def audit(self, owner, campaign_id, show_rolls=False):
        with self.store.transaction() as db:
            state = self._get(db, owner, campaign_id)
            rows = records.find(db, "events_v1", {"campaign_id": campaign_id}, order="number")
            previous, valid = "0" * 64, True
            events = []
            for number, row in enumerate(rows, 1):
                digest = hashlib.sha256((previous + row["event"]).encode()).hexdigest()
                valid &= row["number"] == number and row["previous_hash"] == previous and row["hash"] == digest
                previous = row["hash"]
                events.append(json.loads(row["event"]))
            valid &= bool(events) and events[-1].get("state_sha256") == state_hash(state)
            valid &= bool(events) and state["last_event"] == events[-1]
            return {"campaign_id": campaign_id, "version": state["version"],
                    "integrity_valid": bool(valid), "event_count": len(events),
                    "events": events if show_rolls else [safe_event(e) for e in events],
                    "raw_rolls_included": show_rolls}

    def dashboard(self, owner, campaign_id=None):
        context = self.campaign_context(owner, campaign_id) if campaign_id else {"campaign": None, "_meta": {}}
        return {"app_version": APP_VERSION, "rules_version": RULES_VERSION,
                "campaigns": self.list_campaigns(owner),
                "campaign": context["campaign"],
                "view_preferences": self.get_view_preferences(owner),
                "_meta": context["_meta"],
                "capabilities": {"operations": [kind for kind in OPERATIONS
                                                if self.enable_combat or kind not in DEVELOPMENT_OPERATIONS],
                                 "sandbox_combat": self.enable_combat, "full_rules_engine": False,
                                 "chat_led_saved_state": True,
                                 "chat_led_character_draft": True, "gm_adjudication": "ChatGPT",
                                 "character_creation": False, "advancement_offers": False,
                                 "model_api_calls": False}}

    def pending_approval(self, owner, campaign_id, *, db=None, state=None):
        if db is None:
            with self.store.transaction() as session:
                return self.pending_approval(owner, campaign_id, db=session)
        if state is None:
            state = self._get(db, owner, campaign_id)
        rows = records.find(db, "proposals_v1", {"campaign_id": campaign_id, "owner": owner, "result": None},
                                order="created_at", descending=True, limit=10)
        for row in rows:
            preview = json.loads(row["preview"])
            if state.get("mode") == "chat" and preview["kind"] in {"confirm_chat_character", "start_chat_adventure"}:
                continue
            if preview["expected_version"] == state["version"]:
                expires_at = row["created_at"] + 900
                approval = {"proposal": preview, "expires_at": expires_at, "expired": time.time() > expires_at}
                if not approval["expired"]:
                    approval["approval_token"] = row["approval_token"]
                return {"approval": approval}
        return {"approval": None}

    def get_view_preferences(self, owner):
        with self.store.transaction() as db:
            row = records.get(db, "ui_preferences_v1", {"owner": owner})
            return json.loads(row["data"]) if row else {"panels": [], "details": [], "hud_hidden": False}

    def set_view_preferences(self, owner, preferences):
        keys = {"panels", "details", "hud_hidden"}
        if type(preferences) is not dict or not keys <= set(preferences) <= keys | {"equipment_tab", "skills_tab", "world_tab", "combat_tab", "scene", "layout", "ambient_motion"}:
            fail(422, "invalid_preferences", "Preferences require panels, details and hud_hidden; display choices are optional")
        if "equipment_tab" in preferences and preferences["equipment_tab"] not in ("equipment", "inventory"):
            fail(422, "invalid_preferences", "equipment_tab must be equipment or inventory")
        if "skills_tab" in preferences and preferences["skills_tab"] not in ("combat", "reactions", "passives", "utility"):
            fail(422, "invalid_preferences", "skills_tab must be combat, reactions, passives or utility")
        if "world_tab" in preferences and preferences["world_tab"] not in ("world", "log"):
            fail(422, "invalid_preferences", "world_tab must be world or log")
        if "combat_tab" in preferences and preferences["combat_tab"] not in ("summons", "combat"):
            fail(422, "invalid_preferences", "combat_tab must be summons or combat")
        if "scene" in preferences and (not isinstance(preferences["scene"], str) or
                                       preferences["scene"] not in SCENE_IDS):
            fail(422, "invalid_preferences", "Unknown reading atmosphere")
        if type(preferences["hud_hidden"]) is not bool:
            fail(422, "invalid_preferences", "hud_hidden must be boolean")
        if "layout" in preferences and (not isinstance(preferences["layout"], str) or
                                         preferences["layout"] not in ("original", "reclaimed", "orrery", "ember")):
            fail(422, "invalid_preferences", "Unknown dashboard layout")
        if "ambient_motion" in preferences and type(preferences["ambient_motion"]) is not bool:
            fail(422, "invalid_preferences", "ambient_motion must be boolean")
        for key, maximum in (("panels", 7), ("details", 200)):
            values = preferences[key]
            if type(values) is not list or len(values) > maximum or any(
                    not isinstance(value, str) or not 1 <= len(value) <= 128 for value in values):
                fail(422, "invalid_preferences", "Invalid expansion preferences")
        with self.store.transaction() as db:
            records.upsert(db, "ui_preferences_v1", {"owner": owner}, {"data": canonical(preferences)})
        return {"view_preferences": preferences}
