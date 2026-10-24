"""Finite quest records and once-only rewards inside the normal saved turn."""
import copy

from .engine import fail
from .rules import award_xp

TERMINAL = {"completed", "failed", "abandoned"}
OBJECTIVE_STATES = {"pending", "in_progress", "done", "blocked"}


def require(condition, message):
    if not condition:
        fail(422, "invalid_quest", message)


def nonblank(value, maximum=600):
    return type(value) is str and 0 < len(value.strip()) <= maximum


def integer(value, maximum=10**9):
    return type(value) is int and 0 <= value <= maximum


def reward(value, contract=False):
    require(type(value) is dict, "Quest rewards must be objects")
    allowed = {"summary", "source", "currency", "items"} | (set() if contract else {"xp", "evolution_credits"})
    require(not value.keys() - allowed, "Unknown reward field; settlement is server-controlled")
    require(value.get("source", "System") == "System" or contract, "System reward source must be System")
    require(integer(value.get("xp", 0), 100000), "Quest XP must be 0..100000")
    require(integer(value.get("evolution_credits", 0), 3), "Evolution credits must be 0..3")
    currency = value.get("currency", {})
    require(type(currency) is dict and len(currency) <= 8 and
            all(nonblank(key, 40) and integer(amount) for key, amount in currency.items()),
            "Reward currency needs named nonnegative integer amounts")
    items = value.get("items", [])
    require(type(items) is list and len(items) <= 12, "Reward items must be a list of at most 12")
    ids = []
    for item in items:
        require(type(item) is dict and nonblank(item.get("id"), 128) and nonblank(item.get("name"), 160),
                "Each reward item needs a stable ID and name")
        ids.append(item["id"])
    require(len(ids) == len(set(ids)), "Reward item IDs must be distinct")
    return value


def normalize(quest):
    require(nonblank(quest.get("name") or quest.get("title"), 200), "A quest needs a short title")
    require(nonblank(quest.get("finish_condition")), "A quest needs an explicit finish condition")
    objectives = quest.get("objectives")
    require(type(objectives) is list and 1 <= len(objectives) <= 12, "A quest needs 1..12 finite objectives")
    ids = []
    for obj in objectives:
        require(type(obj) is dict and nonblank(obj.get("id"), 128) and nonblank(obj.get("text")),
                "Each objective needs a stable ID and text")
        require(type(obj.get("optional", False)) is bool, "Objective optional must be boolean")
        require(obj.get("status", "pending") in OBJECTIVE_STATES, "Unknown objective status")
        if "target" in obj:
            require(integer(obj["target"], 1000000) and obj["target"] > 0 and
                    integer(obj.get("current", 0), obj["target"]), "Invalid objective counter")
            if obj.get("current", 0) == obj["target"]:
                obj["status"] = "done"
            else:
                require(obj.get("status") != "done", "A completed counter must reach its target")
        if "reward" in obj:
            require(obj.get("optional", False), "Use System reward for required objectives")
            reward(obj["reward"])
        ids.append(obj["id"])
    require(len(ids) == len(set(ids)) and any(not obj.get("optional") for obj in objectives),
            "Use distinct objective IDs and at least one required objective")
    reward(quest.get("system_reward"))
    package = quest["system_reward"]
    require(package.get("xp") or package.get("evolution_credits") or package.get("items") or
            any(package.get("currency", {}).values()), "Declare a concrete System reward")
    status = str(quest.get("status", "active")).lower()
    require(status in TERMINAL | {"active", "paused"}, "Unknown quest status")
    done = all(obj.get("status") == "done" for obj in objectives if not obj.get("optional"))
    require(status != "completed" or done, "Complete all required objectives before closing a quest")
    quest["status"] = "completed" if done and status in {"active", "paused"} else status
    if "contract_payment" in quest:
        contract = quest["contract_payment"]
        require(type(contract) is dict and nonblank(contract.get("creditor"), 200) and
                nonblank(contract.get("condition")), "Contract payment needs creditor and collection condition")
        require(contract.get("status", "owed") in {"owed", "collected", "unavailable"}, "Unknown payment status")
        reward(contract.setdefault("reward", {}), contract=True)


def grant(state, package):
    """The caller marks this source settled in the same atomic saved version."""
    amount = package.get("xp", 0)
    if amount:
        state.setdefault("advancement", {}).setdefault("pending_levels", [])
        paused = state["paused"]
        award_xp(state, amount)
        state["paused"] = paused  # Advancement freezes choices, not a separate manual resume gate.
    funds = state.setdefault("funds", {})
    for unit, amount in package.get("currency", {}).items():
        require(integer(funds.get(unit, 0)), "Existing funds need integer amounts before settling this currency")
        funds[unit] = funds.get(unit, 0) + amount
    inventory = {item["id"]: item for item in state["inventory"]}
    for item in package.get("items", []):
        require(item["id"] not in inventory, "Reward item already exists; do not also upsert automatically granted items")
        inventory[item["id"]] = copy.deepcopy(item)
    state["inventory"] = list(inventory.values())
    state["reward_credits"]["earned"] += package.get("evolution_credits", 0)


def apply_quests(before, state, changes, correction=False):
    old = {row["id"]: row for row in before.get("quest_log", [])}
    current = {row["id"]: row for row in state.get("quest_log", [])}
    structured = [row for row in current.values() if row.get("quest_schema") == 1]
    prior = [row for row in old.values() if row.get("quest_schema") == 1]
    if not structured and not prior and "spend_evolution_credit" not in changes:
        return
    ledger = state.setdefault("quest_settlements", copy.deepcopy(before.get("quest_settlements", {})))
    credits = state.setdefault("reward_credits", copy.deepcopy(before.get("reward_credits", {"earned": 0, "spent": []})))
    if not correction:
        require(all(row["id"] in current and current[row["id"]].get("quest_schema") == 1 for row in prior),
                "Keep structured quest history; use a reviewed correction to remove it")
    for quest in structured:
        normalize(quest)
        previous = old.get(quest["id"], {})
        require(quest.get("reward_status") == previous.get("reward_status"), "Quest reward_status is server-controlled")
        if previous.get("quest_schema") == 1 and not correction:
            require(quest["finish_condition"] == previous["finish_condition"] and
                    quest["system_reward"] == previous["system_reward"], "Keep the published finish condition and reward; create a follow-up quest")
            old_objs = {obj["id"]: obj for obj in previous["objectives"]}
            new_objs = {obj["id"]: obj for obj in quest["objectives"]}
            fixed = lambda obj: {k: v for k, v in obj.items() if k not in {"status", "current"}}
            require(old_objs.keys() == new_objs.keys() and all(fixed(obj) == fixed(new_objs[key]) for key, obj in old_objs.items()),
                    "Keep the finite objective list; new goals need a follow-up quest")
            if previous.get("status") in TERMINAL:
                require(quest["status"] == previous["status"], "A closed quest stays closed")
            if "contract_payment" in previous:
                require({k: v for k, v in previous["contract_payment"].items() if k != "status"} ==
                        {k: v for k, v in quest.get("contract_payment", {}).items() if k != "status"}, "Preserve the promised contract terms")
        if correction:
            continue
        settled = ledger.setdefault(quest["id"], {})
        historical = previous.get("quest_schema") != 1 and previous.get("status") in TERMINAL
        payouts = []
        if quest["status"] == "completed":
            payouts.append(("system", quest["system_reward"]))
        if quest.get("contract_payment", {}).get("status") == "collected":
            payouts.append(("contract", quest["contract_payment"]["reward"]))
        for obj in quest["objectives"]:
            if obj.get("optional") and obj.get("status") == "done" and "reward" in obj:
                payouts.append(("bonus:" + obj["id"], obj["reward"]))
        for key, package in payouts:
            if key not in settled:
                require(before["phase"] == "adventure" or historical, "Quest rewards are earned during adventure play")
                if not historical:
                    grant(state, package)
                settled[key] = {"version": before["version"] + 1, "historical": historical}
        quest["reward_status"] = "settled" if "system" in settled else "pending"
    spend = changes.get("spend_evolution_credit")
    if spend is not None:
        require(type(spend) is dict and set(spend) == {"ability_id", "evolution_id"}, "Select an owned ability and new evolution ID")
        require(credits["earned"] > len(credits["spent"]), "No unspent Skill Evolution credit")
        base = next((row for row in before["abilities"] if row["id"] == spend["ability_id"]), None)
        parent = next((row for row in state["abilities"] if row["id"] == spend["ability_id"]), None)
        require(base is not None and parent is not None and not any(base.get(key) for key in
                ("parent_id", "parent_ability_id", "parent_skill_id")), "Evolve an owned standalone base ability")
        groups = ("evolutions", "upgrades", "imprints")
        old_rows = [row for key in groups for row in base.get(key, [])]
        new_rows = [row for key in groups for row in parent.get(key, [])]
        require(all(type(row) is dict and nonblank(row.get("id"), 128) for row in old_rows + new_rows),
                "Saved upgrades need stable child IDs before spending a free evolution")
        owned = {row["id"] for row in old_rows}
        children = {row["id"] for row in new_rows}
        preserved = {row["id"]: row for row in new_rows if row["id"] in owned}
        require(nonblank(spend["evolution_id"], 128) and spend["evolution_id"] not in owned and
                spend["evolution_id"] not in credits["spent"] and children == owned | {spend["evolution_id"]} and
                len(new_rows) == len(children) and
                all(preserved.get(row["id"]) == row for row in old_rows) and
                parent.get("imprints", []) == base.get("imprints", []) and
                parent.get("rarity") == base.get("rarity"), "Add one nested evolution and preserve prior upgrades and source rarity")
        credits["spent"].append(spend["evolution_id"])
