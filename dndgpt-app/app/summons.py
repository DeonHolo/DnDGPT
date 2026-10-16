"""Typed summon laws; neither a creature catalogue nor a global summon limit."""
from dataclasses import dataclass

from .abilities import Ability, decode as ability
from .contracts import construct, pairs, sequence, text
from .powers import bind, immutable, member
from .rules import ATTRIBUTES, integer


@dataclass(frozen=True)
class Behavior:
    rule: str
    ability_id: str | None = None
    can_move: bool = False
    move_and_act: bool = False

    def __post_init__(self):
        member(self.rule, ("WAIT", "NEAREST_HOSTILE"), "autonomous behavior")
        if any(type(value) is not bool for value in (self.can_move, self.move_and_act)):
            raise ValueError("Behavior permissions must be boolean")
        if self.rule == "WAIT":
            if self.ability_id is not None or self.can_move or self.move_and_act:
                raise ValueError("Waiting behavior cannot grant actions")
        else:
            text(self.ability_id, "autonomous ability")
        if self.move_and_act and not self.can_move:
            raise ValueError("Move-and-act behavior requires movement permission")


@dataclass(frozen=True)
class Unit:
    id: str
    name: str
    attributes: tuple
    hp: int
    defense: int
    movement_mm: int
    half_extents_mm: tuple[int, int, int]
    abilities: tuple[Ability, ...]
    control: str
    utility: str
    weaknesses: str
    special_interactions: str
    behavior: Behavior = Behavior("WAIT")
    mp: int = 0
    sta: int = 0
    blocks_movement: bool = False
    reaction_policy: str = "CONSERVE"

    def __post_init__(self):
        for value in (self.id, self.name, self.utility, self.weaknesses, self.special_interactions):
            text(value, "summon definition")
        if type(self.attributes) is not tuple or len(self.attributes) != 5 or set(dict(self.attributes)) != set(ATTRIBUTES):
            raise ValueError("Summon requires five actual attributes")
        for _, score in self.attributes:
            integer(score, 1, 20, "summon attribute")
        for value, minimum, name in ((self.hp, 1, "HP"), (self.mp, 0, "MP"), (self.sta, 0, "STA")):
            integer(value, minimum, 1000000000, "summon " + name)
        integer(self.defense, 1, 1000000, "summon DEF")
        integer(self.movement_mm, 0, 100000000, "summon movement")
        if type(self.half_extents_mm) is not tuple or len(self.half_extents_mm) != 3:
            raise ValueError("Summon requires an actual three-dimensional footprint")
        for amount in self.half_extents_mm:
            integer(amount, 1, 1000000, "summon half extent")
        immutable(self.abilities, Ability, "summon abilities", 32)
        if len({power.id for power in self.abilities}) != len(self.abilities):
            raise ValueError("Duplicate summon ability ID")
        for power in self.abilities:
            program = bind(power)
            if power.source_kind != "SUMMON" or power.source_id != self.id:
                raise ValueError("Summon powers require actual template provenance")
            if program.summon is not None or program.command is not None:
                raise ValueError("Nested summoners/commanders require an additional runtime context")
        member(self.control, ("COMMANDED", "AUTONOMOUS"), "summon control")
        member(self.reaction_policy, ("CONSERVE", "MITIGATE"), "summon Reaction policy")
        if type(self.behavior) is not Behavior or type(self.blocks_movement) is not bool:
            raise ValueError("Summon behavior and blocking must be explicit")
        if self.control == "COMMANDED" and self.behavior.rule != "WAIT":
            raise ValueError("Commanded summons cannot gain autonomous actions")
        if self.behavior.rule != "WAIT":
            power = next((row for row in self.abilities if row.id == self.behavior.ability_id), None)
            if power is None or power.activation != "ACTION" or bind(power).target_kind != "ENEMY":
                raise ValueError("Autonomous hostile behavior requires an actual Action against enemies")


@dataclass(frozen=True)
class Manifest:
    family: str
    units: tuple[Unit, ...]
    max_active: int
    duration_rounds: int | None
    replacement: str = "REJECT"
    owner_loss: str = "DISMISS"
    destruction: str = "DISMISS"
    expiry: str = "DISMISS"

    def __post_init__(self):
        text(self.family, "summon family")
        immutable(self.units, Unit, "manifested formation", 32)
        if len({unit.id for unit in self.units}) != len(self.units):
            raise ValueError("Formation template IDs must be distinct")
        integer(self.max_active, len(self.units), 128, "declared active summon cap")
        if self.duration_rounds is not None:
            integer(self.duration_rounds, 1, 100000, "summon round duration")
        member(self.replacement, ("REJECT", "REPLACE_FAMILY"), "summon replacement")
        for value in (self.owner_loss, self.destruction, self.expiry):
            member(value, ("DISMISS",), "summon departure effect")


@dataclass(frozen=True)
class Command:
    family: str
    max_units: int
    range_mm: int
    can_move: bool
    can_act: bool
    move_and_act: bool
    requires_line_of_effect: bool = True

    def __post_init__(self):
        text(self.family, "command family")
        integer(self.max_units, 1, 128, "units per shared command")
        integer(self.range_mm, 0, 10000000, "command range")
        if any(type(value) is not bool for value in (self.can_move, self.can_act, self.move_and_act, self.requires_line_of_effect)):
            raise ValueError("Command permissions must be boolean")
        if not (self.can_move or self.can_act) or (self.move_and_act and not (self.can_move and self.can_act)):
            raise ValueError("Command must grant explicit compatible operations")


def manifest(value):
    return construct(Manifest, value, {"units": lambda rows: tuple(construct(Unit, row, {
        "attributes": pairs, "half_extents_mm": sequence,
        "abilities": lambda powers: tuple(ability(power) for power in sequence(powers)),
        "behavior": lambda data: construct(Behavior, data)}) for row in sequence(rows))})


def command(value):
    return construct(Command, value)
