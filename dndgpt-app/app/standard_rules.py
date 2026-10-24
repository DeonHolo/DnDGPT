"""Current chat-play contract; legacy sandbox calculations stay versioned separately."""

PROFILE = "resources-utility-2026-10-17"
UTILITY_MINIMUM = {"EPIC": 1, "LEGENDARY": 1, "UNIQUE": 2}


def uses_standard_rules(state):
    return (state.get("rules_profile") == PROFILE and
            state.get("creation", {}).get("rules_source") != "custom")


def starting_resources(attributes):
    return {"hp_max": 45 + 3 * attributes["STR"],
            "mp_max": 75 + 5 * attributes["INT"]}


def ability_kind(ability):
    activation = str(ability.get("activation", "")).lower()
    labels = " ".join(str(ability.get(key, "")) for key in
                      ("group", "category", "role", "type")).lower()
    if "utility" in activation + " " + labels or ability.get("outside_combat_only") is True:
        return "utility"
    if activation.startswith("passive"):
        return "passive"
    if activation.startswith("reaction"):
        return "reaction"
    if activation.replace("_", " ").startswith("free action"):
        return "free_action"
    return "active" if activation.startswith(("action", "active", "bonus action")) else "other"


def class_kit_check(state):
    """Report fixed starting-kit counts, never invent or roll missing abilities."""
    rarity = str(state.get("character", {}).get("rarity", "")).upper()
    minimum = (0 if state.get("creation", {}).get("rules_source") == "custom"
               else UTILITY_MINIMUM.get(rarity, 0))
    if not minimum:
        return {"missing": [], "utility_required": 0, "utility_recorded": 0}
    owned = [a for a in state.get("abilities", [])
             if str(a.get("source", "")).lower().startswith("class") or a.get("source_class")]
    counts = {kind: 0 for kind in ("active", "passive", "reaction", "free_action", "utility")}
    for ability in owned:
        kind = ability_kind(ability)
        if kind in counts:
            counts[kind] += 1
    required = {"active": 1, "passive": 1, "reaction": 1, "free_action": 1, "utility": minimum}
    missing = [f"{value - counts[kind]} {kind.replace('_', ' ')}" for kind, value in required.items()
               if counts[kind] < value]
    return {"missing": missing, "utility_required": minimum, "utility_recorded": counts["utility"]}


def rules_guidance():
    return {"resources": ["HP", "MP"], "starting_hp": "45 + 3 * STR",
            "starting_mp": "75 + 5 * INT",
            "attributes": ["STR", "DEX", "INT", "CHA", "LCK"],
            "completion": "Read direct-play. Final creation choices save story, gear and opening with "
                          "begin_adventure=true. Advancement choices commit and continue directly.",
            "starting_equipment": "Read starting-gear for one recorded class-budgeted outfitting draw "
                                  "and four functional equipped items; save receipt/item_ids in creation.outfitting.",
            "distance_display": "From the FIRST reveal, use complete mechanics_display and range_display "
                                "with descriptive reach (Engaged/Near/Far/Distant), including starting kits, "
                                "summon stats/commands, Full rules and upgrades. Counted distances, including "
                                "spelled-out meters, paces or steps, stay private except requested audits. "
                                "Keep other stats/dice/costs/durations exact. Check legal source ranges privately; "
                                "movement stays limited and Dash costs the Action.",
            "companion_identity": "Name the concrete individual from its identity/culture; vary accessible "
                                  "naming history. Preserve chosen names. No shared memory of unavailable chats.",
            "class_kits": "Epic/Legendary: Active, Passive, Reaction, Free Action, 1 Utility. "
                          "Unique: Active, Passive, Reaction, Free Action, 2 distinct Utilities.",
            "utility": "An outside-combat role with Active or Passive activation; save group=utility. "
                       "Class-native Utilities inherit class rarity. Independent Utilities use normal "
                       "skill-board rarity/Luck rolls and selection slots. Apply the same creativity, "
                       "originality and class-flavor locks to every Utility.",
            "custom_rules": "For a player's explicit replacement rulebook, save creation.rules_source=custom."}
