"""Bounded continuity derived from committed state, without extra storage reads."""
import copy

TEXT_LIMITS = {"scene": 600, "last_player_intent": 600, "last_action": 600,
               "outcome": 600, "pending_decision": 600, "transition": 600}
LIST_FIELDS = {"unresolved_threads", "npc_commitments"}


def validate_continuity(value):
    from .engine import fail
    if type(value) is not dict or value.keys() - (TEXT_LIMITS.keys() | LIST_FIELDS):
        fail(422, "invalid_continuity", "Unknown continuity field")
    for key, content in value.items():
        if key in TEXT_LIMITS:
            valid = type(content) is str and len(content) <= TEXT_LIMITS[key]
        else:
            valid = (type(content) is list and len(content) <= 8 and
                     all(type(item) is str and len(item) <= 240 for item in content))
        if not valid:
            fail(422, "invalid_continuity", "Continuity needs short text and at most eight short entries per list")


def short(value, limit=240):
    return value[:limit] if isinstance(value, str) else ""


def resume_brief(state):
    note = state.get("continuity", {})
    character = state.get("character", {})
    event = state.get("last_event") or {}
    quests = [row for row in state.get("quest_log", []) if isinstance(row, dict) and
              str(row.get("status", "active")).lower() not in {"completed", "failed", "abandoned"}]
    return {"campaign_id": state["id"], "version": state["version"],
            "name": state.get("name", ""), "phase": state.get("phase"),
            "paused": state["paused"], "level_up_freeze": state["level_up_freeze"],
            "current_location": short(state.get("current_location")),
            "fictional_time_seconds": state["fictional_time_seconds"],
            "scene": short(note.get("scene")),
            "last_player_intent": short(note.get("last_player_intent")),
            "last_action": short(note.get("last_action")),
            "outcome": short(note.get("outcome")) or short(event.get("summary")),
            "pending_decision": short(note.get("pending_decision")),
            "transition": short(note.get("transition")),
            "unresolved_threads": [short(item, 160) for item in note.get("unresolved_threads", [])[:4]],
            "npc_commitments": [short(item, 160) for item in note.get("npc_commitments", [])[:4]],
            "additional_threads": max(0, len(note.get("unresolved_threads", [])) - 4),
            "additional_commitments": max(0, len(note.get("npc_commitments", [])) - 4),
            "excerpted_fields": [key for key in TEXT_LIMITS if len(note.get(key, "")) > 240],
            "active_quests": [short(row.get("name") or row.get("title"), 120) for row in quests[:3]],
            "resources": {key: character[key] for key in ("hp", "hp_max", "mp", "mp_max") if key in character},
            "read_only": True, "continuation_requires_player_action": True,
            "missing_continuity": not bool(note)}


def model_view(state, view="full"):
    """Full mechanics stay available; old logs and world articles are opt-in."""
    from .engine import fail
    if view not in {"full", "turn", "resume"}:
        fail(422, "invalid_campaign_view", "Choose full, turn or resume")
    if view == "resume":
        return {"id": state["id"], "version": state["version"], "resume_brief": resume_brief(state)}
    result = copy.deepcopy(state)
    if view == "turn":
        omitted = {}
        for key, keep in (("world_log", 3), ("generation_ledger", 3)):
            rows = result.get(key, [])
            if len(rows) > keep:
                omitted[key] = len(rows) - keep
                result[key] = rows[-keep:]
        if result.get("world"):
            result["world"] = {"summary": short(result["world"].get("summary"), 1000)}
            omitted["world"] = "Use view=full for established world articles and details"
        result["view"] = "turn"
        result["omitted"] = omitted
    return result
