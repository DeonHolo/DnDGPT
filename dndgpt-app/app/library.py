"""Owned, versioned reusable content. Campaigns take copies, never live links."""
import copy
import json
import uuid

from . import records
from .engine import fail, identifier
from .storage import canonical


class Library:
    def __init__(self, engine):
        self.engine, self.store = engine, engine.store

    def _get(self, db, owner, entry_id, version=None):
        row = records.get(db, "library_entries_v1", {"id": entry_id, "owner": owner})
        if row is None:
            fail(404, "not_found", "Library entry not found")
        if version is not None:
            row = records.get(db, "library_versions_v1", {"id": entry_id, "owner": owner, "version": version})
            if row is None:
                fail(404, "not_found", "Library version not found")
        return json.loads(row["data"])

    def get(self, owner, entry_id, version=None):
        with self.store.transaction() as db:
            return self._get(db, owner, entry_id, version)

    def list(self, owner, kind=None, game_id=None):
        with self.store.transaction() as db:
            entries = [json.loads(row["data"]) for row in records.find(db, "library_entries_v1", {"owner": owner})]
        return [self.summary(entry) for entry in entries
                if (kind is None or entry["kind"] == kind) and (game_id is None or entry["game_id"] == game_id)]

    @staticmethod
    def summary(entry):
        data = entry["content"]
        return {key: copy.deepcopy(entry[key]) for key in ("id", "kind", "game_id", "version", "name")} | {
            "level": data.get("level"), "class_name": data.get("class_name"),
            "species": data.get("species"), "setting": data.get("setting"),
            "adventure_type": data.get("adventure_type"), "summary": data.get("summary", "")}

    def save(self, owner, action_id, kind, content, entry_id=None, expected_version=None):
        from .dnd5e import GAME, normalize_sheet
        from .adventure_library import validate_adventure
        identifier(action_id, "action_id")
        if expected_version is not None and (type(expected_version) is not int or expected_version < 1):
            fail(422, "invalid_library_version", "Use the integer version returned by the library")
        if kind not in {"character", "adventure"}:
            fail(422, "invalid_library_kind", "Choose character or adventure")
        if kind == "character" and type(content) is dict and not content.get("id"):
            content = {**content, "id": "hero-" + uuid.uuid5(uuid.NAMESPACE_URL, owner+action_id).hex}
        clean = normalize_sheet(content) if kind == "character" else validate_adventure(content)
        request = canonical({"kind": kind, "content": clean, "id": entry_id, "expected_version": expected_version})
        if len(request.encode()) > 250000:
            fail(422, "library_too_large", "Split this source into an adventure pack of at most 250000 bytes")
        with self.store.transaction() as db:
            prior = records.get(db, "library_actions_v1", {"owner": owner, "action_id": action_id})
            if prior:
                if prior["request"] != request:
                    fail(409, "idempotency_conflict", "Reuse the original library save arguments")
                return json.loads(prior["result"])
            version = 1
            if entry_id:
                previous = self._get(db, owner, entry_id)
                if previous["kind"] != kind or previous["version"] != expected_version:
                    fail(409, "version_conflict", "Read the latest library version before editing")
                version = previous["version"] + 1
            elif expected_version is not None:
                fail(422, "invalid_library_version", "A new entry starts without an expected version")
            entry_id = entry_id or "library-" + uuid.uuid4().hex
            entry = {"id": entry_id, "kind": kind, "game_id": GAME, "version": version,
                     "name": clean.get("name", clean.get("title", "Adventure")), "content": clean}
            records.upsert(db, "library_entries_v1", {"id": entry_id, "owner": owner},
                           {"version": version, "data": canonical(entry)})
            records.insert(db, "library_versions_v1", {"id": entry_id, "owner": owner,
                           "version": version, "data": canonical(entry)})
            result = {"entry": entry, "saved": True}
            records.insert(db, "library_actions_v1", {"owner": owner, "action_id": action_id,
                           "request": request, "result": canonical(result)})
            return result

