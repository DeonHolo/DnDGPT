"""Summon execution mixed into the shared combat transaction/resolver."""
from copy import deepcopy
from dataclasses import asdict
import json
from math import isqrt

from .powers import bind
from .rules import TurnBudget, integer
from .spatial import Point, SolidBox, in_range, intersects, legal_target


def position(value):
    if type(value) is not list or len(value) != 3:
        raise ValueError("Position requires three integer coordinates")
    return Point(*(integer(n, -1000000000, 1000000000, "coordinate") for n in value))


def entries(value, maximum):
    if type(value) is not list or not 1 <= len(value) <= maximum:
        raise ValueError("Explicit bounded summon orders are required")
    return value


def fields(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError("Invalid summon order fields")


def expanded(box, extent):
    return SolidBox(Point(*(getattr(box.minimum, axis) - size for axis, size in zip(("x", "y", "z"), extent))),
                    Point(*(getattr(box.maximum, axis) + size for axis, size in zip(("x", "y", "z"), extent))))


class SummonRuntime:
    def movement_boxes(self, actor, *, occupied=False):
        extent = actor.get("half_extents_mm", [0, 0, 0])
        result = [expanded(box, extent) for box in self.boxes]
        for other in self.actors.values():
            if other["id"] == actor["id"] or other["hp"] <= 0:
                continue
            if not occupied and not other.get("blocks_movement", False):
                continue
            center, half = other["position"], other.get("half_extents_mm", [0, 0, 0])
            box = SolidBox(Point(*(n - d for n, d in zip(center, half))), Point(*(n + d for n, d in zip(center, half))))
            result.append(expanded(box, extent))
        return result

    def controlled_power(self, actor, ability_id):
        power = next((power for power in self.powers(actor) if power.id == ability_id), None)
        if power is None:
            raise ValueError("Ability is not owned by this actor")
        return power

    def live_summons(self, owner=None, family=None):
        return [row for row in self.actors.values() if row["hp"] > 0 and "summon" in row
                and (owner is None or row["summon"]["owner_id"] == owner)
                and (family is None or row["summon"]["family"] == family)]

    def departure(self, unit, reason):
        if unit["summon"].get("departed"):
            return
        self.ledger.append({"summon_id": unit["id"], "departure": reason,
                            "owner_id": unit["summon"]["owner_id"], "hp_before_departure": unit["hp"]})
        unit["summon"]["departed"] = reason
        unit["hp"] = 0

    def settle_summons(self):
        for unit in list(self.actors.values()):
            if "summon" not in unit or unit["summon"].get("departed"):
                continue
            meta = unit["summon"]
            if unit["hp"] <= 0:
                self.departure(unit, "DESTROYED")
            elif self.actor(meta["owner_id"])["hp"] <= 0:
                self.departure(unit, "OWNER_LOST")
            elif meta["expires_round"] is not None and self.state["round"] >= meta["expires_round"]:
                self.departure(unit, "EXPIRED")

    def manifest_summons(self, owner, power, placements):
        self.validate_use(owner, power, [owner["id"]], permission="MANIFEST")
        plan = bind(power).summon
        if plan is None:
            raise ValueError("This ability does not manifest summons")
        entries(placements, len(plan.units))
        if len(placements) != len(plan.units):
            raise ValueError("Place exactly the declared formation")
        existing = self.live_summons(owner["id"], plan.family)
        replacing = existing if plan.replacement == "REPLACE_FAMILY" else []
        if len(existing) - len(replacing) + len(plan.units) > plan.max_active:
            raise ValueError("Declared active summon cap exceeded")
        if len(self.live_summons()) - len(replacing) + len(plan.units) > 128:
            raise ValueError("Development encounter capacity exceeded; no gameplay cap is inferred")
        # Spatial and capacity preflight happens before owner resource costs or RNG.
        projected = deepcopy(self.state)
        check = type(self)(projected, self.dice, True)
        for unit in replacing:
            check.actors[unit["id"]]["hp"] = 0
        prepared = []
        serial = self.state.get("summon_serial", 0)
        for definition, placement in zip(plan.units, placements):
            fields(placement, ("template_id", "position"))
            if placement["template_id"] != definition.id:
                raise ValueError("Formation placements must name their actual template in order")
            where = position(placement["position"])
            legality = legal_target(position(owner["position"]), where, power.range_mm, self.boxes)
            if not legality["legal"]:
                raise ValueError(legality["reason"])
            serial += 1
            identity = "summon-" + str(serial)
            while identity in check.actors:
                serial += 1
                identity = "summon-" + str(serial)
            actor = {"id": identity, "name": definition.name, "team": owner["team"],
                "attributes": dict(definition.attributes), "hp": definition.hp, "hp_max": definition.hp,
                "mp": definition.mp, "mp_max": definition.mp, "sta": definition.sta, "sta_max": definition.sta,
                "def": definition.defense, "movement_mm": definition.movement_mm,
                "position": placement["position"], "half_extents_mm": definition.half_extents_mm,
                "blocks_movement": definition.blocks_movement, "abilities": [asdict(row) for row in definition.abilities],
                "imprints": [], "resistances": {}, "reaction_policy": definition.reaction_policy, "turn": owner["turn"],
                "movement_spent_mm": 0, "budget": asdict(TurnBudget(movement_mm=definition.movement_mm)),
                "conditions": [], "ward": None, "cooldowns": {}, "uses_turn": {}, "uses_encounter": {},
                "summon": {"owner_id": owner["id"], "family": plan.family, "source_ability_id": power.id,
                    "source_rarity": power.rarity, "definition": asdict(definition), "created_round": self.state["round"],
                    "expires_round": None if plan.duration_rounds is None else self.state["round"] + plan.duration_rounds,
                    "last_autonomous_round": 0}}
            actor = json.loads(json.dumps(actor))
            if any(intersects(where, where, box) for box in check.movement_boxes(actor, occupied=True)):
                raise ValueError("Summon footprint overlaps solid geometry or an occupied position")
            check.actors[identity] = actor
            prepared.append(actor)
        self.activate(owner, power, [owner["id"]], permission="MANIFEST")
        for unit in replacing:
            self.departure(unit, "REPLACED")
        self.state["summon_serial"] = serial
        for unit in prepared:
            self.actors[unit["id"]] = unit
            self.ledger.append({"summon_id": unit["id"], "manifested": True, "owner_id": owner["id"],
                                "template_id": unit["summon"]["definition"]["id"], "position": unit["position"]})

    def command_summons(self, owner, power, orders, *, checked=False):
        plan = bind(power).command
        if plan is None:
            raise ValueError("This ability does not grant summon commands")
        entries(orders, plan.max_units)
        if not checked:
            projected = deepcopy(self.state)
            type(self)(projected, self.dice, True).command_summons(
                projected["actors"][owner["id"]], power, orders, checked=True)
        self.activate(owner, power, [owner["id"]], permission="COMMAND_OWNER")
        self.settle_summons()
        seen = set()
        for order in orders:
            fields(order, ("summon_id",), ("path", "ability_id", "target_ids"))
            unit = self.actor(order["summon_id"])
            meta = unit.get("summon", {})
            if (unit["id"] in seen or meta.get("owner_id") != owner["id"] or meta.get("family") != plan.family
                    or unit["hp"] <= 0 or meta.get("definition", {}).get("control") != "COMMANDED"):
                if not self.preview and not checked:
                    self.ledger.append({"summon_id": unit["id"], "skipped": "Summon no longer available"})
                    continue
                raise ValueError("Command requires distinct living owned commanded summons of that family")
            seen.add(unit["id"])
            if not in_range(position(owner["position"]), position(unit["position"]), plan.range_mm):
                raise ValueError("Summon is outside its actual command range")
            if plan.requires_line_of_effect and not legal_target(position(owner["position"]), position(unit["position"]), plan.range_mm, self.boxes)["legal"]:
                raise ValueError("Command line of effect is blocked")
            moving, acting = "path" in order, "ability_id" in order
            if ((not moving and not acting) or (moving and not plan.can_move) or (acting and not plan.can_act)
                    or (moving and acting and not plan.move_and_act) or ("target_ids" in order) != acting):
                raise ValueError("Command cannot grant undeclared move/act combinations")
            if moving:
                try:
                    self.move_actor(unit, order["path"])
                except ValueError as error:
                    if self.preview or checked:
                        raise
                    self.ledger.append({"summon_id": unit["id"], "skipped": str(error)})
                    continue
            if acting:
                action = self.controlled_power(unit, order["ability_id"])
                try:
                    self.validate_use(unit, action, order["target_ids"], permission="COMMANDED")
                except ValueError as error:
                    if self.preview or checked:
                        raise
                    self.ledger.append({"summon_id": unit["id"], "skipped": str(error)})
                    continue  # Earlier effects may have incapacitated the planned target.
                self.activate(unit, action, order["target_ids"], permission="COMMANDED")

    def summon_phase(self, owner):
        self.settle_summons()
        for unit in list(self.live_summons(owner["id"])):
            meta = unit["summon"]
            if meta["definition"]["control"] == "AUTONOMOUS" and meta["last_autonomous_round"] != self.state["round"]:
                meta["last_autonomous_round"] = self.state["round"]
                behavior = meta["definition"]["behavior"]
                if behavior["rule"] == "NEAREST_HOSTILE":
                    self.autonomous_summon(unit, behavior)
            self.finish_turn(unit)
            self.settle_summons()

    def autonomous_summon(self, unit, behavior):
        power = self.controlled_power(unit, behavior["ability_id"])
        targets = sorted((row for row in self.actors.values() if row["hp"] > 0 and row["team"] != unit["team"]),
            key=lambda row: (sum((a-b)**2 for a,b in zip(row["position"], unit["position"])), row["id"]))
        if not targets:
            return
        target = targets[0]
        moved = False
        if behavior["can_move"] and not in_range(position(unit["position"]), position(target["position"]), power.range_mm):
            delta = [a-b for a,b in zip(target["position"], unit["position"])]
            square = sum(n*n for n in delta)
            floor = isqrt(square)
            distance = floor + (floor*floor != square)
            travel = min(unit["budget"]["movement_mm"], max(0, distance - power.range_mm))
            if travel:
                end = [n + (1 if d >= 0 else -1) * (abs(d)*travel//distance) for n,d in zip(unit["position"], delta)]
                before = list(unit["position"])
                try:
                    self.move_actor(unit, [end])
                    moved = unit["position"] != before
                except ValueError as error:
                    self.ledger.append({"summon_id": unit["id"], "held": str(error)})
        if moved and not behavior["move_and_act"]:
            return
        try:
            self.validate_use(unit, power, [target["id"]], permission="AUTONOMOUS")
        except ValueError as error:
            self.ledger.append({"summon_id": unit["id"], "held": str(error)})
            return
        self.activate(unit, power, [target["id"]], permission="AUTONOMOUS")
