"""Owner-scoped, resumable campaign deletion with explicit confirmation."""
import hashlib
import json
import secrets
import time

from . import records
from .engine import fail, identifier
from .storage import canonical


class CampaignLifecycle:
    PREVIEW_TTL_SECONDS = 900
    BATCH_SIZE = 20
    CHILD_TABLES = ("proposals_v1", "events_v1", "chat_updates_v1",
                    "chat_versions_v1", "game_rolls_v1", "gallery_entries_v1",
                    "gallery_assets_v1", "gallery_actions_v1")

    def __init__(self, engine):
        self.engine = engine
        self.store = engine.store

    @staticmethod
    def _key(owner, campaign_id):
        return {"owner": owner, "campaign_id": campaign_id}

    @staticmethod
    def _data(row):
        try:
            value = json.loads(row["data"])
        except (KeyError, TypeError, json.JSONDecodeError):
            fail(503, "storage_integrity", "Campaign deletion record is invalid")
        if not isinstance(value, dict):
            fail(503, "storage_integrity", "Campaign deletion record is invalid")
        return value

    @staticmethod
    def _save(db, owner, campaign_id, data):
        records.update(db, "campaign_deletions_v1",
                       {"owner": owner, "campaign_id": campaign_id},
                       {"data": canonical(data)})

    @staticmethod
    def _public(data):
        return {"campaign_id": data["campaign_id"], "campaign_name": data["campaign_name"],
                "expected_version": data["expected_version"], "status": data["phase"],
                "removed_records": data.get("removed_records", {}),
                "compacted_receipts": data.get("compacted_receipts", 0),
                "cleanup_pending": data["phase"] == "deleting",
                "deleted": data["phase"] == "complete"}

    def preview_delete(self, owner, campaign_id, expected_version):
        identifier(campaign_id, "campaign_id")
        if type(expected_version) is not int or expected_version < 1:
            fail(422, "invalid_version", "expected_version must be a positive integer")
        token = secrets.token_urlsafe(32)
        with self.store.transaction() as db:
            state = self.engine._get(db, owner, campaign_id)
            if state["version"] != expected_version:
                fail(409, "version_conflict", f"Current version is {state['version']}; read before previewing deletion")
            key = self._key(owner, campaign_id)
            prior = records.get(db, "campaign_deletions_v1", key)
            if prior:
                data = self._data(prior)
                if data["phase"] == "deleting":
                    fail(409, "deletion_in_progress", "Campaign deletion is already in progress; continue the existing deletion")
                if data["phase"] == "complete":
                    fail(410, "campaign_deleted", "This campaign has already been deleted")
            data = {"campaign_id": campaign_id, "campaign_name": state["name"],
                    "expected_version": expected_version, "phase": "preview",
                    "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                    "expires_at": time.time() + self.PREVIEW_TTL_SECONDS,
                    "table_index": 0, "legacy_cursor": None,
                    "removed_records": {}, "compacted_receipts": 0}
            if prior:
                self._save(db, owner, campaign_id, data)
            else:
                records.insert(db, "campaign_deletions_v1",
                               {**key, "data": canonical(data)})
            return {**self._public(data), "confirmation_token": token,
                    "expires_in_seconds": self.PREVIEW_TTL_SECONDS,
                    "will_remove": ["this campaign", "its proposals, event history, saved versions, and chat updates",
                                    "detailed data from roll receipts explicitly linked to this campaign",
                                    "its Gallery images, captions, credits and media receipts"],
                    "will_retain": ["other campaigns", "account preferences", "unlinked historical roll receipts",
                                    "a small deletion marker and compact idempotency receipts so stale retries cannot restore saves or reroll dice"]}

    def delete(self, owner, campaign_id, expected_version, confirmation_token, confirm_permanent):
        identifier(campaign_id, "campaign_id")
        if type(expected_version) is not int or expected_version < 1:
            fail(422, "invalid_version", "expected_version must be a positive integer")
        if type(confirm_permanent) is not bool or confirm_permanent is not True:
            fail(422, "confirmation_required", "confirm_permanent must be true after the user explicitly approves permanent deletion")
        if not isinstance(confirmation_token, str) or not 20 <= len(confirmation_token) <= 256:
            fail(422, "invalid_confirmation", "A valid deletion preview confirmation token is required")
        token_hash = hashlib.sha256(confirmation_token.encode()).hexdigest()

        with self.store.transaction() as db:
            key = self._key(owner, campaign_id)
            row = records.get(db, "campaign_deletions_v1", key)
            if row is None:
                fail(409, "deletion_preview_required", "Preview this campaign deletion before confirming it")
            data = self._data(row)
            if data.get("expected_version") != expected_version:
                fail(409, "version_conflict", "The confirmation does not match the previewed campaign version")
            if not secrets.compare_digest(data.get("token_sha256", ""), token_hash):
                fail(403, "invalid_confirmation", "The deletion confirmation token is invalid")
            if data["phase"] == "complete":
                return self._public(data)
            if data["phase"] == "preview":
                if time.time() > data.get("expires_at", 0):
                    fail(410, "preview_expired", "Deletion preview expired; read the campaign and preview again")
                state = self.engine._get(db, owner, campaign_id)
                if state["version"] != expected_version:
                    fail(409, "version_conflict", f"Current version is {state['version']}; preview deletion again")
                campaign = records.get(db, "campaigns_v1", {"id": campaign_id, "owner": owner})
                data["phase"] = "deleting"
                data["started_at"] = time.time()
                self._save(db, owner, campaign_id, data)
                # Lock the campaign row in this transaction so an earlier in-flight
                # writer cannot commit after the deletion tombstone becomes active.
                records.update(db, "campaigns_v1", {"id": campaign_id, "owner": owner},
                               {"data": campaign["data"]})
            elif data["phase"] != "deleting":
                fail(503, "storage_integrity", "Campaign deletion has an unknown phase")

            budget = self.BATCH_SIZE
            index = data.get("table_index", 0)
            while budget > 0 and index < len(self.CHILD_TABLES):
                table = self.CHILD_TABLES[index]
                where = {"campaign_id": campaign_id}
                if table == "proposals_v1" or table.startswith("gallery_"):
                    where["owner"] = owner
                rows = records.find(db, table, where, limit=budget)
                if rows:
                    batch_limit = budget
                    for item in rows:
                        if table == "game_rolls_v1":
                            records.update(db, table,
                                           {"owner": item["owner"], "action_id": item["action_id"]},
                                           {"campaign_id": "", "request": "deleted",
                                            "result": canonical({"_campaign_deleted": True,
                                                                 "campaign_id": campaign_id})})
                            data["compacted_receipts"] += 1
                        else:
                            identity = {field: item[field] for field in records.KEYS[table]}
                            records.delete(db, table, identity)
                            data["removed_records"][table] = data["removed_records"].get(table, 0) + 1
                    budget -= len(rows)
                    if len(rows) == batch_limit:
                        break
                index += 1
                data["table_index"] = index

            if index == len(self.CHILD_TABLES) and budget > 0:
                linked_limit = budget
                linked = records.find(db, "creations_v1",
                                      {"owner": owner, "campaign_id": campaign_id}, limit=linked_limit)
                for item in linked:
                    self._compact_creation(db, owner, campaign_id, item)
                budget -= len(linked)
                if len(linked) < linked_limit and budget > 0:
                    cursor = data.get("legacy_cursor")
                    legacy_limit = budget
                    legacy = records.find(db, "creations_v1", {"owner": owner},
                                          order="action_id", limit=legacy_limit,
                                          minimum={"action_id": cursor} if cursor else None)
                    for item in legacy:
                        if item.get("campaign_id") == campaign_id:
                            self._compact_creation(db, owner, campaign_id, item)
                        else:
                            try:
                                result = json.loads(item.get("result", "{}"))
                            except (TypeError, json.JSONDecodeError):
                                result = {}
                            if result.get("id") == campaign_id:
                                self._compact_creation(db, owner, campaign_id, item)
                    if legacy:
                        data["legacy_cursor"] = legacy[-1]["action_id"]
                    budget -= len(legacy)
                    if len(legacy) < legacy_limit:
                        index += 1
                        data["table_index"] = index
                elif len(linked) == linked_limit:
                    data["table_index"] = index

            if index > len(self.CHILD_TABLES):
                campaign = records.get(db, "campaigns_v1", {"id": campaign_id, "owner": owner})
                if campaign is not None:
                    records.delete(db, "campaigns_v1", {"id": campaign_id})
                    data["removed_records"]["campaigns_v1"] = 1
                data = {"campaign_id": campaign_id, "campaign_name": data["campaign_name"],
                        "expected_version": expected_version, "phase": "complete",
                        "token_sha256": token_hash,
                        "removed_records": data.get("removed_records", {}),
                        "compacted_receipts": data.get("compacted_receipts", 0),
                        "completed_at": time.time()}
            self._save(db, owner, campaign_id, data)
            return self._public(data)

    @staticmethod
    def _compact_creation(db, owner, campaign_id, item):
        records.update(db, "creations_v1", {"owner": owner, "action_id": item["action_id"]},
                       {"campaign_id": "", "result": canonical({"_campaign_deleted": True,
                                                                    "campaign_id": campaign_id})})
