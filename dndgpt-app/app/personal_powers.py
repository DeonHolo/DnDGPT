"""A stable Sovereign personal kit, with atomic, once-only integrated upgrades."""
import copy

from .engine import fail
from .game_profiles import SOVEREIGN, game_id

PROFILE = "sovereign-core-powers-2026-11-03"
CHILD_FIELDS = ("upgrades", "evolutions", "imprints", "integrated_imprints")


def require(test, message):
    if not test:
        fail(422, "invalid_personal_power", message)


def initial():
    return {"profile": PROFILE, "legacy": False, "earned": 2, "spent": [], "extra_powers": []}


def powers(state):
    from .sovereignty import is_foundation
    return [a for a in state.get("abilities", []) if not is_foundation(a)]


def summary(state):
    ledger = state.get("personal_powers")
    legacy = not ledger or ledger.get("legacy", False)
    available = (max(0, ledger["earned"] - len(ledger["spent"])) if ledger else
                 sum(state["character"].get(k, 0) for k in ("skill_points", "talent_points")))
    return {"profile": PROFILE, "legacy_kit": legacy, "power_count": len(powers(state)),
            "upgrades_available": available, "upgrades_per_level": 2, "starting_refinements": 2,
            "acquisition": "Upgrade owned powers; additional standalone powers require an explicit player request."}


def kit_check(state):
    ledger = state.get("personal_powers", {})
    owned = powers(state)
    if ledger.get("profile") != PROFILE or ledger.get("legacy"):
        return {"missing": [] if len(owned) >= 4 else [f"four established personal powers ({len(owned)} recorded)"],
                "personal_required": 4, "personal_recorded": len(owned), "utility_required": 0, "utility_recorded": 0}
    count = state.get("creation", {}).get("personal_power_count", 4)
    reason = state.get("creation", {}).get("personal_power_reason")
    missing = []
    if type(count) is not int or count not in (4, 5) or count == 5 and not isinstance(reason, str) or count == 5 and not reason.strip():
        missing.append("four personal powers, or five with a class-specific reason")
    elif len(owned) != count:
        missing.append(f"{count} substantial personal powers ({len(owned)} recorded)")
    for power in owned:
        if (not all(isinstance(power.get(k), str) and power[k].strip() for k in ("name", "flavor_text")) or
                not any(isinstance(power.get(k), str) and power[k].strip() for k in
                        ("mechanics", "mechanics_display", "full_rules"))):
            missing.append("a name, flavor and current rules for each personal power")
            break
    return {"missing": missing, "personal_required": count, "personal_recorded": len(owned),
            "utility_required": 0, "utility_recorded": 0}


def children(power):
    result = {}
    for field in CHILD_FIELDS:
        values = power.get(field, [])
        require(type(values) is list, "Power improvements must be lists")
        for child in values:
            require(type(child) is dict and isinstance(child.get("id"), str) and
                    1 <= len(child["id"].strip()) <= 128 and child["id"] not in result,
                    "Use unique stable IDs for a power's nested improvements")
            result[child["id"]] = child
    return result


def apply_personal_powers(before, state, changes, correction=False):
    controls = {"spend_personal_upgrades", "personal_power_exception"}
    if game_id(state) != SOVEREIGN:
        require(not controls.intersection(changes), "Personal power upgrades belong to Sovereign System")
        return
    if state.get("creation", {}).get("rules_source") == "custom":
        require(not controls.intersection(changes), "Use the campaign's explicit custom progression rules")
        return
    ledger = state.get("personal_powers")
    if ledger is not None:
        require(type(ledger) is dict and ledger.get("profile") == PROFILE and
                type(ledger.get("earned")) is int and ledger["earned"] >= 0 and
                type(ledger.get("spent")) is list and all(isinstance(key, str) for key in ledger["spent"]) and
                len(set(ledger["spent"])) == len(ledger["spent"]) and
                len(ledger["spent"]) <= ledger["earned"] and type(ledger.get("extra_powers")) is list,
                "Invalid personal upgrade history")
    if correction:
        return
    if ledger is None:
        # Older characters keep every ability. Only their actual banked points carry over.
        ledger = {"profile": PROFILE, "legacy": True,
                  "earned": sum(before["character"].get(k, 0) for k in ("skill_points", "talent_points")),
                  "spent": [], "extra_powers": []}
        state["personal_powers"] = ledger
    for key in ("skill_points", "talent_points"):
        require(changes.get("character", {}).get(key, 0) == 0,
                "Sovereign levels grant two personal upgrades automatically; use spend_personal_upgrades")
        state["character"][key] = 0
    gained = state["character"]["level"] - before["character"]["level"]
    require(gained >= 0, "Use a reviewed correction to lower character level")
    ledger["earned"] += 2 * gained + max(0, state["character"]["level"] // 4 - before["character"]["level"] // 4)

    old, current = {p["id"]: p for p in powers(before)}, {p["id"]: p for p in powers(state)}
    exception = changes.get("personal_power_exception")
    if exception is not None:
        require(type(exception) is dict and set(exception) == {"ability_ids", "reason"} and
                isinstance(exception["reason"], str) and 1 <= len(exception["reason"].strip()) <= 1000 and
                type(exception["ability_ids"]) is list and 1 <= len(exception["ability_ids"]) <= 4 and
                all(isinstance(key, str) for key in exception["ability_ids"]) and
                len(set(exception["ability_ids"])) == len(exception["ability_ids"]),
                "An explicitly requested additional power needs its IDs and the player's reason")
        require(set(exception["ability_ids"]) == current.keys() - old.keys(),
                "Reference exactly the new personal powers requested by the player")
        ledger["extra_powers"].append(copy.deepcopy(exception))
    if before["phase"] == "adventure":
        require(old.keys() <= current.keys(), "Preserve owned personal powers; use a reviewed correction for a rebuild")
        require(not current.keys() - old.keys() or exception is not None,
                "Upgrade existing personal powers. New standalone powers require an explicit player request and personal_power_exception")

    spends = changes.get("spend_personal_upgrades", [])
    require(type(spends) is list and len(spends) <= 20, "Batch at most twenty personal upgrades")
    paid, identifiers = {}, set()
    for spend in spends:
        require(type(spend) is dict and set(spend) == {"ability_id", "upgrade_id"} and
                all(isinstance(spend[k], str) and 1 <= len(spend[k].strip()) <= 128 for k in spend),
                "Select an owned personal power and a nested upgrade ID")
        key, upgrade = spend["ability_id"], spend["upgrade_id"]
        require(key in old and key in current and upgrade not in identifiers and upgrade not in ledger["spent"],
                "Spend each personal upgrade once on an already owned personal power")
        identifiers.add(upgrade); paid.setdefault(key, set()).add(upgrade)
    require(ledger["earned"] - len(ledger["spent"]) >= len(spends), "No personal upgrades remain available")
    free = changes.get("spend_evolution_credit", {})
    require(not identifiers.intersection({free.get("evolution_id")} if type(free) is dict else set()),
            "An upgrade uses one funding source")
    sovereign = changes.get("spend_sovereign_evolution", {})
    require(not identifiers.intersection({sovereign.get("evolution_id")} if type(sovereign) is dict else set()),
            "Personal and Sovereign upgrades have separate funding")
    for key in old.keys() & current.keys():
        base, parent = old[key], current[key]
        if before["phase"] != "adventure" and key not in paid:
            continue
        if key not in paid and all(parent.get(field, []) == base.get(field, []) for field in CHILD_FIELDS):
            require(parent.get("rarity") == base.get("rarity"), "Preserve the power's recorded rarity")
            continue
        previous, updated = children(base), children(parent)
        require(parent.get("rarity") == base.get("rarity") and
                all(updated.get(child_id) == row for child_id, row in previous.items()),
                "Preserve the power's rarity and acquired improvements")
        added = updated.keys() - previous.keys()
        expected = set(paid.get(key, ()))
        if type(free) is dict and free.get("ability_id") == key:
            expected.add(free.get("evolution_id"))
        require(added == expected, "Commit each new personal improvement with its upgrade selection or quest reward")
        if added:
            require(any(isinstance(parent.get(field), str) and parent[field].strip() and
                        parent.get(field) != base.get(field) for field in ("mechanics", "mechanics_display", "full_rules")),
                    "Update the power's consolidated Full rules with the selected improvements")
            require(all(isinstance(updated[child].get("name"), str) and updated[child]["name"].strip() and
                        any(updated[child].get(k) for k in ("change_display", "changes", "mechanics", "mechanics_display", "description"))
                        for child in added), "Name each improvement and describe its actual change")
    ledger["spent"].extend(spend["upgrade_id"] for spend in spends)
