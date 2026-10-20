"""Owned, paged history and readable public changes. Never used on the turn path."""
import json
import re

from . import records
from .chat_game import number

PRIVATE = re.compile(r"secret|private|gm_only|gm_notes|token|receipt|raw_roll|sha256", re.I)
IGNORED = {"id", "version", "last_event", "rules_check", "resume_brief", "rarity_candidates"}
AREAS = {"character", "current_location", "fictional_time_seconds", "paused", "phase",
         "level_up_freeze", "abilities", "conditions", "summons", "inventory", "equipment",
         "quest_log", "continuity", "funds", "supplies", "name", "world", "world_log",
         "notes", "opening_preview", "creation", "advancement", "generation_ledger"}


def visible(value):
    if isinstance(value, dict):
        if value.get("hidden") is True or value.get("gm_only") is True or value.get("revealed") is False:
            return None
        return {key: visible(item) for key, item in value.items()
                if key not in IGNORED and not PRIVATE.search(key)}
    if isinstance(value, list):
        return [clean for item in value if (clean := visible(item)) is not None]
    return value


def changes_between(before, after, limit=100, text_limit=1200):
    changes = []
    withheld = []

    def walk(left, right, path):
        if left == right:
            return
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(left.keys() | right.keys()):
                walk(left.get(key), right.get(key), [*path, key])
        else:
            def compact(value):
                text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                return {"text": text if text_limit is None else text[:text_limit],
                        "truncated": text_limit is not None and len(text) > text_limit}
            changes.append({"path": ".".join(path),
                            "label": " › ".join(key.replace("_", " ").capitalize() for key in path),
                            "before": compact(left), "after": compact(right)})

    for key in sorted(AREAS):
        left, right = visible(before.get(key)), visible(after.get(key))
        if before.get(key) != after.get(key) and left == right:
            withheld.append(key)
        walk(left, right, [key])
    return {"changes": changes[:limit], "change_count": len(changes),
            "truncated": limit is not None and len(changes) > limit,
            "withheld_sections": withheld}


class SaveHistory:
    def __init__(self, engine):
        self.engine, self.store = engine, engine.store

    def list(self, owner, campaign_id, before=None, limit=20):
        number(limit, "limit", 1, 30)
        if before is not None:
            number(before, "before", 1)
        with self.store.transaction() as db:
            current = self.engine._get(db, owner, campaign_id)
            rows = records.find(db, "chat_versions_v1", {"campaign_id": campaign_id},
                                order="version", descending=True, limit=limit + 1,
                                maximum={"version": before - 1} if before is not None else None)
            entries = []
            for row in rows[:limit]:
                state = json.loads(row["data"])
                event = state.get("last_event") or {}
                entries.append({"version": row["version"], "utc": event.get("utc"),
                                "summary": event.get("summary") or event.get("kind", "Saved state").replace("_", " "),
                                "location": state.get("current_location", ""),
                                "fictional_time_seconds": state["fictional_time_seconds"]})
            return {"campaign_id": campaign_id, "current_version": current["version"], "versions": entries,
                    "next_before": entries[-1]["version"] if len(rows) > limit else None}

    def compare(self, owner, campaign_id, version):
        from .engine import fail
        number(version, "version", 1)
        with self.store.transaction() as db:
            current = self.engine._get(db, owner, campaign_id)
            row = records.get(db, "chat_versions_v1", {"campaign_id": campaign_id, "version": version})
            if row is None:
                fail(404, "not_found", "Saved version not found")
            previous = records.find(db, "chat_versions_v1", {"campaign_id": campaign_id},
                                    order="version", descending=True, limit=1, maximum={"version": version - 1})
            saved = json.loads(row["data"])
            base = json.loads(previous[0]["data"]) if previous else {}
            return {"historical": True, "campaign_id": campaign_id, "version": version,
                    "previous_version": previous[0]["version"] if previous else None,
                    "current_version": current["version"], **changes_between(base, saved)}
