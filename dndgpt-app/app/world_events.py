"""One recorded conditional event draw per physical transition; cached regional pools."""
import copy

from .engine import fail

CHANCES = {"safe": 10, "travel": 30, "frontier": 50, "unstable": 70}
CATEGORIES = {"combat": 30, "opportunity": 25, "world": 20, "hazard": 15, "social": 10}
SEVERITIES = {"minor": 50, "moderate": 30, "major": 15, "exceptional": 5}


def valid_id(value):
    return (type(value) is str and 1 <= len(value) <= 48 and
            all(c.isascii() and (c.isalnum() or c in "-_") for c in value))


def validate_pool(pool):
    if type(pool) is not dict or pool.keys() - {"events", "category_weights"}:
        raise ValueError("Event pool needs events and optional precommitted category_weights")
    weights = pool.get("category_weights", CATEGORIES)
    if (type(weights) is not dict or set(weights) != set(CATEGORIES) or
            any(type(v) is not int or not 0 <= v <= 100 for v in weights.values()) or sum(weights.values()) != 100):
        raise ValueError("Event category weights must name all five categories and sum to 100")
    entries = pool.get("events")
    if type(entries) is not list or not 1 <= len(entries) <= 100:
        raise ValueError("Prepare 1..100 contextual event candidates before rolling")
    seen, coverage = set(), set()
    for event in entries:
        if (type(event) is not dict or not valid_id(event.get("id")) or event["id"] in seen or
                event.get("category") not in CATEGORIES or event.get("severity") not in SEVERITIES or
                any(type(event.get(key)) is not str or not 1 <= len(event[key].strip()) <= limit
                    for key, limit in (("title", 160), ("summary", 1400))) or
                type(event.get("repeatable", False)) is not bool):
            raise ValueError("Event candidates need distinct IDs, category, severity, title and summary")
        seen.add(event["id"])
        coverage.add((event["category"], event["severity"]))
    required = {(category, severity) for category, weight in weights.items() if weight for severity in SEVERITIES}
    if not required <= coverage:
        raise ValueError("Prepare every severity for each enabled category; cache this pool for later transitions")
    from .chat_game import bounded_json
    bounded_json(pool)


def weighted_label(draw, weights):
    total = 0
    for label in (CATEGORIES if set(weights) == set(CATEGORIES) else SEVERITIES):
        weight = weights[label]
        total += weight
        if draw <= total:
            return label
    raise ValueError("Event roll outside committed weights")


def draw_event(context, transition_id, pool, pool_action_id, used, dice):
    trigger = dice.roll(100)
    result = {"transition_id": transition_id, "context": context, "chance": CHANCES[context],
              "trigger_roll": trigger, "pool_action_id": pool_action_id, "outcome": "no_event"}
    if trigger > CHANCES[context]:
        return result
    category_roll, severity_roll = dice.roll(100), dice.roll(100)
    category = weighted_label(category_roll, pool.get("category_weights", CATEGORIES))
    severity = weighted_label(severity_roll, SEVERITIES)
    choices = [entry for entry in pool["events"] if entry["category"] == category and
               entry["severity"] == severity and (entry.get("repeatable") or entry["id"] not in used)]
    result.update(category=category, severity=severity, category_roll=category_roll, severity_roll=severity_roll)
    if not choices:
        result.update(outcome="no_applicable_event", reason="This prepared cell is exhausted; refresh future possibilities without rerolling this transition")
        return result
    index = dice.roll(len(choices)) if len(choices) > 1 else 1
    result.update(outcome="event", selection_roll=index, selected=copy.deepcopy(choices[index - 1]))
    return result


def apply_tracking(before, state, changes, receipt=None):
    transition = changes.get("event_transition")
    moved = (before.get("phase") == "adventure" and
             (before.get("current_location") != state.get("current_location") or
              state.get("fictional_time_seconds", 0) - before.get("fictional_time_seconds", 0) >= 1800))
    if transition is None:
        if moved:
            tracking = state.setdefault("event_tracking", {})
            tracking.update(check_due=True, due_reason="Location changed or substantial time elapsed; classify the transition")
        return
    if (type(transition) is not dict or transition.keys() - {"id", "context", "eligible", "reason", "roll_action_id"} or
            not valid_id(transition.get("id")) or type(transition.get("eligible")) is not bool):
        fail(422, "invalid_event_transition", "Use id, eligible, context and roll_action_id, or a reason for an ineligible transition")
    tracking = state.setdefault("event_tracking", {})
    if transition["eligible"]:
        rows = [row["result"] for row in (receipt or {}).get("results", []) if row["kind"] == "world_event"]
        if (not rows or rows[0]["transition_id"] != transition["id"] or
                rows[0]["context"] != transition.get("context")):
            fail(422, "event_receipt_required", "Use the recorded world_event receipt for this transition and context")
        event = copy.deepcopy(rows[0])
        event.pop("_event_pool", None)
        event["roll_action_id"] = transition["roll_action_id"]
        if transition["id"] in tracking.get("checked_ids", []):
            fail(409, "event_transition_already_saved", "This transition is already recorded; do not apply it twice")
        tracking.setdefault("checked_ids", []).append(transition["id"])
        selected = event.get("selected")
        if selected and not selected.get("repeatable"):
            used = tracking.setdefault("used_events", {}).setdefault(event["pool_action_id"], [])
            if selected["id"] in used:
                fail(409, "event_already_resolved", "This one-time event was already used; preserve this roll and review the transition")
            used.append(selected["id"])
        tracking["last_check"] = event
        tracking["history"] = (tracking.get("history", []) + [event])[-8:]
    elif type(transition.get("reason")) is not str or not 1 <= len(transition["reason"].strip()) <= 400:
        fail(422, "invalid_event_transition", "Record why this transition has no eligible event check")
    tracking.update(last_transition=copy.deepcopy(transition), check_due=False)
    tracking.pop("due_reason", None)
