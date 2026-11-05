"""Saved records for Sovereign Laws. The GM resolves the fictional maneuver."""

from .rules import RARITIES
from .sovereign_play import records, require, words

SCOPES = {"personal", "origin", "title", "domain", "general", "forces"}
LEGACY_CONTROLS = {"sovereign_awards", "sovereign_development", "spend_sovereign_evolution",
                   "sovereign_battle", "spend_personal_upgrades", "spend_evolution_credit",
                   "personal_power_exception"}
CHARACTER_FIELDS = {"name", "class_name", "rarity", "attributes", "story_summary", "appearance",
                    "biography", "ancestry", "ancestry_description"}


def initial():
    return {"domain": {"id": "domain", "name": "Unestablished domain", "capabilities": []},
            "commanders": [], "formations": [], "operations": [], "fronts": []}


def kit_check(state):
    creation, character = state["creation"], state["character"]
    missing = []
    for label, ready in (
        ("chosen body", bool(creation.get("sovereign_body"))),
        ("four core Laws", len(state["abilities"]) == 4),
        ("Origin and its ability", bool(creation.get("origin"))),
        ("Title or a choice to defer it", creation.get("title") or creation.get("title_declined") is True),
        ("actual Domain", words(state["sovereignty"]["domain"].get("description"))),
        ("actual rarity", character.get("rarity") in RARITIES),
    ):
        if not ready:
            missing.append(label)
    return {"required": True, "ready": not missing, "missing": missing}


def owners(state):
    s, creation = state["sovereignty"], state["creation"]
    for key in ("origin", "title"):
        if creation.get(key) is not None:
            yield key, creation[key]
    yield "domain", s["domain"]
    for scope, group in (("personal", state["abilities"]), ("general", s["commanders"]),
                         ("forces", s["formations"])):
        for row in group:
            yield scope, row


def validate(before, state, changes, correction=False):
    creation, character = state["creation"], state["character"]
    require(not LEGACY_CONTROLS.intersection(changes) and not state["level_up_freeze"],
            "Save the named development on its owner under Sovereign Laws")
    require(set(character) <= CHARACTER_FIELDS and character.get("rarity") in RARITIES and
            set(character.get("attributes", {})) == {"LCK"} and 1 <= character["attributes"]["LCK"] <= 20,
            "Sovereign Laws records Luck and the creature's actual capabilities")
    require(not any(state["equipment"].values()), "Record who holds or houses gear in inventory")

    body = creation.get("sovereign_body")
    if body is not None:
        require(type(body) is dict and body.get("mode") in ("mobile", "bound", "distributed") and
                all(words(body.get(key)) for key in ("form", "description", "reach", "perception", "vulnerability")),
                "Describe the creature's form, reach, senses and vulnerability")
        if body["mode"] == "bound":
            require(words(body.get("core_location")), "A bound creature needs its fixed locus")

    require(type(creation.get("title_declined", False)) is bool and
            not (creation.get("title_declined") and creation.get("title")), "Choose a Title or defer it")
    for scope, history in (("origin", ("history",)), ("title", ("deed", "recognition"))):
        item = creation.get(scope)
        if item is not None:
            require(type(item) is dict and all(words(item.get(key)) for key in ("id", "name", "effect", *history)) and
                    item.get("rarity") in RARITIES, "Record the " + scope + " and the ability it grants")

    for law in records(state["abilities"], "Core Laws", 4).values():
        require(words(law.get("name")) and words(law.get("mechanics_display")) and words(law.get("flavor_text")) and
                law.get("rarity") == character["rarity"], "Each Law needs a usable effect, flavor and the class grade")

    s = state["sovereignty"]
    require(s.keys() == initial().keys(), "Use the Sovereign Laws Domain and allies records")
    domain = s["domain"]
    require(type(domain) is dict and words(domain.get("id")) and words(domain.get("name")) and
            not {"level", "next_milestone", "limits"}.intersection(domain), "Describe a Domain with actual capabilities")
    for key in ("capabilities", "holdings", "assets", "zones", "encounters"):
        records(domain.get(key, []), "Domain " + key)
    for key in ("commanders", "formations", "operations", "fronts"):
        records(s[key], key)

    previous = {(scope, owner["id"]): owner for scope, owner in owners(before)}
    current = {(scope, owner["id"]): owner for scope, owner in owners(state)}
    quests = {quest["id"]: quest for quest in state["quest_log"]}
    quest_awards = set()
    for (scope, _), owner in current.items():
        require(words(owner.get("name")), "Name the owner of the capability")
        if scope in {"general", "forces"}:
            records(owner.get("abilities", []), "Ally abilities")
        for upgrade in records(owner.get("upgrades", []), "Earned developments").values():
            require(all(words(upgrade.get(key)) for key in ("name", "effect", "source")) and
                    upgrade.get("rarity") in RARITIES, "Record the named upgrade, effect, source and rarity")
            if upgrade["source"].startswith("quest:"):
                quest_id = upgrade["source"].removeprefix("quest:")
                quest = quests.get(quest_id, {})
                reward = quest.get("system_reward", {}).get("development", {}) if quest.get("quest_schema") == 1 else {}
                require(quest.get("status") == "completed" and reward.get("scope") == scope and quest_id not in quest_awards,
                        "Apply a completed quest's promised development once, to its actual owner")
                quest_awards.add(quest_id)

    if before["phase"] == "adventure" and not correction:
        for key, owner in previous.items():
            old_upgrades = {row["id"]: row for row in owner.get("upgrades", [])}
            updated = {row["id"]: row for row in current.get(key, {}).get("upgrades", [])}
            require(all(updated.get(child) == row for child, row in old_upgrades.items()) and
                    (key in current or key[0] in {"general", "forces"} and not old_upgrades),
                    "Keep established Laws, identity, Domain and earned development history")


def complete(state):
    check = kit_check(state)
    require(check["ready"], "Complete the Sovereign build: " + ", ".join(check["missing"]))
