"""Transactional sandbox combat for explicitly supported power programs.

All declarations and targets are checked before dice. Callers receive a new state;
failed commands cannot partially spend resources. This is not the full RPG engine.
"""
from copy import deepcopy
from dataclasses import asdict
from math import isqrt

from .creation_codec import ability as decode_ability
from .powers import bind, integrate, label, rider as decode_rider
from .rules import ATTRIBUTES, TurnBudget, integer, modifier
from .spatial import Point, SolidBox, intersects, legal_target
from . import gear
from .summon_runtime import SummonRuntime


def exact(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError("Invalid combat fields")


def rows(value, maximum=32, minimum=0):
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise ValueError("Invalid combat list")
    return value


def point(value):
    if len(rows(value, 3, 3)) != 3:
        raise ValueError("Position needs three coordinates")
    return Point(*(integer(n, -1000000000, 1000000000, "coordinate") for n in value))


def obstacles(values):
    result = []
    for value in rows(values, 100):
        exact(value, ("minimum", "maximum"))
        result.append(SolidBox(point(value["minimum"]), point(value["maximum"])))
    return result


def prepare(character, actors, order, solids):
    """Commit a disposable test scenario, never a generated playable character."""
    definitions, boxes = rows(actors, 32, 2), obstacles(solids)
    result = {}
    for definition in definitions:
        exact(definition, ("id", "name", "team", "attributes", "hp", "hp_max", "mp", "mp_max",
                           "sta", "sta_max", "def", "movement_mm", "position", "abilities"),
              ("imprints", "resistances", "reaction_policy", "loadout"))
        actor = deepcopy(definition)
        for field in ("id", "name", "team"):
            label(actor[field])
        if actor["id"] in result:
            raise ValueError("Duplicate combat actor")
        exact(actor["attributes"], ATTRIBUTES)
        for score in actor["attributes"].values():
            integer(score, 1, 20, "attribute")
        for resource in ("hp", "mp", "sta"):
            maximum = integer(actor[resource + "_max"], 1 if resource == "hp" else 0, 1000000000, resource + " maximum")
            integer(actor[resource], 1 if resource == "hp" else 0, maximum, resource)
        # Input bounds must accommodate the sum of all sixteen legal gear bonuses.
        integer(actor["def"], 1, 1000000, "defense")
        integer(actor["movement_mm"], 0, 100000000, "speed")
        origin = point(actor["position"])
        if any(intersects(origin, origin, box) for box in boxes):
            raise ValueError("Actor is inside solid geometry")
        powers = [decode_ability(value) for value in rows(actor["abilities"], 100)]
        if any(power.source_kind == "ITEM" for power in powers):
            raise ValueError("Item powers must come from the actual owned loadout")
        if "loadout" in actor:
            loadout = gear.decode(actor["loadout"])
            calculated = gear.calculate(loadout, actor["attributes"])["derived"]
            if any(actor[field] != calculated[field] for field in ("hp_max", "mp_max", "sta_max", "def", "movement_mm")):
                raise ValueError("Equipped actor statistics do not match the actual loadout")
            powers.extend(power.ability for item in (*loadout.items, *loadout.supplies) for power in item.powers)
        if len({power.id for power in powers}) != len(powers):
            raise ValueError("Duplicate ability ID")
        for power in powers:
            bind(power)
        actor["imprints"] = actor.get("imprints", [])
        parents = {power.id: power for power in powers}
        imprint_ids, imprint_parents = set(), set()
        for imprint in rows(actor["imprints"], 1):
            exact(imprint, ("id", "parent_id", "rider"))
            label(imprint["id"])
            label(imprint["parent_id"])
            if imprint["id"] in imprint_ids or imprint["parent_id"] in imprint_parents:
                raise ValueError("Duplicate integrated Imprint")
            imprint_ids.add(imprint["id"])
            imprint_parents.add(imprint["parent_id"])
            parent = parents.get(imprint["parent_id"])
            if parent is None:
                raise ValueError("Imprint parent is not owned")
            integrate(parent, decode_rider(imprint["rider"]))
        actor["resistances"] = actor.get("resistances", {})
        if type(actor["resistances"]) is not dict or len(actor["resistances"]) > 100:
            raise ValueError("Invalid resistances")
        for damage_type, ratio in actor["resistances"].items():
            label(damage_type)
            if type(ratio) is not list or any(type(n) is not int for n in ratio) or ratio not in ([0, 1], [1, 2], [1, 1], [2, 1]):
                raise ValueError("Resistance needs an explicit supported rational multiplier")
        actor["reaction_policy"] = actor.get("reaction_policy", "CONSERVE")
        if actor["reaction_policy"] not in ("CONSERVE", "MITIGATE"):
            raise ValueError("Unsupported defensive Reaction policy")
        actor.update(turn=0, movement_spent_mm=0, budget=asdict(TurnBudget(movement_mm=actor["movement_mm"])),
                     conditions=[], ward=None, cooldowns={}, uses_turn={}, uses_encounter={})
        result[actor["id"]] = actor
    if "player" not in result or len({actor["team"] for actor in result.values()}) < 2:
        raise ValueError("Scenario requires the sandbox player and an opposing team")
    player = result["player"]
    for field in (*ATTRIBUTES,):
        if player["attributes"][field] != character["attributes"][field]:
            raise ValueError("Scenario cannot change sandbox attributes")
    for field in ("hp", "hp_max", "mp", "mp_max", "sta", "sta_max", "def", "movement_mm"):
        if player[field] != character[field]:
            raise ValueError("Scenario cannot change sandbox resources or derived statistics")
    rows(order, 32, 2)
    if any(type(actor_id) is not str for actor_id in order) or len(set(order)) != len(order) or set(order) != set(result):
        raise ValueError("Turn order must contain each actor exactly once")
    return {"schema": 1, "actors": result, "order": deepcopy(order), "active": order[0],
            "round": 1, "status": "ready", "obstacles": deepcopy(solids)}


class Runtime(SummonRuntime):
    def __init__(self, encounter, dice, preview):
        self.state, self.dice, self.preview = encounter, dice, preview
        self.actors = encounter["actors"]
        self.boxes = obstacles(encounter["obstacles"])
        self.ledger = []

    def actor(self, actor_id):
        if type(actor_id) is not str or actor_id not in self.actors:
            raise ValueError("Unknown combat actor")
        return self.actors[actor_id]

    def ready(self, actor_id):
        if self.state["status"] != "active" or self.state["active"] != actor_id:
            raise ValueError("Actor does not have the active turn")
        actor = self.actor(actor_id)
        if actor["hp"] <= 0:
            raise ValueError("Incapacitated actor cannot act")
        return actor

    def blocked(self, actor, activation):
        return any(activation in condition["definition"]["blocks"] for condition in actor["conditions"])

    def bonus(self, actor, name):
        return sum(condition["definition"][name] for condition in actor["conditions"])

    def budget(self, actor, resource, amount=1):
        actor["budget"] = asdict(TurnBudget(**actor["budget"]).spend(resource, amount))

    def refresh_gear(self, actor, loadout):
        previous_speed = actor["movement_mm"]
        gear.recalculate(actor, loadout)
        actor["loadout"] = gear.encode(loadout)
        # More speed can help this turn; re-equipping cannot reset distance spent.
        limit = max(0, actor["movement_mm"] - actor.get("movement_spent_mm", 0) - self.bonus(actor, "movement_penalty_mm"))
        actor["budget"]["movement_mm"] = min(limit, max(0, actor["budget"]["movement_mm"] + actor["movement_mm"] - previous_speed))

    def validate_use(self, actor, power, targets, trigger=None, *, permission=None):
        program = bind(power)
        if program.summon is not None and permission != "MANIFEST":
            raise ValueError("Use manifest_summons with explicit formation placements")
        if program.command is not None and permission != "COMMAND_OWNER":
            raise ValueError("Use command_summons with explicit legal unit orders")
        if actor["hp"] <= 0 or self.blocked(actor, power.activation):
            raise ValueError("Actor cannot activate this power")
        if trigger is None:
            if "summon" in actor:
                if permission not in ("COMMANDED", "AUTONOMOUS") or actor["summon"]["definition"]["control"] != permission:
                    raise ValueError("Summon requires its actual command or autonomous phase")
                self.ready(actor["summon"]["owner_id"])
            else:
                self.ready(actor["id"])
            if power.activation not in ("ACTION", "FREE_ACTION"):
                raise ValueError("Passive and Reaction powers require an actual internal trigger")
        elif trigger not in (program.passive_trigger, program.reaction_trigger):
            raise ValueError("Wrong power trigger")
        if power.activation != "PASSIVE" and actor["budget"][power.activation.lower()] < 1:
            raise ValueError("Activation budget exhausted")
        if power.mp_cost > actor["mp"] or power.sta_cost > actor["sta"]:
            raise ValueError("Insufficient ability resources")
        if actor["turn"] < actor["cooldowns"].get(power.id, 0):
            raise ValueError("Power is cooling down")
        if actor["uses_turn"].get(power.id, 0) >= program.uses_per_turn:
            raise ValueError("Power turn limit reached")
        if program.uses_per_encounter is not None and actor["uses_encounter"].get(power.id, 0) >= program.uses_per_encounter:
            raise ValueError("Power encounter limit reached")
        if any(actor["attributes"][key] < minimum for key, minimum in program.minimum_attributes):
            raise ValueError("Power attribute prerequisite is unmet")
        conditions = {condition["definition"]["id"] for condition in actor["conditions"]}
        if not set(program.required_conditions) <= conditions or set(program.forbidden_conditions) & conditions:
            raise ValueError("Power condition prerequisite is unmet")
        if power.source_kind == "ITEM":
            if "loadout" not in actor:
                raise ValueError("Item power has no actual owned loadout")
            item, item_power, interaction = gear.validate_use(gear.decode(actor["loadout"]), power.id)
            if type(item) is gear.Item and any(actor["attributes"][key] < minimum for key, minimum in item.minimum_attributes):
                raise ValueError("Item activation prerequisite is unmet")
            if interaction and (actor["budget"]["item_interaction"] < interaction or self.blocked(actor, "ITEM_INTERACTION")):
                raise ValueError("Item retrieval interaction is unavailable")
        rows(targets, program.max_targets, 1)
        if any(type(target_id) is not str for target_id in targets) or len(set(targets)) != len(targets):
            raise ValueError("Targets must be unique actor IDs")
        for target_id in targets:
            target = self.actor(target_id)
            if target["hp"] <= 0:
                raise ValueError("This runtime does not target incapacitated creatures")
            relation = program.target_kind
            if ((relation == "SELF" and target_id != actor["id"]) or
                    (relation == "ALLY" and target["team"] != actor["team"]) or
                    (relation == "ENEMY" and target["team"] == actor["team"])):
                raise ValueError("Target relationship is illegal")
            legality = legal_target(point(actor["position"]), point(target["position"]), power.range_mm, self.boxes)
            if not legality["legal"]:
                raise ValueError(legality["reason"])
        # Conflicting definitions must fail before even an attack/save die is drawn.
        planned = {}
        for effect, _ in self.effects(actor, power):
            for recipient_id in ([actor["id"]] if effect.recipient == "CASTER" else targets):
                if effect.kind != "CONDITION":
                    continue
                definition = asdict(effect.condition)
                # State uses JSON-compatible arrays; comparing the canonical shape matters.
                definition["blocks"] = list(definition["blocks"])
                key = (recipient_id, definition["id"])
                existing = next((row["definition"] for row in self.actor(recipient_id)["conditions"]
                                 if row["definition"]["id"] == definition["id"]), None)
                previous = planned.get(key, existing)
                if previous and previous != definition and definition["stacking"] != "REPLACE":
                    raise ValueError("Condition ID has conflicting mechanical definitions")
                planned[key] = definition
        return program

    def effects(self, actor, power):
        result = [(effect, "BASE") for effect in power.program.effects]
        for imprint in actor["imprints"]:
            if imprint["parent_id"] == power.id:
                rider = decode_rider(imprint["rider"])
                result.extend((effect, rider.trigger) for effect in rider.effects)
        return result

    def activate(self, actor, power, targets, trigger=None, *, permission=None):
        program = self.validate_use(actor, power, targets, trigger, permission=permission)
        actor["mp"] -= power.mp_cost
        actor["sta"] -= power.sta_cost
        if power.activation != "PASSIVE":
            self.budget(actor, power.activation.lower())
        item_receipt = None
        if power.source_kind == "ITEM":
            updated, item_receipt = gear.spend(gear.decode(actor["loadout"]), power.id)
            if item_receipt["item_interaction_cost"]:
                self.budget(actor, "item_interaction", item_receipt["item_interaction_cost"])
            self.refresh_gear(actor, updated)
        actor["uses_turn"][power.id] = actor["uses_turn"].get(power.id, 0) + 1
        actor["uses_encounter"][power.id] = actor["uses_encounter"].get(power.id, 0) + 1
        if program.cooldown_turns:
            actor["cooldowns"][power.id] = actor["turn"] + program.cooldown_turns + 1
        entry = {"actor_id": actor["id"], "ability_id": power.id, "activation": power.activation,
                 "trigger": trigger, "mp_cost": power.mp_cost, "sta_cost": power.sta_cost, "targets": []}
        self.ledger.append(entry)
        if item_receipt is not None:
            entry["item_expenditure"] = item_receipt
        if self.preview:
            entry["outcome"] = "Not rolled or resolved until approval"
            return
        outcomes = []
        for target_id in targets:
            target = self.actor(target_id)
            resolution = program.resolution
            attribute_bonus = modifier(actor["attributes"][resolution.attribute]) if resolution.attribute else 0
            outcome = {"target_id": target_id, "success": True, "critical": False, "effects": []}
            if resolution.kind == "ATTACK":
                natural = self.dice.roll(20)
                bonus = attribute_bonus + resolution.bonus + self.bonus(actor, "attack_bonus")
                defense = target["def"] + self.bonus(target, "defense_bonus")
                outcome.update(natural=natural, total=natural + bonus, defense=defense,
                               success=natural == 20 or (natural != 1 and natural + bonus >= defense),
                               critical=natural == 20)
            elif resolution.kind == "SAVE":
                dc = resolution.dc_base + attribute_bonus + resolution.bonus
                natural = self.dice.roll(20)
                total = natural + modifier(target["attributes"][resolution.save_attribute])
                saved = natural == 20 or (natural != 1 and total >= dc)
                outcome.update(natural=natural, total=total, dc=dc, success=not saved)
            outcomes.append(outcome)
            entry["targets"].append(outcome)
            for effect, source in self.effects(actor, power):
                if effect.recipient == "TARGET":
                    self.effect(actor, target, effect, outcome, source)
        # Caster effects apply once, even when a power has many targets.
        caster_outcome = {"success": any(row["success"] for row in outcomes), "critical": False, "effects": []}
        for effect, source in self.effects(actor, power):
            if effect.recipient == "CASTER":
                self.effect(actor, actor, effect, caster_outcome, source)
        entry["caster_effects"] = caster_outcome["effects"]

    def effect(self, caster, target, effect, outcome, source):
        if target["hp"] <= 0 and effect.kind in ("DAMAGE", "HEAL"):
            return  # No further damage rolls or unsupported revival after incapacitation.
        gated = effect.on_success and source != "EXECUTION"
        if source == "SUCCESS" and not outcome["success"]:
            return
        if gated and not outcome["success"] and not effect.save_half:
            return
        result = {"kind": effect.kind, "recipient_id": target["id"], "source": source}
        if effect.amount is not None:
            amount, roll = effect.amount.resolve(caster["attributes"], self.dice,
                                                 effect.kind == "DAMAGE" and source == "BASE" and outcome["critical"])
            if effect.save_half and not outcome["success"]:
                amount //= 2
            result.update(amount=amount, **roll)
        if effect.kind == "DAMAGE":
            numerator, denominator = target["resistances"].get(effect.damage_type, [1, 1])
            damage = amount * numerator // denominator
            if damage:
                self.react(target, damage)
            absorbed = min(damage, target["ward"]["amount"] if target["ward"] else 0)
            if absorbed:
                target["ward"]["amount"] -= absorbed
            lost = min(target["hp"], damage - absorbed)
            target["hp"] -= lost
            result.update(damage_type=effect.damage_type, multiplier=[numerator, denominator],
                          mitigated=amount - damage, ward_absorbed=absorbed, hp_lost=lost)
        elif effect.kind in ("HEAL", "RESTORE_MP", "RESTORE_STA"):
            resource = {"HEAL": "hp", "RESTORE_MP": "mp", "RESTORE_STA": "sta"}[effect.kind]
            restored = min(amount, target[resource + "_max"] - target[resource])
            target[resource] += restored
            result["restored"] = restored
        elif effect.kind == "WARD":
            # This primitive uses one non-stacking temporary HP pool.
            if not target["ward"] or amount > target["ward"]["amount"]:
                target["ward"] = {"amount": amount, "expires_turn": target["turn"] + effect.duration_turns}
            result["temporary_hp"] = target["ward"]["amount"]
        elif effect.kind == "CONDITION":
            definition = asdict(effect.condition)
            definition["blocks"] = list(definition["blocks"])
            prior = next((row for row in target["conditions"] if row["definition"]["id"] == definition["id"]), None)
            before = self.bonus(target, "movement_penalty_mm")
            if prior is None or definition["stacking"] != "IGNORE":
                if prior:
                    target["conditions"].remove(prior)
                target["conditions"].append({"definition": definition,
                    "expires_turn": target["turn"] + definition["duration_turns"]})
                penalty = max(0, self.bonus(target, "movement_penalty_mm") - before)
                target["budget"]["movement_mm"] = max(0, target["budget"]["movement_mm"] - penalty)
            result["condition_id"] = definition["id"]
        elif effect.kind == "REMOVE_CONDITION":
            target["conditions"] = [row for row in target["conditions"] if row["definition"]["id"] != effect.condition_id]
            result["condition_id"] = effect.condition_id
        outcome["effects"].append(result)

    def powers(self, actor):
        result = [decode_ability(value) for value in actor["abilities"]]
        if "loadout" in actor:
            loadout = gear.decode(actor["loadout"])
            result.extend(power.ability for item in (*loadout.items, *loadout.supplies) for power in item.powers)
        return result

    def automatic(self, actor, trigger):
        for power in self.powers(actor):
            if power.activation == "PASSIVE" and power.program.passive_trigger == trigger:
                try:
                    self.validate_use(actor, power, [actor["id"]], trigger)
                except ValueError:
                    continue  # A failed prerequisite is not an activation.
                self.activate(actor, power, [actor["id"]], trigger)

    def react(self, actor, damage):
        # The committed policy is explicit in this sandbox, not inferred player consent.
        if actor["reaction_policy"] != "MITIGATE" or (actor["ward"] and actor["ward"]["amount"] >= damage):
            return
        for power in self.powers(actor):
            if power.activation != "REACTION":
                continue
            # Limited encounter charges are conserved by this simple renewable-only policy.
            if power.program.uses_per_encounter is not None:
                continue
            try:
                self.validate_use(actor, power, [actor["id"]], "INCOMING_DAMAGE")
            except ValueError:
                continue
            self.activate(actor, power, [actor["id"]], "INCOMING_DAMAGE")
            return

    def start_turn(self, actor):
        self.settle_summons()
        actor["turn"] += 1
        actor["movement_spent_mm"] = 0
        actor["uses_turn"] = {}
        actor["budget"] = asdict(TurnBudget(movement_mm=max(0, actor["movement_mm"] - self.bonus(actor, "movement_penalty_mm"))))
        self.automatic(actor, "TURN_START")
        if "summon" not in actor:
            for unit in list(self.live_summons(actor["id"])):
                self.start_turn(unit)

    def finish_turn(self, actor):
        self.automatic(actor, "TURN_END")
        actor["conditions"] = [row for row in actor["conditions"] if row["expires_turn"] > actor["turn"]]
        if actor["ward"] and actor["ward"]["expires_turn"] <= actor["turn"]:
            actor["ward"] = None

    def move_actor(self, actor, path):
        if actor["hp"] <= 0 or self.blocked(actor, "MOVEMENT"):
            raise ValueError("Movement is blocked by incapacitation or a condition")
        origin, distance = point(actor["position"]), 0
        for waypoint in rows(path, 100, 1):
            target = point(waypoint)
            if any(intersects(origin, target, box) for box in self.movement_boxes(actor)):
                raise ValueError("Movement path intersects solid geometry or a blocking creature")
            square = sum((getattr(target, axis) - getattr(origin, axis)) ** 2 for axis in ("x", "y", "z"))
            floor = isqrt(square)
            distance += floor + (floor * floor != square)
            origin = target
        if distance:
            self.budget(actor, "movement_mm", distance)
            actor["movement_spent_mm"] = actor.get("movement_spent_mm", 0) + distance
        actor["position"] = [origin.x, origin.y, origin.z]
        self.ledger.append({"actor_id": actor["id"], "movement_mm": distance,
                            "path": deepcopy(path), "position": actor["position"]})

    def complete(self):
        self.settle_summons()
        return len({row["team"] for row in self.actors.values() if row["hp"] > 0}) <= 1

    def advance_turn(self, actor):
        index, elapsed = self.state["order"].index(actor["id"]), 0
        for offset in range(1, len(self.state["order"]) + 1):
            if index + offset == len(self.state["order"]):
                self.state["round"] += 1
                elapsed = 6
            following = self.actor(self.state["order"][(index + offset) % len(self.state["order"])])
            if following["hp"] <= 0:
                continue
            self.state["active"] = following["id"]
            self.start_turn(following)
            if following["hp"] > 0 or self.complete():
                break
        return elapsed

    def run(self, kind, payload):
        elapsed = 0
        if kind == "start_combat":
            exact(payload, ())
            if self.state["status"] != "ready":
                raise ValueError("Encounter is already started")
            self.state["status"] = "active"
            self.start_turn(self.actor(self.state["active"]))
        elif kind in ("manifest_summons", "command_summons"):
            key = "placements" if kind == "manifest_summons" else "orders"
            exact(payload, ("actor_id", "ability_id", key))
            actor = self.ready(payload["actor_id"])
            power = self.controlled_power(actor, payload["ability_id"])
            if kind == "manifest_summons":
                self.manifest_summons(actor, power, payload[key])
            else:
                self.command_summons(actor, power, payload[key])
        elif kind in ("use_ability", "use_item"):
            exact(payload, ("actor_id", "ability_id", "target_ids") + (("item_id",) if kind == "use_item" else ()))
            actor = self.ready(payload["actor_id"])
            power = next((power for power in self.powers(actor) if power.id == payload["ability_id"]), None)
            if power is None:
                raise ValueError("Ability is not owned by this actor")
            if kind == "use_item":
                if power.source_kind != "ITEM" or power.source_id != payload["item_id"]:
                    raise ValueError("Ability does not belong to that item")
            self.activate(actor, power, payload["target_ids"])
        elif kind in ("equip_item", "unequip_item", "retrieve_item"):
            exact(payload, ("actor_id", "item_id") + (("slots",) if kind == "equip_item" else ()))
            actor = self.ready(payload["actor_id"])
            if "loadout" not in actor:
                raise ValueError("Actor has no owned equipment ledger")
            loadout = gear.decode(actor["loadout"])
            if kind == "retrieve_item":
                updated, receipt = gear.retrieve(loadout, payload["item_id"])
            else:
                slots = tuple(rows(payload["slots"], 16)) if kind == "equip_item" else ()
                updated, receipt = gear.change_equipment(loadout, payload["item_id"], slots)
                if not receipt["hand_only"]:
                    raise ValueError("Body equipment changes require preparation outside combat")
            if self.blocked(actor, receipt["combat_cost"].upper()):
                raise ValueError("Item manipulation is blocked by a condition")
            self.budget(actor, receipt["combat_cost"])
            self.refresh_gear(actor, updated)
            self.ledger.append({"actor_id": actor["id"], **receipt, "elapsed_seconds": 0})
        elif kind == "combat_move":
            exact(payload, ("actor_id", "path"))
            actor = self.ready(payload["actor_id"])
            self.move_actor(actor, payload["path"])
        elif kind == "end_turn":
            exact(payload, ("actor_id",))
            actor = self.ready(payload["actor_id"])
            self.finish_turn(actor)
            self.summon_phase(actor)
            if not self.preview and self.complete():
                self.state["status"] = "complete"
                return {"ledger": self.ledger, "elapsed_seconds": 6, "preview": False, "rng": self.dice.source}
            elapsed += self.advance_turn(actor)
        else:
            raise ValueError("Unsupported combat command")
        if not self.preview and not self.complete() and self.actor(self.state["active"])["hp"] <= 0:
            elapsed += self.advance_turn(self.actor(self.state["active"]))
        if not self.preview and self.complete():
            self.state["status"] = "complete"
            elapsed += 6  # Account for the final partial round exactly once.
        return {"ledger": self.ledger, "elapsed_seconds": elapsed, "preview": self.preview,
                "rng": "No draws during preview" if self.preview else self.dice.source}


def apply(encounter, kind, payload, dice, *, preview=False):
    projected = deepcopy(encounter)
    receipt = Runtime(projected, dice, preview).run(kind, payload)
    projected["actors"] = {key: actor for key, actor in projected["actors"].items()
                           if not actor.get("summon", {}).get("departed")}
    return projected, receipt
