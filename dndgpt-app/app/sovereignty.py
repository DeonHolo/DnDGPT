"""Independent sovereign progression and bounded, atomic formation warfare."""
import copy
import hashlib
import math
from .engine import fail
from .game_profiles import SOVEREIGN, game_id
from .storage import canonical

VETERANCY = (0, 100, 250, 450, 700, 1000)
ROOT_FIELDS = {"domain", "commanders", "formations", "operations", "fronts", "developments",
               "award_ledger", "ascension_earned", "ascension_spent", "battle_reports"}


def require(test, message):
    if not test:
        fail(422, "invalid_sovereignty", message)


def integer(value, low=0, high=1000000):
    return type(value) is int and low <= value <= high


def text(value, maximum=2000):
    return type(value) is str and 0 < len(value.strip()) <= maximum


def one_of(value, options):
    return type(value) is str and value in options


def rows(value, label, maximum=100):
    require(type(value) is list and len(value) <= maximum, label + " must be a bounded list")
    require(all(type(r) is dict and text(r.get("id"), 128) for r in value), label + " needs stable IDs")
    require(len({r["id"] for r in value}) == len(value), label + " IDs must be unique")
    return {r["id"]: r for r in value}


def initial():
    return {"domain": {"id": "domain", "name": "Unestablished domain", "level": 1,
                       "capabilities": [], "next_milestone": None},
            "commanders": [], "formations": [], "operations": [], "fronts": [],
            "developments": [], "award_ledger": {}, "ascension_earned": 0,
            "ascension_spent": [], "battle_reports": []}


def validate(s):
    require(type(s) is dict and set(s) == ROOT_FIELDS, "Use the complete sovereignty schema")
    d = s["domain"]
    require(type(d) is dict and text(d.get("id"), 128) and text(d.get("name"), 160) and
            integer(d.get("level"), 1, 100), "A domain needs an ID, name and level")
    rows(d.get("capabilities"), "Domain capabilities")
    milestone = d.get("next_milestone")
    if milestone is not None:
        require(type(milestone) is dict and text(milestone.get("id"), 128) and
                text(milestone.get("title"), 240) and integer(milestone.get("target_level"), 2, 100),
                "A milestone needs an ID, title and target level")
        objectives = rows(milestone.get("objectives"), "Milestone objectives", 6)
        require(2 <= len(objectives) <= 6 and all(text(o.get("text")) and o.get("status") in
                ("pending", "done") for o in objectives.values()), "Publish 2..6 finite objectives")
        choices = rows(milestone.get("choices"), "Development choices", 3)
        require(len(choices) == 3, "Publish three development choices")
        for choice in choices.values():
            require(text(choice.get("name"), 160) and text(choice.get("description")), "Describe each development")
            rows(choice.get("capabilities"), "Development capabilities")
    commanders = rows(s["commanders"], "Commanders")
    formations = rows(s["formations"], "Formations")
    fronts = rows(s["fronts"], "Fronts", 30)
    limits = d.get("limits")
    if limits is not None:
        require(type(limits) is dict and set(limits) == {"max_formations", "max_strength"} and
                integer(limits["max_formations"], 1, 100) and integer(limits["max_strength"], 1, 100000000),
                "Declare the class-specific domain force limits")
        own = [f for f in formations.values() if f.get("side") == "player" and f.get("status", "active") != "destroyed"]
        require(all(integer(f.get("strength")) for f in own), "Formation strength must be an integer")
        require(len(own) <= limits["max_formations"] and sum(f.get("strength", 0) for f in own) <= limits["max_strength"],
                "Recorded forces exceed the domain's declared capacity")
    for c in commanders.values():
        require(text(c.get("name"), 160) and integer(c.get("level", 1), 1, 1000) and
                integer(c.get("xp", 0)) and integer(c.get("xp_total", 0)) and
                one_of(c.get("status", "active"), {"active", "wounded", "dead", "captured", "departed"}),
                "Invalid commander profile")
        rows(c.get("abilities", []), "Commander abilities")
    for f in formations.values():
        require(text(f.get("name"), 160) and one_of(f.get("side"), {"player", "enemy"}) and
                integer(f.get("maximum_strength"), 1) and integer(f.get("strength"), 0, f["maximum_strength"]) and
                integer(f.get("attack"), -10, 20) and integer(f.get("defense"), 5, 40) and
                integer(f.get("power"), 1, 20) and integer(f.get("armor"), 1, 20) and
                integer(f.get("morale"), 0, 100) and integer(f.get("xp_total", 0)) and
                one_of(f.get("status", "active"), {"active", "routed", "destroyed", "recovering"}), "Invalid formation statistics")
        require(not f.get("commander_id") or text(f["commander_id"], 128) and f["commander_id"] in commanders, "Formation commander must exist")
        require(not f.get("front_id") or text(f["front_id"], 128) and f["front_id"] in fronts, "Formation front must exist")
        require(f["strength"] > 0 or f.get("status") == "destroyed", "Zero-strength formations are destroyed")
        rows(f.get("abilities", []), "Formation abilities")
    for f in fronts.values():
        require(text(f.get("name"), 160) and text(f.get("objective")) and
                integer(f.get("target_progress"), 1, 10) and integer(f.get("terrain_defense", 0), 0, 4) and
                all(integer(f.get(key, 0), 0, 10) for key in ("player_progress", "enemy_progress")) and
                one_of(f.get("status", "active"), {"active", "player_victory", "enemy_victory", "draw"}), "Invalid battle front")
    for op in rows(s["operations"], "Operations").values():
        require(text(op.get("name"), 160) and text(op.get("objective")) and text(op.get("mandate")) and
                text(op.get("commander_id"), 128) and op["commander_id"] in commanders and type(op.get("formation_ids")) is list and
                all(text(key, 128) and key in formations for key in op["formation_ids"]) and
                integer(op.get("started_at"), 0, 10**12) and integer(op.get("due_at"), op["started_at"], 10**12) and
                one_of(op.get("status"), {"active", "completed", "failed", "cancelled"}), "Invalid standing operation")
    rows(s["developments"], "Completed developments", 100)
    rows(s["battle_reports"], "Battle reports", 300)
    require(type(s["award_ledger"]) is dict and len(s["award_ledger"]) <= 10000 and
            all(text(key, 128) and type(value) is str and len(value) == 64 and
                all(c in "0123456789abcdef" for c in value) for key, value in s["award_ledger"].items()) and
            integer(s["ascension_earned"]) and type(s["ascension_spent"]) is list and
            all(text(key, 128) for key in s["ascension_spent"]) and
            len(set(s["ascension_spent"])) == len(s["ascension_spent"]) <= s["ascension_earned"], "Invalid progression ledger")


def award(s, entry):
    require(type(entry) is dict and set(entry) == {"id", "kind", "target_id", "amount", "reason"} and
            text(entry["id"], 128) and text(entry["reason"]) and integer(entry["amount"], 1, 1000), "Invalid progression award")
    require(one_of(entry["kind"], {"commander", "formation"}), "Award a commander or formation")
    old = s["award_ledger"].get(entry["id"])
    signature = hashlib.sha256(canonical(entry).encode()).hexdigest()
    if old is not None:
        require(old == signature, "An achievement ID already has a different reward")
        return
    group = "commanders" if entry["kind"] == "commander" else "formations"
    target = next((r for r in s[group] if r["id"] == entry["target_id"]), None)
    require(target is not None, "Progression target must exist")
    target["xp_total"] = target.get("xp_total", 0) + entry["amount"]
    if group == "commanders":
        target["xp"] = target.get("xp", 0) + entry["amount"]
        target.setdefault("level", 1)
        while target["xp"] >= 100 + 50 * (target["level"] - 1):
            target["xp"] -= 100 + 50 * (target["level"] - 1)
            target["level"] += 1
    else:
        target["veterancy"] = max(i for i, threshold in enumerate(VETERANCY) if target["xp_total"] >= threshold)
    s["award_ledger"][entry["id"]] = signature


def develop(s, request):
    require(type(request) is dict and set(request) == {"milestone_id", "choice_id"}, "Choose a published domain development")
    d, m = s["domain"], s["domain"].get("next_milestone")
    require(m is not None and m["id"] == request["milestone_id"] and m["target_level"] == d["level"] + 1 and
            all(o["status"] == "done" for o in m["objectives"]), "Finish the published milestone before developing")
    choice = next((c for c in m["choices"] if c["id"] == request["choice_id"]), None)
    require(choice is not None, "Choose an actual published development")
    require(not any(r["id"] == m["id"] for r in s["developments"]), "This milestone was already completed")
    existing = rows(d["capabilities"], "Domain capabilities")
    for capability in choice["capabilities"]:
        require(capability["id"] not in existing, "Development capability ID already exists")
        existing[capability["id"]] = copy.deepcopy(capability)
    d["capabilities"] = list(existing.values())
    d["level"] = m["target_level"]
    s["developments"].append({"id": m["id"], "level": d["level"], "title": m["title"], "choice": copy.deepcopy(choice)})
    d["next_milestone"] = None


def battle(s, request, dice):
    require(dice is not None and type(request) is dict and set(request) <= {"front_id", "phase_id", "orders", "phases"}
            and text(request.get("phase_id"), 64) and integer(request.get("phases", 1), 1, 3), "Invalid battle phase")
    require("phase:" + request["phase_id"] not in s["award_ledger"], "This battle phase is already recorded")
    front = next((r for r in s["fronts"] if r["id"] == request.get("front_id")), None)
    require(front is not None and front.get("status", "active") == "active", "Choose an active front")
    forces = {f["id"]: f for f in s["formations"] if f.get("front_id") == front["id"] and
              f.get("status", "active") == "active" and f["strength"] > 0}
    require({f["side"] for f in forces.values()} == {"player", "enemy"}, "A battle needs active opposing forces")
    orders = rows(request.get("orders"), "Battle orders", 20)
    # Orders use the formation ID as their ID to make coverage unambiguous.
    require(set(orders) == set(forces), "Give one order for every active formation on this front")
    for key, order in orders.items():
        require(one_of(order.get("stance"), {"attack", "guard", "withdraw"}), "Choose attack, guard or withdraw")
        if order["stance"] == "attack":
            require(text(order.get("target_id"), 128), "Name an actual target formation")
            target = forces.get(order.get("target_id"))
            require(target is not None and target["side"] != forces[key]["side"], "Attack an opposing formation on this front")
    commanders = {r["id"]: r for r in s["commanders"]}
    report = {"id": request["phase_id"], "front_id": front["id"], "phases": []}
    for _ in range(request.get("phases", 1)):
        active = {key: f for key, f in forces.items() if f.get("status", "active") == "active" and f["strength"]}
        start = {key: f["strength"] for key, f in active.items()}
        losses = {key: 0 for key in active}
        phase = {"attacks": [], "morale": [], "losses": {}}
        for key, f in active.items():
            order = orders[key]
            if order["stance"] != "attack" or order.get("target_id") not in active:
                continue
            target = active[order["target_id"]]
            c = commanders.get(f.get("commander_id"), {})
            leadership = min(3, (c.get("level", 1) - 1) // 3) if c.get("status", "active") == "active" else 0
            natural = dice.roll(20)
            defense = target["defense"] + front.get("terrain_defense", 0) + (2 if orders[target["id"]]["stance"] == "guard" else 0)
            hit = natural == 20 or (natural != 1 and natural + f["attack"] + leadership >= defense)
            pressure = dice.roll(6) if hit else None
            count = math.ceil(start[key] * f["power"] * pressure / (target["armor"] * 20)) if hit else 0
            losses[target["id"]] += count
            phase["attacks"].append({"attacker": key, "target": target["id"], "d20": natural,
                                     "leadership": leadership, "defense": defense, "hit": hit,
                                     "d6": pressure, "pressure_casualties": count})
        for key, f in active.items():
            lost = min(start[key], losses[key])
            f["strength"] -= lost
            f["morale"] = max(0, f["morale"] - math.ceil(lost * 50 / start[key]))
            if not f["strength"]:
                f["status"] = "destroyed"
            elif orders[key]["stance"] == "withdraw":
                f["status"] = "routed"
            elif lost:
                roll = dice.roll(100)
                phase["morale"].append({"formation_id": key, "d100": roll, "threshold": f["morale"]})
                if roll > f["morale"]:
                    f["status"] = "routed"
            phase["losses"][key] = lost
        totals = {side: sum(f["strength"] for f in forces.values() if f["side"] == side and
                           f.get("status", "active") == "active") for side in ("player", "enemy")}
        for side, enemy in (("player", "enemy"), ("enemy", "player")):
            if totals[side] > totals[enemy]:
                field = side + "_progress"
                front[field] = front.get(field, 0) + 1
                if front[field] >= front["target_progress"] or totals[enemy] == 0:
                    front["status"] = side + "_victory"
        if not any(totals.values()):
            front["status"] = "draw"
        phase["objective"] = {key: front.get(key, 0) for key in ("player_progress", "enemy_progress")}
        report["phases"].append(phase)
        if front.get("status", "active") != "active":
            break
    report["outcome"] = front.get("status", "active")
    s["battle_reports"].append(report)
    s["battle_reports"] = s["battle_reports"][-50:]
    s["award_ledger"]["phase:" + request["phase_id"]] = hashlib.sha256(canonical(report).encode()).hexdigest()
    credited = set()
    for key, f in forces.items():
        if f["side"] != "player" or f.get("status") == "destroyed":
            continue
        amount = 40 if report["outcome"] == "player_victory" else 20 if report["outcome"] == "enemy_victory" else 10
        award_id = lambda target: "battle-" + hashlib.sha256((request["phase_id"] + ":" + target).encode()).hexdigest()
        award(s, {"id": award_id(key), "kind": "formation", "target_id": key,
                  "amount": amount, "reason": "Recorded battle phase: " + report["outcome"]})
        commander = f.get("commander_id")
        if commander and commander not in credited and commanders[commander].get("status", "active") in {"active", "wounded"}:
            award(s, {"id": award_id(commander), "kind": "commander", "target_id": commander,
                      "amount": amount * 2, "reason": "Commanded a recorded battle phase"})
            credited.add(commander)


def apply_sovereignty(before, state, changes, correction=False, dice=None):
    controls = {"sovereignty", "sovereign_awards", "sovereign_development", "spend_sovereign_evolution", "sovereign_battle"}
    if game_id(state) != SOVEREIGN:
        require(not controls.intersection(changes), "Sovereign changes require a Sovereign System campaign")
        return
    require("sovereignty" in state, "A Sovereign campaign needs its domain records")
    old, s = before.get("sovereignty", initial()), state["sovereignty"]
    validate(s)
    if correction:
        return
    for ability in state["abilities"]:
        require(one_of(ability.get("scope", "personal"), {"personal", "sovereign"}), "Entity-owned powers belong to their owner, not the player's skill list")
    for c in s["commanders"]:
        for field, default in (("level", 1), ("xp", 0), ("xp_total", 0), ("status", "active")):
            c.setdefault(field, default)
    for f in s["formations"]:
        for field, default in (("xp_total", 0), ("veterancy", 0), ("status", "active")):
            f.setdefault(field, default)
    for key in ("award_ledger", "ascension_earned", "ascension_spent", "developments", "battle_reports"):
        require(s[key] == old[key], key + " is server-controlled")
    require(s["domain"]["level"] == old["domain"]["level"], "Use the published domain development")
    for group, protected in (("commanders", ("level", "xp", "xp_total")), ("formations", ("xp_total", "veterancy"))):
        previous = {r["id"]: r for r in old[group]}
        current = {r["id"]: r for r in s[group]}
        require(previous.keys() <= current.keys(), "Retain entity history; mark casualties/status instead of deleting")
        for key, entity in current.items():
            baseline = previous.get(key, {})
            for field in protected:
                default = 1 if field == "level" else 0
                require(entity.get(field, default) == baseline.get(field, default), "Use achievement awards for entity progression")
    milestone = old["domain"].get("next_milestone")
    if milestone:
        current = s["domain"].get("next_milestone")
        fixed = lambda m: {**m, "objectives": [{k: v for k, v in o.items() if k != "status"} for o in m["objectives"]]}
        require(current is not None and fixed(current) == fixed(milestone), "Keep the published domain milestone fixed")
    if s["domain"].get("next_milestone"):
        require(s["domain"]["next_milestone"]["target_level"] == s["domain"]["level"] + 1, "Publish the next domain level")
    for op in s["operations"]:
        if op["status"] in {"completed", "failed"}:
            require(state["fictional_time_seconds"] >= op["due_at"] and text(op.get("outcome")), "Resolve operations with elapsed fictional time and a recorded outcome")
    gained = max(0, state["character"]["level"] - before["character"]["level"])
    s["ascension_earned"] += gained
    if changes.get("sovereign_awards") or changes.get("sovereign_battle") or changes.get("sovereign_development"):
        require(before["phase"] == "adventure" and not before["paused"] and not before["level_up_freeze"], "Strategic advancement needs active adventure play")
    awards = changes.get("sovereign_awards", [])
    require(type(awards) is list and len(awards) <= 30, "Batch up to 30 earned strategic awards")
    for entry in awards:
        require(type(entry) is dict and not str(entry.get("id", "")).startswith(("phase:", "battle-")), "Battle award IDs are reserved")
        award(s, entry)
    if changes.get("sovereign_development") is not None:
        develop(s, changes["sovereign_development"])
    spend = changes.get("spend_sovereign_evolution")
    if spend is not None:
        require(changes.get("spend_evolution_credit", {}).get("evolution_id") != spend.get("evolution_id")
                if type(spend) is dict and type(changes.get("spend_evolution_credit", {})) is dict else False,
                "An evolution uses one funding source")
        require(s["ascension_earned"] > len(s["ascension_spent"]), "No unspent Sovereign Evolution credit")
        base = next((r for r in before["abilities"] if r["id"] == spend.get("ability_id")), None) if type(spend) is dict else None
        require(base is not None and base.get("scope") == "sovereign", "Evolve an owned sovereign power")
        # Reuse exactly the shared nested-upgrade/preservation validator with an isolated ledger.
        from .quests import apply_quests
        trial_before, trial = copy.deepcopy(before), copy.deepcopy(state)
        trial_before["quest_log"], trial["quest_log"] = [], []
        trial["reward_credits"] = {"earned": s["ascension_earned"], "spent": list(s["ascension_spent"])}
        apply_quests(trial_before, trial, {"spend_evolution_credit": spend})
        s["ascension_spent"] = trial["reward_credits"]["spent"]
    if changes.get("sovereign_battle") is not None:
        require(state["fictional_time_seconds"] > before["fictional_time_seconds"], "A battle phase consumes declared fictional time")
        front_id = changes["sovereign_battle"].get("front_id") if type(changes["sovereign_battle"]) is dict else None
        prior_front = next((r for r in old["fronts"] if r["id"] == front_id), None)
        current_front = next((r for r in s["fronts"] if r["id"] == front_id), None)
        require(prior_front is not None and current_front == prior_front, "Commit the front and conditions before resolving its battle")
        previous_forces = {r["id"]: r for r in old["formations"] if r.get("front_id") == front_id}
        for force in s["formations"]:
            if force.get("front_id") == front_id:
                prior_force = previous_forces.get(force["id"])
                require(prior_force is not None and all(force.get(key) == prior_force.get(key) for key in
                        ("strength", "attack", "defense", "power", "armor", "morale", "commander_id", "status")),
                        "Use precommitted formation statistics for a battle")
        battle(s, changes["sovereign_battle"], dice)
    validate(s)


def complete_sovereign(state):
    if game_id(state) != SOVEREIGN:
        return
    s = state["sovereignty"]
    validate(s)
    require(state["character"]["rarity"] == "UNIQUE" and text(s["domain"].get("description")) and
            s["domain"].get("limits") and s["domain"]["capabilities"] and
            any(c.get("status", "active") == "active" for c in s["commanders"]) and
            any(f["side"] == "player" and f["strength"] > 0 and f.get("status", "active") == "active" for f in s["formations"]) and
            any(a.get("scope") == "sovereign" for a in state["abilities"]),
            "Complete the Unique class, functional domain, major commander, forces and sovereign powers")
