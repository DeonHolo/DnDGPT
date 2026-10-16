"""Bounded executable power definitions, never Python/SQL or narrative parsing.

These primitives are extensible, not a class catalogue or a rarity-strength oracle.
Ability activation/cost/range have one source of truth in creation.Ability.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .summons import Manifest, Command

from .contracts import construct, pairs, sequence
from .rules import ATTRIBUTES, integer, modifier


def label(value):
    if type(value) is not str or not value.strip() or len(value) > 128:
        raise ValueError("Mechanical labels require 1..128 characters")


def member(value, values, name):
    if type(value) is not str or value not in values:
        raise ValueError(f"Unsupported {name}")


def immutable(values, cls, name, maximum=32):
    if type(values) is not tuple or not 1 <= len(values) <= maximum or any(type(row) is not cls for row in values):
        raise ValueError(f"Invalid {name}")


@dataclass(frozen=True)
class Formula:
    count: int = 0
    sides: int = 6
    flat: int = 0
    attribute: str | None = None

    def __post_init__(self):
        integer(self.count, 0, 20, "dice count")
        integer(self.sides, 2, 10000, "dice sides")
        integer(self.flat, -100000, 100000, "flat amount")
        if self.attribute is not None:
            member(self.attribute, ATTRIBUTES, "formula attribute")

    def resolve(self, attributes, dice, critical=False):
        rolls = [dice.roll(self.sides) for _ in range(self.count * (2 if critical else 1))]
        bonus = self.flat + (modifier(attributes[self.attribute]) if self.attribute else 0)
        return max(0, sum(rolls) + bonus), {"rolls": rolls, "sides": self.sides, "bonus": bonus, "critical": critical}


@dataclass(frozen=True)
class Resolution:
    kind: str = "AUTO"
    attribute: str | None = None
    bonus: int = 0
    save_attribute: str | None = None
    dc_base: int = 12

    def __post_init__(self):
        member(self.kind, ("AUTO", "ATTACK", "SAVE"), "resolution")
        integer(self.bonus, -20, 20, "resolution bonus")
        integer(self.dc_base, 1, 40, "DC base")
        if self.attribute is not None:
            member(self.attribute, ATTRIBUTES, "casting attribute")
        if self.kind == "SAVE":
            member(self.save_attribute, ATTRIBUTES, "saving attribute")
        elif self.save_attribute is not None:
            raise ValueError("Only saves specify a saving attribute")
        if self.kind == "AUTO" and (self.attribute is not None or self.bonus):
            raise ValueError("Automatic effects do not roll a hidden check")


@dataclass(frozen=True)
class Condition:
    id: str
    name: str
    duration_turns: int
    defense_bonus: int = 0
    attack_bonus: int = 0
    movement_penalty_mm: int = 0
    blocks: tuple[str, ...] = ()
    stacking: str = "REFRESH"

    def __post_init__(self):
        label(self.id)
        label(self.name)
        integer(self.duration_turns, 1, 1000, "condition duration")
        integer(self.defense_bonus, -20, 20, "condition defense bonus")
        integer(self.attack_bonus, -20, 20, "condition attack bonus")
        integer(self.movement_penalty_mm, 0, 1000000, "movement penalty")
        if (type(self.blocks) is not tuple or any(type(value) is not str for value in self.blocks) or
                len(set(self.blocks)) != len(self.blocks)):
            raise ValueError("Invalid condition activation restrictions")
        for value in self.blocks:
            member(value, ("ACTION", "FREE_ACTION", "REACTION", "PASSIVE", "MOVEMENT", "ITEM_INTERACTION"), "condition restriction")
        member(self.stacking, ("REFRESH", "REPLACE", "IGNORE"), "condition stacking")


@dataclass(frozen=True)
class Effect:
    kind: str
    amount: Formula | None = None
    damage_type: str | None = None
    condition: Condition | None = None
    condition_id: str | None = None
    duration_turns: int = 0
    recipient: str = "TARGET"
    on_success: bool = True
    save_half: bool = False

    def __post_init__(self):
        member(self.kind, ("DAMAGE", "HEAL", "RESTORE_MP", "RESTORE_STA", "WARD", "CONDITION", "REMOVE_CONDITION"), "effect")
        member(self.recipient, ("TARGET", "CASTER"), "effect recipient")
        if type(self.on_success) is not bool or type(self.save_half) is not bool:
            raise ValueError("Effect gates must be boolean")
        amounts = self.kind in ("DAMAGE", "HEAL", "RESTORE_MP", "RESTORE_STA", "WARD")
        if (amounts and type(self.amount) is not Formula) or (not amounts and self.amount is not None):
            raise ValueError("Effect amount must match its kind")
        if self.kind == "DAMAGE":
            label(self.damage_type)
        elif self.damage_type is not None or self.save_half:
            raise ValueError("Only damage has a damage type or half-save rule")
        if self.save_half and (not self.on_success or self.recipient != "TARGET"):
            raise ValueError("Half-save damage must target the saving creature")
        if ((self.kind == "CONDITION" and type(self.condition) is not Condition) or
                (self.kind != "CONDITION" and self.condition is not None)):
            raise ValueError("Condition effect requires its exact condition definition")
        if self.kind == "REMOVE_CONDITION":
            label(self.condition_id)
        elif self.condition_id is not None:
            raise ValueError("Only condition removal names a condition ID")
        integer(self.duration_turns, 1 if self.kind == "WARD" else 0,
                1000 if self.kind == "WARD" else 0, "ward duration")


@dataclass(frozen=True)
class Program:
    effects: tuple[Effect, ...]
    resolution: Resolution = Resolution()
    target_kind: str = "ENEMY"
    max_targets: int = 1
    cooldown_turns: int = 0
    uses_per_turn: int = 1
    uses_per_encounter: int | None = None
    minimum_attributes: tuple = ()
    required_conditions: tuple[str, ...] = ()
    forbidden_conditions: tuple[str, ...] = ()
    passive_trigger: str | None = None
    reaction_trigger: str | None = None
    summon: "Manifest | None" = None
    command: "Command | None" = None

    def __post_init__(self):
        from .summons import Manifest, Command
        if self.summon is not None and type(self.summon) is not Manifest:
            raise ValueError("Summoning requires a typed formation definition")
        if self.command is not None and type(self.command) is not Command:
            raise ValueError("Summon command requires typed permissions")
        if self.summon is not None and self.command is not None:
            raise ValueError("One activation cannot manifest and command independently")
        if self.effects or (self.summon is None and self.command is None):
            immutable(self.effects, Effect, "power effects", 20)
        elif type(self.effects) is not tuple:
            raise ValueError("Power effects must be immutable")
        if type(self.resolution) is not Resolution:
            raise ValueError("Power needs a typed resolution")
        member(self.target_kind, ("SELF", "ALLY", "ENEMY", "ANY"), "target relationship")
        integer(self.max_targets, 1, 32, "target count")
        if self.target_kind == "SELF" and self.max_targets != 1:
            raise ValueError("Self powers have one target")
        integer(self.cooldown_turns, 0, 10000, "cooldown")
        integer(self.uses_per_turn, 1, 100, "uses per turn")
        if self.uses_per_encounter is not None:
            integer(self.uses_per_encounter, 1, 10000, "uses per encounter")
        if type(self.minimum_attributes) is not tuple:
            raise ValueError("Attribute requirements must be immutable")
        seen = set()
        for pair in self.minimum_attributes:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("Invalid attribute prerequisite")
            attribute, score = pair
            member(attribute, ATTRIBUTES, "required attribute")
            if attribute in seen:
                raise ValueError("Duplicate attribute prerequisite")
            seen.add(attribute)
            integer(score, 1, 20, "required score")
        for values in (self.required_conditions, self.forbidden_conditions):
            if (type(values) is not tuple or any(type(value) is not str for value in values) or
                    len(set(values)) != len(values)):
                raise ValueError("Invalid condition prerequisites")
            for value in values:
                label(value)
        if set(self.required_conditions) & set(self.forbidden_conditions):
            raise ValueError("Contradictory condition prerequisites")
        if self.passive_trigger is not None:
            member(self.passive_trigger, ("TURN_START", "TURN_END"), "passive trigger")
        if self.reaction_trigger is not None:
            member(self.reaction_trigger, ("INCOMING_DAMAGE",), "reaction trigger")
        if any(effect.save_half for effect in self.effects) and self.resolution.kind != "SAVE":
            raise ValueError("Half damage requires an actual save")
        if (self.summon is not None or self.command is not None) and (self.target_kind != "SELF" or self.resolution.kind != "AUTO"):
            raise ValueError("Summon laws require automatic self activation and explicit spatial orders")


@dataclass(frozen=True)
class Rider:
    effects: tuple[Effect, ...]
    trigger: str = "SUCCESS"

    def __post_init__(self):
        immutable(self.effects, Effect, "integrated rider effects", 10)
        member(self.trigger, ("SUCCESS", "EXECUTION"), "integrated trigger")
        if any(effect.save_half for effect in self.effects):
            raise ValueError("Integrated half-save handling needs a separate explicit rule")


def bind(ability):
    program = ability.program
    if type(program) is not Program:
        raise ValueError("Ability has no supported executable program")
    if (program.summon is not None or program.command is not None) and ability.activation not in ("ACTION", "FREE_ACTION"):
        raise ValueError("Summoning and commands need an explicit Action or Free Action")
    if ability.activation == "PASSIVE":
        if (program.passive_trigger is None or program.reaction_trigger is not None or
                program.target_kind != "SELF" or program.resolution.kind != "AUTO" or
                ability.mp_cost or ability.sta_cost):
            raise ValueError("Passive requires a self trigger and no activation cost")
    elif ability.activation == "REACTION":
        if (program.reaction_trigger is None or program.passive_trigger is not None or
                program.target_kind != "SELF" or program.resolution.kind != "AUTO" or
                any(effect.kind != "WARD" for effect in program.effects)):
            raise ValueError("Supported defensive Reaction requires self ward and incoming damage trigger")
    elif program.passive_trigger is not None or program.reaction_trigger is not None:
        raise ValueError("Active powers cannot invent passive or Reaction activations")
    return program


def integrate(ability, modification):
    bind(ability)
    if type(modification) is not Rider:
        raise ValueError("Integrated Imprint has no supported executable rider")
    if ability.activation == "REACTION" and any(effect.kind != "WARD" for effect in modification.effects):
        raise ValueError("Supported Reaction Imprint must preserve defensive ward semantics")
    return modification


def formula(value):
    return construct(Formula, value)


def condition(value):
    return construct(Condition, value, {"blocks": sequence})


def effect(value):
    return construct(Effect, value, {
        "amount": lambda row: None if row is None else formula(row),
        "condition": lambda row: None if row is None else condition(row)})


def program(value):
    from .summons import manifest, command
    return construct(Program, value, {
        "effects": lambda rows: tuple(effect(row) for row in sequence(rows)),
        "resolution": lambda row: construct(Resolution, row),
        "minimum_attributes": pairs, "required_conditions": sequence, "forbidden_conditions": sequence,
        "summon": lambda row: None if row is None else manifest(row),
        "command": lambda row: None if row is None else command(row)})


def rider(value):
    return construct(Rider, value, {"effects": lambda rows: tuple(effect(row) for row in sequence(rows))})
