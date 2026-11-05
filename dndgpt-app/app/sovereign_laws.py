"""Saved records for Sovereign Laws. The GM resolves the fictional maneuver."""

from .rules import RARITIES
from .sovereign_play import records, require, words

SCOPES = {"personal", "origin", "title", "domain", "general", "forces"}
SELECTIONS = {"class_offers": 12, "other_offers": 6, "picks": 2}
LEGACY_CONTROLS = {"sovereign_awards", "sovereign_development", "spend_sovereign_evolution",
                   "sovereign_battle", "spend_personal_upgrades", "spend_evolution_credit",
                   "personal_power_exception"}
CHARACTER_FIELDS = {"name", "class_name", "rarity", "attributes", "story_summary", "appearance",
                    "biography", "ancestry", "ancestry_description"}


def initial():
    return {"domain": {"id": "domain", "name": "Unestablished domain", "capabilities": []},
            "commanders": [], "formations": [], "operations": [], "fronts": []}


def selection_policy(state):
    return {**SELECTIONS, **state.get("creation", {}).get("selection_policy", {})}


def identities(state, scope):
    creation = state["creation"]
    if scope + "s" in creation:
        return creation[scope + "s"]
    return [creation[scope]] if creation.get(scope) else []


def validate_selections(before, state):
    policy = state["creation"].get("selection_policy", {})
    require(type(policy) is dict and set(policy) <= SELECTIONS.keys() and
            all(type(value) is int and 1 <= value <= 20 for value in policy.values()),
            "Selection preferences need bounded offer and pick counts")
    policy = selection_policy(state)
    require(policy["picks"] <= policy["other_offers"], "Picks must fit the offered board")
    previous = {row["id"]: row for row in before["creation"].get("selection_boards", [])}
    for board in records(state["creation"].get("selection_boards", []), "Selection boards").values():
        require(type(board.get("kind")) is str and board["kind"] in {"class", "origin", "title", "personal", "sovereign", "identity", "major"} and
                type(board.get("complete", False)) is bool,
                "Name the selection board's purpose")
        old = previous.get(board["id"])
        require(not old or old["kind"] == board["kind"], "Keep the issued board's purpose")
        offers = records(board.get("offers"), "Selection offers", 20)
        issued = selection_policy(before) if old else policy
        count = old.get("offer_count") if old and "offer_count" in old else issued["class_offers"] if board["kind"] == "class" else issued["other_offers"]
        require(len(offers) == count and all(words(row.get("name")) and row.get("rarity") in RARITIES for row in offers.values()),
                "Offer the complete board with each candidate's name and rolled rarity")
        picked = board.get("selected_ids", [])
        expected = old.get("pick_count") if old and "pick_count" in old else 1 if board["kind"] == "class" else issued["picks"]
        require(type(picked) is list and all(type(key) is str and key in offers for key in picked) and
                len(picked) == len(set(picked)) and len(picked) <= expected and
                (not board.get("complete") or len(picked) == expected), "Complete the board with its selected picks")
        board.update(offer_count=count, pick_count=expected)


def kit_check(state):
    creation, character = state["creation"], state["character"]
    count = selection_policy(state)["picks"] if creation.get("selection_policy") else 1
    established = state["phase"] == "adventure"
    missing = []
    for label, ready in (
        ("chosen body", bool(creation.get("sovereign_body"))),
        ("four core Laws", len(state["abilities"]) == 4),
        (str(count) + " Origin traits and their abilities", bool(identities(state, "origin")) if established else len(identities(state, "origin")) == count),
        (str(count) + " Titles or a choice to defer them", (bool(identities(state, "title")) if established else len(identities(state, "title")) == count) or creation.get("title_declined") is True),
        ("actual Domain", words(state["sovereignty"]["domain"].get("description"))),
        ("actual rarity", character.get("rarity") in RARITIES),
    ):
        if not ready:
            missing.append(label)
    return {"required": True, "ready": not missing, "missing": missing}


def owners(state):
    s, creation = state["sovereignty"], state["creation"]
    for key in ("origin", "title"):
        for item in identities(state, key):
            yield key, item
    yield "domain", s["domain"]
    for scope, group in (("personal", state["abilities"]), ("general", s["commanders"]),
                         ("forces", s["formations"])):
        for row in group:
            yield scope, row


def validate(before, state, changes, correction=False):
    creation, character = state["creation"], state["character"]
    validate_selections(before, state)
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
            not (creation.get("title_declined") and identities(state, "title")), "Choose Titles or defer them")
    for scope, history in (("origin", ("history",)), ("title", ("deed", "recognition"))):
        for item in records(identities(state, scope), scope.title() + " records").values():
            require(all(words(item.get(key)) for key in ("id", "name", "effect", *history)) and
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
    quest_awards = {}
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
                quest_awards[quest_id] = quest_awards.get(quest_id, 0) + 1
                require(quest.get("status") == "completed" and reward.get("scope") == scope and
                        quest_awards[quest_id] <= reward.get("picks", 1),
                        "Apply the completed quest's promised development picks once, to their actual owners")

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
