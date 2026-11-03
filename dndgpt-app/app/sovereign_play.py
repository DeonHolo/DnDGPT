"""Embodied Sovereign campaigns: creation contract and ordinary saved scene records.

No background simulation or additional tool round trip. Older campaigns opt in only
through an explicitly requested correction; merely reading/publishing rules changes none.
"""
from .game_profiles import SOVEREIGN, game_id
from .rules import ATTRIBUTES, EQUIPMENT_SLOTS

PROFILE = "sovereign-embodied-2026-11-04"
GROWTH = {"personal_start": 2, "personal_per_level": 2,
          "sovereign_start": 2, "sovereign_per_level": 2}
MODES = {"mobile", "bound", "distributed"}


def embodied(state):
    return game_id(state) == SOVEREIGN and state.get("creation", {}).get("sovereign_ruleset") == PROFILE


def growth(state):
    defaults = GROWTH if embodied(state) else {**GROWTH, "sovereign_start": 1, "sovereign_per_level": 1}
    return {**defaults, **state.get("creation", {}).get("sovereign_growth", {})}


def body(state):
    return state.get("creation", {}).get("sovereign_body", {}) if game_id(state) == SOVEREIGN else {}


def equipment_labels(state):
    return body(state).get("equipment_slots", {})


def require(test, message):
    from .engine import fail
    if not test:
        fail(422, "invalid_sovereign_play", message)


def words(value, maximum=2000):
    return type(value) is str and 0 < len(value.strip()) <= maximum


def records(value, label, maximum=100):
    require(type(value) is list and len(value) <= maximum, label + " must be a bounded list")
    require(all(type(row) is dict and words(row.get("id"), 128) for row in value), label + " needs stable IDs")
    require(len({row["id"] for row in value}) == len(value), label + " IDs must be unique")
    return {row["id"]: row for row in value}


def validate_body(value):
    require(type(value) is dict and set(value) <= {"mode", "form", "description", "primary_attribute",
            "movement", "manipulation", "communication", "perception", "vulnerability", "core_location",
            "equipment_slots"}, "Use the documented Sovereign body fields")
    require(value.get("mode") in MODES and words(value.get("form"), 160) and
            words(value.get("description")), "Describe a mobile, bound or distributed body")
    require(value.get("primary_attribute") in ATTRIBUTES, "Choose the class's actual primary attribute")
    for field in ("movement", "manipulation", "communication", "perception", "vulnerability"):
        require(words(value.get(field)), "Describe the body's " + field + " during creation")
    if value["mode"] == "bound":
        require(words(value.get("core_location"), 240), "A bound character needs a fixed core location")
    slots = value.get("equipment_slots")
    require(type(slots) is dict and 4 <= len(slots) <= len(EQUIPMENT_SLOTS) and
            set(slots) <= set(EQUIPMENT_SLOTS) and all(words(label, 80) for label in slots.values()) and
            len({label.strip().casefold() for label in slots.values()}) == len(slots),
            "Define 4..16 distinct body-appropriate equipment labels using stable equipment keys")


def validate_domain(domain, character):
    holdings = records(domain.get("holdings", []), "Domain holdings")
    for holding in holdings.values():
        require(words(holding.get("name"), 160) and words(holding.get("description")) and
                holding.get("status") in {"integrated", "occupied", "contested", "lost"},
                "Describe each holding and its actual control")
        requirements = records(holding.get("integration_objectives", []), "Integration objectives", 6)
        require(all(words(row.get("text")) and row.get("status") in {"pending", "done"}
                    for row in requirements.values()), "Give integration objectives readable text and status")
        if holding["status"] == "integrated":
            require(words(holding.get("integration_basis")) and
                    all(row["status"] == "done" for row in requirements.values()),
                    "Record why a holding is integrated and finish its published conditions")
    zones = records(domain.get("zones", []), "Domain zones", 100)
    for zone in zones.values():
        require(words(zone.get("name"), 160) and words(zone.get("description")), "Describe each battlefield zone")
        require(type(zone.get("connections", [])) is list and
                all(type(key) is str and key in zones for key in zone.get("connections", [])),
                "Zone connections reference actual zones")
    for asset in records(domain.get("assets", []), "Domain defenses").values():
        require(words(asset.get("name"), 160) and words(asset.get("description")) and
                asset.get("zone_id") in zones, "A defense needs a name, function and actual zone")
        linked = asset.get("character_core") is True
        if linked:
            require(not {"hp", "hp_max", "defense"}.intersection(asset),
                    "The core uses the character's actual HP/DEF, without a second health pool")
        else:
            require(type(asset.get("hp_max")) is int and 1 <= asset["hp_max"] <= 10**9 and
                    type(asset.get("hp")) is int and 0 <= asset["hp"] <= asset["hp_max"] and
                    type(asset.get("defense")) is int and 0 <= asset["defense"] <= 10**6,
                    "Record a defense's real HP, maximum and defense")
    encounters = records(domain.get("encounters", []), "Tactical encounters")
    for encounter in encounters.values():
        require(words(encounter.get("name"), 160) and words(encounter.get("situation")) and
                encounter.get("status") in {"active", "completed", "failed", "abandoned"},
                "Describe the encounter and its actual outcome")
        objectives = records(encounter.get("objectives"), "Encounter objectives", 6)
        require(1 <= len(objectives) <= 6 and all(words(row.get("text")) and
                row.get("status") in {"pending", "done", "failed"} for row in objectives.values()),
                "Publish 1..6 finite encounter objectives")
        require(type(encounter.get("zone_ids")) is list and 1 <= len(encounter["zone_ids"]) <= 12 and
                all(type(key) is str and key in zones for key in encounter["zone_ids"]),
                "An encounter references its actual battlefield zones")
        if encounter["status"] == "completed":
            require(all(row["status"] == "done" for row in objectives.values()) and words(encounter.get("outcome")),
                    "Complete the published encounter objectives and record the aftermath")
    return holdings, encounters


def apply_play(before, state, changes, correction=False):
    if game_id(state) != SOVEREIGN:
        require(not {"sovereign_ruleset", "sovereign_growth", "sovereign_body"}.intersection(state.get("creation", {})),
                "Sovereign body and growth settings belong to Sovereign System")
        return
    creation = state.get("creation", {})
    old_creation = before.get("creation", {})
    marker = creation.get("sovereign_ruleset")
    require(marker is None or marker == PROFILE, "Unknown Sovereign play ruleset")
    if not correction:
        require(marker == old_creation.get("sovereign_ruleset"), "A ruleset conversion needs an explicitly requested correction")
    settings = creation.get("sovereign_growth", {})
    require(type(settings) is dict and set(settings) <= set(GROWTH) and
            all(type(n) is int and 1 <= n <= 4 for n in settings.values()),
            "Growth settings are 1..4 development choices, configured during creation")
    if not correction and before.get("phase") == "adventure":
        if settings != old_creation.get("sovereign_growth", {}):
            request = changes.get("creation", {})
            require(words(request.get("sovereign_growth_reason")),
                    "Record the player's explicit request to change future development rates")
            require(all(growth(state)[key] == growth(before)[key] for key in ("personal_start", "sovereign_start")),
                    "A future growth change does not rewrite already-earned starting rewards")
    if not embodied(state):
        return
    if (not correction and before.get("phase") != "adventure" and
            any(growth(state)[key] != growth(before)[key] for key in ("personal_start", "sovereign_start"))):
        require(not before["personal_powers"]["spent"] and not before["sovereignty"]["ascension_spent"],
                "Configure development counts before choosing the opening improvements")
    value = body(state)
    if value:
        validate_body(value)
        if not correction and before.get("phase") == "adventure":
            require(value == body(before), "Changing an established body needs an explicitly requested rebuild")
        require(all(key in value["equipment_slots"] or item is None for key, item in state["equipment"].items()),
                "Equip items in this body's actual equipment locations")
        if value["mode"] == "bound":
            for field in ("movement", "movement_meters", "movement_mm"):
                require(not changes.get("character", {}).get(field), "The bound core has zero ordinary locomotion")
                state["character"][field] = 0
    domain = state["sovereignty"]["domain"]
    _, encounters = validate_domain(domain, state["character"])
    if not correction:
        previous = before["sovereignty"]["domain"]
        for holding in previous.get("holdings", []):
            current = next((row for row in domain.get("holdings", []) if row["id"] == holding["id"]), None)
            if current is not None and holding.get("integration_objectives"):
                fixed = lambda row: [{k: v for k, v in o.items() if k != "status"}
                                     for o in row.get("integration_objectives", [])]
                require(fixed(current) == fixed(holding), "Keep published integration requirements fixed")
        for prior in previous.get("encounters", []):
            current = encounters.get(prior["id"])
            if prior["status"] == "active":
                require(current is not None, "Resolve an active encounter before archiving it")
            if current is not None:
                fixed = lambda row: [{k: v for k, v in o.items() if k != "status"} for o in row["objectives"]]
                require(fixed(current) == fixed(prior), "Keep the encounter's published finish line fixed")
                require(prior["status"] == "active" or current == prior, "Closed encounters retain their actual outcomes")
    request = changes.get("sovereign_battle")
    if request is not None:
        require(type(request) is dict and request.get("resolution") == "fast",
                "Use ordinary tactical turn saves; set resolution=fast only for delegated or player-authorized fast resolution")


def complete_play(state):
    if not embodied(state):
        return
    require(bool(body(state)), "Save the selected sovereign's body and practical ways of acting")
    validate_body(body(state))
    holdings, _ = validate_domain(state["sovereignty"]["domain"], state["character"])
    if body(state)["mode"] == "bound":
        require(any(row["status"] == "integrated" for row in holdings.values()),
                "Establish the bound sovereign's starting territory")


def award_character(state, amount):
    """Reuse the normal XP/Vital Surge path without resurrecting SP/Talent shops."""
    from .rules import award_xp
    state.setdefault("advancement", {}).setdefault("pending_levels", [])
    paused = state["paused"]
    award_xp(state, amount)
    state["paused"] = paused

