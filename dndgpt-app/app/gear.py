"""Owned Gear-First loadouts and explicit starting equipment calculations.

Declared flat bonuses and bounded item programs share the source power resolver.
No enchantment or effect is inferred from prose or rarity.
"""
from dataclasses import asdict, dataclass, replace
import json

from .contracts import construct, pairs, sequence
from .abilities import Ability, decode as decode_ability, preview as power_preview
from .powers import bind, label, member
from .rules import ATTRIBUTES, EQUIPMENT_SLOTS, RARITIES, derived, integer


def records(values, cls, maximum=1000):
    if type(values) is not tuple or len(values) > maximum or any(type(value) is not cls for value in values):
        raise ValueError("Expected bounded immutable gear records")


def unique_pairs(values, allowed=None):
    if type(values) is not tuple:
        raise ValueError("Gear fields must be immutable key/value pairs")
    keys = []
    for row in values:
        if type(row) is not tuple or len(row) != 2:
            raise ValueError("Invalid gear key/value pair")
        label(row[0])
        keys.append(row[0])
    if len(set(keys)) != len(keys) or (allowed is not None and not set(keys) <= set(allowed)):
        raise ValueError("Duplicate or unsupported gear field")


@dataclass(frozen=True)
class ItemPower:
    ability: Ability
    quantity_cost: int = 0
    charges_cost: int = 0
    battery_cost: int = 0
    ammunition_cost: int = 0
    requires_equipped: bool = True
    requires_free_hand: bool = True

    def __post_init__(self):
        if type(self.ability) is not Ability or self.ability.source_kind != "ITEM":
            raise ValueError("Item power must retain ITEM provenance")
        bind(self.ability)
        for field in ("quantity_cost", "charges_cost", "battery_cost", "ammunition_cost"):
            integer(getattr(self, field), 0, 1000000, field)
        if type(self.requires_equipped) is not bool or type(self.requires_free_hand) is not bool:
            raise ValueError("Item use restrictions must be boolean")
        if self.ability.activation == "REACTION":
            raise ValueError("Item Reaction authorization windows are not implemented")
        if self.ability.activation == "PASSIVE" and (not self.requires_equipped or any(
                getattr(self, field) for field in ("quantity_cost", "charges_cost", "battery_cost", "ammunition_cost"))):
            raise ValueError("Supported item passive must be equipped and have no activation expenditure")


@dataclass(frozen=True)
class Meter:
    current: int
    maximum: int

    def __post_init__(self):
        integer(self.maximum, 0, 1000000, "item capacity")
        integer(self.current, 0, self.maximum, "item remaining")


@dataclass(frozen=True)
class Bonuses:
    hp_max: int = 0
    mp_max: int = 0
    sta_max: int = 0
    defense: int = 0
    movement_mm: int = 0
    carry_grams: int = 0

    def __post_init__(self):
        for name in ("hp_max", "mp_max", "sta_max"):
            integer(getattr(self, name), -100000, 100000, name)
        integer(self.defense, -100, 100, "gear defense")
        integer(self.movement_mm, -100000, 100000, "gear movement")
        integer(self.carry_grams, -1000000, 1000000, "gear carry capacity")


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    rarity: str
    weight_grams: int
    location: str
    provenance: str
    quantity: int = 1
    equip_modes: tuple = ()
    bonuses: Bonuses = Bonuses()
    condition: str = "SERVICEABLE"
    minimum_attributes: tuple = ()
    incompatible_items: tuple[str, ...] = ()
    ownership: str = "OWNED"
    return_obligation: str | None = None
    charges: Meter | None = None
    battery: Meter | None = None
    ammunition: Meter | None = None
    powers: tuple[ItemPower, ...] = ()
    access: str = "ACCESSIBLE"
    equip_seconds: int = 6
    retrieval_seconds: int = 6

    def __post_init__(self):
        for field in ("id", "name", "provenance"):
            label(getattr(self, field))
        member(self.rarity, RARITIES, "item rarity")
        member(self.location, ("EQUIPPED", "CARRIED"), "starting item location")
        member(self.condition, ("SERVICEABLE", "WORN", "DAMAGED", "BROKEN"), "item condition")
        member(self.ownership, ("OWNED", "BORROWED"), "item ownership")
        member(self.access, ("ACCESSIBLE", "PACKED"), "item access")
        integer(self.equip_seconds, 1, 86400, "equipment preparation time")
        integer(self.retrieval_seconds, 1, 86400, "item retrieval time")
        if self.ownership == "BORROWED":
            label(self.return_obligation)
        elif self.return_obligation is not None:
            raise ValueError("Owned item cannot have a borrowed return obligation")
        integer(self.weight_grams, 0, 1000000000, "item weight")
        integer(self.quantity, 1, 1000000, "item quantity")
        if type(self.bonuses) is not Bonuses:
            raise ValueError("Item bonuses must be explicit and typed")
        if type(self.equip_modes) is not tuple or len(self.equip_modes) > 16:
            raise ValueError("Invalid equipment modes")
        modes = set()
        for mode in self.equip_modes:
            if type(mode) is not tuple or not mode or len(mode) > 16:
                raise ValueError("Equipment mode must name its occupied slots")
            for slot in mode:
                member(slot, EQUIPMENT_SLOTS, "equipment slot")
            frozen = frozenset(mode)
            if len(frozen) != len(mode) or frozen in modes:
                raise ValueError("Duplicate equipment mode or slot")
            modes.add(frozen)
        unique_pairs(self.minimum_attributes, ATTRIBUTES)
        for _, minimum in self.minimum_attributes:
            integer(minimum, 1, 20, "gear prerequisite")
        if type(self.incompatible_items) is not tuple:
            raise ValueError("Gear incompatibilities must be immutable")
        for value in self.incompatible_items:
            label(value)
        if len(set(self.incompatible_items)) != len(self.incompatible_items) or self.id in self.incompatible_items:
            raise ValueError("Invalid gear incompatibilities")
        for value in (self.charges, self.battery, self.ammunition):
            if value is not None and type(value) is not Meter:
                raise ValueError("Item pools must be typed or explicitly inapplicable")
        records(self.powers, ItemPower, 32)
        for power in self.powers:
            if power.ability.source_id != self.id or power.ability.rarity != self.rarity:
                raise ValueError("Item power must match its actual item and rarity")
            for pool in ("charges", "battery", "ammunition"):
                cost = getattr(power, pool + "_cost")
                meter = getattr(self, pool)
                if cost and (meter is None or cost > meter.maximum):
                    raise ValueError("Item power expenditure has no matching capacity")


@dataclass(frozen=True)
class Supply:
    id: str
    name: str
    quantity: int
    unit: str
    bulk_grams: int
    provenance: str
    powers: tuple[ItemPower, ...] = ()
    access: str = "ACCESSIBLE"
    retrieval_seconds: int = 6

    def __post_init__(self):
        for field in ("id", "name", "unit", "provenance"):
            label(getattr(self, field))
        integer(self.quantity, 0, 1000000, "supply amount")
        integer(self.bulk_grams, 0, 1000000000, "aggregate supply bulk")
        if not self.quantity and self.bulk_grams:
            raise ValueError("Empty supply cannot carry phantom bulk")
        member(self.access, ("ACCESSIBLE", "PACKED"), "supply access")
        integer(self.retrieval_seconds, 1, 86400, "supply retrieval time")
        records(self.powers, ItemPower, 32)
        for power in self.powers:
            if (power.ability.source_id != self.id or power.ability.rarity != "COMMON" or power.requires_equipped or
                    power.quantity_cost < 1 or any((power.charges_cost, power.battery_cost, power.ammunition_cost))):
                raise ValueError("Ordinary supply effects require actual common stock expenditure")


@dataclass(frozen=True)
class Funds:
    currency: str
    amount: int
    provenance: str

    def __post_init__(self):
        label(self.currency)
        label(self.provenance)
        integer(self.amount, 0, 1000000000000000, "funds")


@dataclass(frozen=True)
class Loadout:
    items: tuple[Item, ...]
    equipment: tuple
    supplies: tuple[Supply, ...] = ()
    funds: tuple[Funds, ...] = ()

    def __post_init__(self):
        records(self.items, Item)
        records(self.supplies, Supply)
        records(self.funds, Funds, 32)
        ids = [item.id for item in (*self.items, *self.supplies)]
        if len(set(ids)) != len(ids) or len({row.currency for row in self.funds}) != len(self.funds):
            raise ValueError("Duplicate owned item, supply or currency")
        power_ids = [power.ability.id for item in (*self.items, *self.supplies) for power in item.powers]
        if len(set(power_ids)) != len(power_ids):
            raise ValueError("Duplicate item ability ID")
        unique_pairs(self.equipment, EQUIPMENT_SLOTS)
        if set(dict(self.equipment)) != set(EQUIPMENT_SLOTS):
            raise ValueError("Starting loadout needs all sixteen equipment slots")
        owned = {item.id: item for item in self.items}
        occupied = {}
        for slot, item_id in self.equipment:
            if item_id is None:
                continue
            label(item_id)
            if item_id not in owned:
                raise ValueError("Equipped item is not in the owned item ledger")
            occupied.setdefault(item_id, set()).add(slot)
        for item in self.items:
            slots = occupied.get(item.id, set())
            if bool(slots) != (item.location == "EQUIPPED"):
                raise ValueError("Item physical location disagrees with its equipment slots")
            if slots:
                if item.access == "PACKED":
                    raise ValueError("Equipped item cannot remain packed away")
                if item.quantity != 1 or slots not in [set(mode) for mode in item.equip_modes]:
                    raise ValueError("Equipped item must occupy exactly one declared mode")
                if item.condition in ("DAMAGED", "BROKEN"):
                    raise ValueError("Impaired starting gear needs an executable impairment rule before equipping")
                if slots & {"Main Hand", "Off-Hand"} and len(slots) > 1 and slots != {"Main Hand", "Off-Hand"}:
                    raise ValueError("Multi-slot hand gear must occupy both hand slots")
                if set(item.incompatible_items) & occupied.keys():
                    raise ValueError("Incompatible items cannot be equipped together")


def calculate(loadout, attributes):
    if type(loadout) is not Loadout or type(attributes) is not dict or set(attributes) != set(ATTRIBUTES):
        raise ValueError("Loadout calculation requires the complete character attributes")
    stats = derived(attributes)
    for item in loadout.items:
        if item.location != "EQUIPPED":
            continue
        if any(attributes[key] < minimum for key, minimum in item.minimum_attributes):
            raise ValueError("Equipped item prerequisite is unmet")
        bonuses = asdict(item.bonuses)
        stats["def"] += bonuses.pop("defense")
        carry = bonuses.pop("carry_grams")
        # Milligrams/floats are unnecessary: capacity is authoritative in grams.
        stats["carry_capacity_grams"] = stats.get("carry_capacity_grams", stats["carry_capacity_kg"] * 1000) + carry
        for key, amount in bonuses.items():
            stats[key] += amount
    stats.setdefault("carry_capacity_grams", stats["carry_capacity_kg"] * 1000)
    if any(stats[key] < 1 for key in ("hp_max", "mp_max", "sta_max", "def")) or min(stats["movement_mm"], stats["carry_capacity_grams"]) < 0:
        raise ValueError("Equipment creates invalid character statistics")
    stats["carry_capacity_kg"] = stats["carry_capacity_grams"] / 1000
    weight = sum(item.weight_grams * item.quantity for item in loadout.items) + sum(row.bulk_grams for row in loadout.supplies)
    if weight > stats["carry_capacity_grams"]:
        raise ValueError("Starting carried weight exceeds actual capacity")
    def describe(item):
        record = asdict(item)
        record["powers"] = [{**asdict(power), "ability": power_preview(power.ability, attributes)} for power in item.powers]
        return record
    return {"derived": stats, "resources": {resource: stats[resource + "_max"] for resource in ("hp", "mp", "sta")},
            "equipment": dict(loadout.equipment), "items": [describe(item) for item in loadout.items],
            "supplies": [describe(row) for row in loadout.supplies], "funds": [asdict(row) for row in loadout.funds],
            "carried_weight_grams": weight, "inventory_mode": "GEAR_FIRST"}


def item(value):
    return construct(Item, value, {
        "equip_modes": lambda rows: tuple(sequence(row) for row in sequence(rows)),
        "bonuses": lambda row: construct(Bonuses, row), "minimum_attributes": pairs,
        "incompatible_items": sequence, "powers": decode_powers,
        **{key: lambda row: None if row is None else construct(Meter, row) for key in ("charges", "battery", "ammunition")}})


def decode(value):
    return construct(Loadout, value, {
        "items": lambda rows: tuple(item(row) for row in sequence(rows)), "equipment": pairs,
        "supplies": lambda rows: tuple(construct(Supply, row, {"powers": decode_powers}) for row in sequence(rows)),
        "funds": lambda rows: tuple(construct(Funds, row) for row in sequence(rows))})


def encode(loadout):
    return json.loads(json.dumps(asdict(loadout), allow_nan=False))


def decode_powers(values):
    return tuple(construct(ItemPower, row, {"ability": decode_ability}) for row in sequence(values))


def find(loadout, item_id):
    label(item_id)
    result = next((row for row in (*loadout.items, *loadout.supplies) if row.id == item_id), None)
    if result is None:
        raise ValueError("Item is not owned")
    return result


def find_power(loadout, ability_id):
    for item in (*loadout.items, *loadout.supplies):
        for power in item.powers:
            if power.ability.id == ability_id:
                return item, power
    raise ValueError("Item ability is not owned")


def validate_use(loadout, ability_id):
    item, power = find_power(loadout, ability_id)
    equipped = type(item) is Item and item.location == "EQUIPPED"
    if type(item) is Item and item.condition in ("DAMAGED", "BROKEN"):
        raise ValueError("Impaired item cannot activate without a supported impairment rule")
    if power.requires_equipped and not equipped:
        raise ValueError("Item power requires its actual equipped item")
    if item.access == "PACKED":
        raise ValueError("Retrieve the packed item before activation")
    if item.quantity < power.quantity_cost:
        raise ValueError("Insufficient item quantity")
    for pool in ("charges", "battery", "ammunition"):
        cost = getattr(power, pool + "_cost")
        if cost and getattr(item, pool).current < cost:
            raise ValueError("Insufficient item " + pool)
    interaction = not equipped and power.ability.activation != "PASSIVE"
    if interaction and power.requires_free_hand and all(dict(loadout.equipment)[slot] is not None for slot in ("Main Hand", "Off-Hand")):
        raise ValueError("Drawing this item requires a free hand")
    return item, power, int(interaction)


def spend(loadout, ability_id):
    item, power, interaction = validate_use(loadout, ability_id)
    remaining = item.quantity - power.quantity_cost
    if type(item) is Supply:
        replacement = replace(item, quantity=remaining,
                              bulk_grams=item.bulk_grams * remaining // item.quantity)
        updated = replace(loadout, supplies=tuple(replacement if row.id == item.id else row for row in loadout.supplies))
    elif not remaining:
        updated = replace(loadout, items=tuple(row for row in loadout.items if row.id != item.id),
            equipment=tuple((slot, None if value == item.id else value) for slot, value in loadout.equipment))
    else:
        changes = {pool: replace(getattr(item, pool), current=getattr(item, pool).current - getattr(power, pool + "_cost"))
                   for pool in ("charges", "battery", "ammunition") if getattr(power, pool + "_cost")}
        replacement = replace(item, quantity=remaining, **changes)
        updated = replace(loadout, items=tuple(replacement if row.id == item.id else row for row in loadout.items))
    balances = {}
    for pool in ("charges", "battery", "ammunition"):
        meter = getattr(item, pool, None)
        balances[pool + "_before"] = meter.current if meter is not None else None
        balances[pool + "_remaining"] = meter.current - getattr(power, pool + "_cost") if meter is not None and remaining else None
    return updated, {"item_id": item.id, "item_name": item.name, "ability_id": ability_id,
                     "source_provenance": item.provenance,
                     "ownership": item.ownership if type(item) is Item else "OWNED",
                     "return_obligation": item.return_obligation if type(item) is Item else None,
                     "quantity_cost": power.quantity_cost,
                     "quantity_remaining": remaining, "item_interaction_cost": interaction,
                     **{pool + "_cost": getattr(power, pool + "_cost") for pool in ("charges", "battery", "ammunition")}, **balances}


def change_equipment(loadout, item_id, slots):
    item = find(loadout, item_id)
    if type(item) is not Item or type(slots) is not tuple:
        raise ValueError("Only individual gear has equipment slots")
    layout = dict(loadout.equipment)
    for slot in slots:
        member(slot, EQUIPMENT_SLOTS, "equipment slot")
    if len(set(slots)) != len(slots) or (slots and set(slots) not in [set(mode) for mode in item.equip_modes]):
        raise ValueError("Item cannot use those slots")
    old_slots = {slot for slot, value in layout.items() if value == item_id}
    if set(slots) == old_slots:
        raise ValueError("Item already has that equipment state")
    if item.access == "PACKED":
        raise ValueError("Retrieve the packed item before equipping")
    displaced = {layout[slot] for slot in slots if layout[slot] not in (None, item_id)}
    affected = old_slots | set(slots) | {slot for slot, value in layout.items() if value in displaced}
    for slot, value in layout.items():
        if value == item_id or value in displaced:
            layout[slot] = None
    layout.update(dict.fromkeys(slots, item_id))
    changed = replace(loadout, equipment=tuple(layout.items()), items=tuple(
        replace(row, location="EQUIPPED" if slots else "CARRIED") if row.id == item_id else
        replace(row, location="CARRIED") if row.id in displaced else row for row in loadout.items))
    return changed, {"item_id": item_id, "slots": list(slots), "displaced": sorted(displaced),
        "combat_cost": "action" if displaced else "item_interaction",
        "hand_only": affected <= {"Main Hand", "Off-Hand"}, "elapsed_seconds": item.equip_seconds}


def retrieve(loadout, item_id):
    item = find(loadout, item_id)
    if item.access != "PACKED":
        raise ValueError("Item is already accessible")
    if all(dict(loadout.equipment)[slot] is not None for slot in ("Main Hand", "Off-Hand")):
        raise ValueError("Retrieving an item requires a free hand")
    field = "items" if type(item) is Item else "supplies"
    changed = replace(loadout, **{field: tuple(replace(row, access="ACCESSIBLE") if row.id == item_id else row
                                              for row in getattr(loadout, field))})
    return changed, {"item_id": item_id, "combat_cost": "action", "elapsed_seconds": item.retrieval_seconds}


def recalculate(character, loadout=None):
    stats = calculate(loadout, character["attributes"])["derived"] if loadout is not None else derived(character["attributes"])
    character.update(stats)
    for resource in ("hp", "mp", "sta"):
        character[resource] = min(character[resource], stats[resource + "_max"])
    return stats
