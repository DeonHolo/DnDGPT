"""Evidence-backed campaign changes, applied inside the normal saved turn."""
import copy
import hashlib

from .storage import canonical

TACTICS = {"focus_summoner", "use_cover", "area_pressure", "disrupt_support", "flank", "retreat"}
STANCES = {"trusted", "friendly", "neutral", "wary", "hostile"}
KINDS = {"observation", "relationship", "commitment", "place_change", "quest_aftermath", "development"}


def require(condition, message):
    if not condition:
        from .engine import fail
        fail(422, "invalid_campaign_life", message)


def text(value, maximum=600):
    return type(value) is str and bool(value.strip()) and len(value) <= maximum


def rows(value, maximum=100):
    require(type(value) is list and len(value) <= maximum and all(type(v) is dict for v in value),
            "Use a bounded list of records")
    ids = [v.get("id") for v in value]
    require(all(text(v, 128) for v in ids) and len(set(ids)) == len(ids), "Records need distinct stable IDs")
    return value


def initial():
    return {"schema": 1, "actors": [], "places": [], "aftermath": [], "developments": [],
            "recent_events": [], "event_ledger": {}, "source_receipts": {}, "pacing": {"mode": "scene"}}


def upsert_registry(life, patch):
    for group in ("actors", "places"):
        entries = rows(patch.get(group, []), 40)
        current = {r["id"]: r for r in life[group]}
        for entry in entries:
            allowed = ({"id", "name", "kind", "description", "traits", "goal", "preferred_approach", "entity_id"}
                       if group == "actors" else {"id", "name", "kind", "description", "links", "entity_id"})
            require(not entry.keys() - allowed, "Registry edits cannot rewrite saved events or relationships")
            old = current.get(entry["id"], {})
            item = {**old, **copy.deepcopy(entry)}
            require(text(item.get("name"), 160) and text(item.get("description", item.get("name"))),
                    "People and places need a name and short description")
            valid_kinds = {"rival", "companion", "general", "faction", "npc"} if group == "actors" else {"location", "holding", "front"}
            require(item.get("kind") in valid_kinds, "Choose a recorded person or place kind")
            require(not old or old["kind"] == item["kind"], "Keep an established record's kind")
            for key in ("goal", "preferred_approach", "entity_id"):
                if key in item:
                    require(text(item[key], 128 if key == "entity_id" else 600), "Use short text for actor details")
            if group == "actors":
                traits = item.get("traits", [])
                require(type(traits) is list and len(traits) <= 5 and all(text(t, 120) for t in traits), "Use at most five short traits")
                item.setdefault("observations", [])
                item.setdefault("commitments", [])
                item.setdefault("relationship", {"stance": "neutral", "reason": "No relationship change recorded."})
            else:
                links = item.get("links", [])
                require(type(links) is list and len(links) <= 20 and all(text(v, 128) for v in links) and
                        len(set(links)) == len(links) and item["id"] not in links, "Routes need distinct other place IDs")
                item.setdefault("features", [])
            current[item["id"]] = item
        require(len(current) <= 200, "Keep at most 200 people or places in the current record")
        life[group] = list(current.values())
    known = {r["id"] for r in life["places"]}
    require(all(set(p.get("links", [])) <= known for p in life["places"]), "Routes must refer to known saved places")


def apply_pacing(life, patch, before, state):
    if "pacing" not in patch:
        return
    p = patch["pacing"]
    require(type(p) is dict and not p.keys() - {"mode", "objective", "authorized_until", "stop_reason"}, "Unknown pacing field")
    require(p.get("mode") in {"scene", "journey", "expedition"}, "Choose scene, journey or expedition pacing")
    if p["mode"] != "scene":
        end = p.get("authorized_until")
        start = before["fictional_time_seconds"]
        require(text(p.get("objective")) and type(end) is int and start <= end <= start + 7 * 86400,
                "A journey or expedition needs a player-authorized objective and a horizon of at most seven fictional days")
        require(state["fictional_time_seconds"] <= end, "Stop at the authorized fictional-time horizon")
    if "stop_reason" in p:
        require(text(p["stop_reason"]), "Record why the next decision needs the player")
    life["pacing"] = copy.deepcopy(p)


def reconcile_pacing(life, before, state, correction=False):
    p = life["pacing"]
    if p["mode"] == "scene":
        return
    if not correction:
        require(state["fictional_time_seconds"] <= p["authorized_until"], "Stop at the authorized fictional-time horizon or save the player's new pacing order")
    pending = state.get("continuity", {}).get("pending_decision", "")
    previous = before.get("continuity", {}).get("pending_decision", "")
    if p.get("stop_reason") or state["fictional_time_seconds"] >= p["authorized_until"] or pending and pending != previous:
        life["pacing"] = {"mode": "scene", "stop_reason": p.get("stop_reason") or pending or "The planned fictional-time horizon has been reached."}


def sources(state):
    result = {r["id"]: r for r in state.get("world_log", [])}
    result.update({r["id"]: r for r in state.get("quest_log", []) if r.get("status") in {"completed", "failed", "abandoned"}})
    return result


def evidence_hash(source):
    value = copy.deepcopy(source)
    value.pop("known_to_player", None)
    if value.get("quest_schema") == 1:
        # Contract collection and optional bonus completion can follow quest closure.
        value.pop("reward_status", None)
        value.pop("progress_note", None)
        if type(value.get("contract_payment")) is dict:
            value["contract_payment"].pop("status", None)
        for objective in value.get("objectives", []):
            objective.pop("status", None)
            objective.pop("current", None)
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def apply_event(life, event, before, state, evidence, correction=False):
    require(not event.keys() - {"id", "kind", "subject_id", "summary", "source_id", "known_to_player",
                               "memory_id", "tactic", "stance", "commitment_id", "status", "feature", "controller", "quest_id"},
            "Unknown campaign event field")
    require(event.get("kind") in KINDS and text(event.get("subject_id"), 128) and text(event.get("summary")) and
            text(event.get("source_id"), 128), "Events need a kind, subject, summary and saved evidence ID")
    require(type(event.get("known_to_player", True)) is bool, "known_to_player must be boolean")
    source = evidence.get(event["source_id"])
    require(source is not None, "Save the source world-log event or closed quest in this batch or an earlier save")
    kind, subject = event["kind"], event["subject_id"]
    actors = {r["id"]: r for r in life["actors"]}
    places = {r["id"]: r for r in life["places"]}
    if kind in {"observation", "relationship", "commitment"}:
        actor = actors.get(subject)
        require(actor is not None, "The event needs a saved person or faction")
        if kind == "observation":
            witnesses = source.get("witnesses", [])
            require(type(witnesses) is list and (subject in witnesses or
                    actor.get("entity_id") is not None and actor["entity_id"] in witnesses),
                    "Learning requires a saved witness or report recipient on its source event")
            require(text(event.get("memory_id"), 128), "Observations need a stable memory ID")
            if "tactic" in event:
                require(event["tactic"] in TACTICS, "Choose an observed tactical response")
            memories = {m["id"]: m for m in actor["observations"]}
            old = memories.get(event["memory_id"])
            if old and not correction:
                require(old["summary"] == event["summary"] and old.get("tactic") == event.get("tactic"), "A remembered fact keeps its identity")
            memories[event["memory_id"]] = {"id": event["memory_id"], "summary": event["summary"],
                "tactic": event.get("tactic"), "first_source_id": old["first_source_id"] if old else event["source_id"],
                "source_id": event["source_id"], "known_to_player": event.get("known_to_player", True),
                "observations": old["observations"] + 1 if old else 1}
            require(len(memories) <= 100, "Keep at most 100 distinct observations per actor")
            actor["observations"] = list(memories.values())
        elif kind == "relationship":
            require(event.get("stance") in STANCES, "Choose a relationship stance")
            actor["relationship"] = {"stance": event["stance"], "reason": event["summary"], "source_id": event["source_id"],
                                     "known_to_player": event.get("known_to_player", True)}
        else:
            require(text(event.get("commitment_id"), 128) and event.get("status") in {"open", "fulfilled", "broken"}, "Commitments need an ID and status")
            promises = {p["id"]: p for p in actor["commitments"]}
            old = promises.get(event["commitment_id"])
            require(correction or not old or old["text"] == event["summary"], "Preserve the recorded promise")
            require(correction or not old or old["status"] == "open" or old["status"] == event["status"], "A resolved promise stays resolved")
            promises[event["commitment_id"]] = {"id": event["commitment_id"], "text": event["summary"], "status": event["status"],
                "source_id": event["source_id"], "known_to_player": event.get("known_to_player", True)}
            require(len(promises) <= 100, "Keep at most 100 commitments per actor")
            actor["commitments"] = list(promises.values())
    elif kind == "place_change":
        place = places.get(subject)
        require(place is not None and event.get("known_to_player", True), "Record changes to a known saved place")
        require("feature" in event or "controller" in event, "A lasting change needs an actual feature or controller")
        if "feature" in event:
            feature = event["feature"]
            require(type(feature) is dict and set(feature) == {"id", "name", "description"} and text(feature["id"], 128) and
                    text(feature["name"], 160) and text(feature["description"]), "A place feature needs an ID, name and description")
            features = {f["id"]: f for f in place["features"]}
            features[feature["id"]] = {**copy.deepcopy(feature), "source_id": event["source_id"]}
            require(len(features) <= 100, "Keep at most 100 current features per place")
            place["features"] = list(features.values())
        if "controller" in event:
            require(text(event["controller"], 160), "Record the actual controller")
            place["controller"] = event["controller"]
        place["last_change"] = event["summary"]
    elif kind == "quest_aftermath":
        quest = next((q for q in state.get("quest_log", []) if q["id"] == event.get("quest_id")), None)
        require(quest is not None and quest.get("status") in {"completed", "failed", "abandoned"}, "Resolve the quest before recording its aftermath")
        require(event["source_id"] == quest["id"], "Quest aftermath must cite the closed quest")
        require(not any(a["quest_id"] == quest["id"] for a in life["aftermath"]), "This quest already has its aftermath; keep new events separate")
        require(subject in places or subject in actors, "Link aftermath to an actual known person or place")
        require(event.get("known_to_player", True), "Quest aftermath is player-facing")
        life["aftermath"].append({"id": event["id"], "quest_id": quest["id"], "subject_id": subject, "summary": event["summary"]})
    else:
        def owned(s):
            sovereignty = s.get("sovereignty", {})
            return {r["id"]: r for key in ("abilities", "summons") for r in s.get(key, [])} | {
                r["id"]: r for key in ("commanders", "formations") for r in sovereignty.get(key, [])
                if r.get("side") != "enemy"}
        old, current = owned(before).get(subject), owned(state).get(subject)
        require(current is not None, "Development belongs to an actual owned power, companion, commander or formation")
        def mechanics(record):
            return {k: v for k, v in (record or {}).items() if k not in {"xp", "xp_total", "level", "veterancy", "status", "hp", "strength", "morale"}}
        require(mechanics(old) != mechanics(current), "Record an acquired capability or role change, not only numerical XP")
        require(event.get("known_to_player", True), "Acquired development is player-facing")
        life["developments"].append({"id": event["id"], "subject_id": subject, "summary": event["summary"], "source_id": event["source_id"]})


def apply_life(before, state, changes, correction=False):
    patch = changes.get("life_updates")
    previous = before.get("campaign_life")
    if previous:
        previous = copy.deepcopy(previous)
        current_sources = sources(state)
        for identity, receipt in previous.get("source_receipts", {}).items():
            if identity in current_sources:
                digest = evidence_hash(current_sources[identity])
                if correction:
                    receipt.update(sha256=digest, version=before["version"] + 1)
                else:
                    require(digest == receipt["sha256"], "Use a reviewed correction to rewrite evidence already cited by campaign memory")
    if patch is None:
        if previous:
            reconcile_pacing(previous, before, state, correction)
            state["campaign_life"] = previous
        return
    require(type(patch) is dict and not patch.keys() - {"actors", "places", "events", "pacing"}, "Unknown campaign-life update")
    life = previous or initial()
    life.setdefault("event_ledger", {})
    life.setdefault("source_receipts", {})
    upsert_registry(life, patch)
    apply_pacing(life, patch, before, state)
    reconcile_pacing(life, before, state, correction)
    evidence = sources(state)
    for event in rows(patch.get("events", []), 30):
        event = copy.deepcopy(event)
        if event.get("kind") == "observation":
            event.setdefault("known_to_player", False)
        digest = hashlib.sha256(canonical(event).encode()).hexdigest()
        prior = life["event_ledger"].get(event["id"])
        if prior is not None:
            require(prior == digest, "An event ID already records a different outcome")
            continue
        apply_event(life, event, before, state, evidence, correction)
        source_id = event["source_id"]
        life["source_receipts"][source_id] = {"sha256": evidence_hash(evidence[source_id]),
                                               "version": before["version"] + 1}
        life["event_ledger"][event["id"]] = digest
        life["recent_events"].append({**copy.deepcopy(event), "version": before["version"] + 1,
                                      "fictional_time_seconds": state["fictional_time_seconds"]})
    require(len(life["event_ledger"]) <= 10000, "This campaign reached its detailed event receipt limit")
    life["recent_events"] = life["recent_events"][-30:]
    state["campaign_life"] = life


def validate_snapshot(life):
    require(type(life) is dict and set(life) == set(initial()) and life.get("schema") == 1,
            "Unsupported saved campaign-life schema")
    registry = initial()
    for group in ("actors", "places"):
        rows(life[group], 200)
    # Validate registry records in batches without allowing historical fields as edits.
    for group in ("actors", "places"):
        fields = ({"id", "name", "kind", "description", "traits", "goal", "preferred_approach", "entity_id"}
                  if group == "actors" else {"id", "name", "kind", "description", "links", "entity_id"})
        for record in life[group]:
            require(not record.keys() - (fields | ({"observations", "commitments", "relationship"} if group == "actors" else {"features", "controller", "last_change"})), "Unknown saved registry field")
    seeds = {group: [{k: v for k, v in r.items() if k in ({"id", "name", "kind", "description", "traits", "goal", "preferred_approach", "entity_id"} if group == "actors" else {"id", "name", "kind", "description", "entity_id"})} for r in life[group]] for group in ("actors", "places")}
    for group in ("actors", "places"):
        for at in range(0, len(seeds[group]), 40):
            upsert_registry(registry, {group: seeds[group][at:at+40]})
    place_ids = {p["id"] for p in life["places"]}
    for place in life["places"]:
        links = place.get("links", [])
        require(type(links) is list and len(links) <= 20 and all(text(v, 128) for v in links) and
                set(links) <= place_ids and place["id"] not in links, "Invalid saved routes")
        for feature in rows(place.get("features", []), 100):
            require(text(feature.get("name"), 160) and text(feature.get("description")) and text(feature.get("source_id"), 128), "Invalid saved feature")
    for actor in life["actors"]:
        relationship = actor.get("relationship")
        require(type(relationship) is dict and relationship.get("stance") in STANCES and text(relationship.get("reason")), "Invalid saved relationship")
        for key in ("observations", "commitments"):
            for record in rows(actor.get(key), 100):
                require(type(record.get("known_to_player", True)) is bool and text(record.get("source_id"), 128), "Invalid saved memory visibility or source")
                if key == "observations":
                    require(text(record.get("summary")) and text(record.get("first_source_id"), 128) and
                            type(record.get("observations")) is int and record["observations"] > 0 and
                            record.get("tactic") in TACTICS | {None}, "Invalid saved observation")
                else:
                    require(text(record.get("text")) and record.get("status") in {"open", "fulfilled", "broken"}, "Invalid saved commitment")
    for group in ("aftermath", "developments", "recent_events"):
        for record in rows(life[group], 1000 if group != "recent_events" else 30):
            require(text(record.get("summary")) and text(record.get("subject_id"), 128), "Invalid saved campaign event")
    ledger = life["event_ledger"]
    require(type(ledger) is dict and len(ledger) <= 10000 and all(text(k, 128) and type(v) is str and len(v) == 64 and all(c in "0123456789abcdef" for c in v) for k, v in ledger.items()), "Invalid event receipt ledger")
    source_ledger = life["source_receipts"]
    require(type(source_ledger) is dict and len(source_ledger) <= 10000 and all(text(k, 128) and type(v) is dict and
            type(v.get("sha256")) is str and len(v["sha256"]) == 64 and type(v.get("version")) is int and v["version"] >= 1
            for k,v in source_ledger.items()), "Invalid source receipt ledger")
    dummy = {"fictional_time_seconds": 0}
    p = life["pacing"]
    start = max(0, p.get("authorized_until", 0) - 7*86400) if type(p) is dict and type(p.get("authorized_until", 0)) is int else 0
    apply_pacing(initial(), {"pacing": p}, {"fictional_time_seconds": start}, dummy)


def public_life(life):
    """The model receives GM memory; the dashboard uses this player-only projection."""
    result = copy.deepcopy(life)
    result.pop("event_ledger", None)
    result.pop("source_receipts", None)
    for actor in result["actors"]:
        for key in ("observations", "commitments"):
            actor[key] = [r for r in actor[key] if r.get("known_to_player", True)]
        if not actor["relationship"].get("known_to_player", True):
            actor["relationship"] = {"stance": "neutral", "reason": "No known relationship change."}
    result["recent_events"] = [e for e in result["recent_events"] if e.get("known_to_player", True)]
    return result
