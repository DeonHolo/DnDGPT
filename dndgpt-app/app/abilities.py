"""One immutable ability contract for source powers and owned item powers."""
from dataclasses import asdict, dataclass

from .contracts import construct, items, sequence, text
from .powers import Program, bind, program
from .rules import RARITIES, integer, modifier


@dataclass(frozen=True)
class Ability:
    id: str
    name: str
    source_kind: str
    source_id: str
    rarity: str
    activation: str
    manifestation: tuple[str, str, str, str, str]
    mp_cost: int
    sta_cost: int
    range_mm: int
    targets: str
    resolution: str
    trigger: str
    duration: str
    cooldown: str
    prerequisites: str
    stacking: str
    limits: str
    program: Program | None = None

    def __post_init__(self):
        for name in ("id", "name", "source_id", "targets", "resolution", "trigger",
                     "duration", "cooldown", "prerequisites", "stacking", "limits"):
            text(getattr(self, name), name)
        if self.source_kind not in {"CLASS", "SIGNATURE", "TITLE", "ITEM", "SUMMON"}:
            raise ValueError("Invalid ability source")
        if self.rarity not in RARITIES:
            raise ValueError("Invalid rarity")
        if self.activation not in {"ACTION", "FREE_ACTION", "REACTION", "PASSIVE"}:
            raise ValueError("Invalid activation")
        for part in items(self.manifestation, "manifestation", 5):
            text(part, "physical manifestation")
        integer(self.mp_cost, 0, 100000, "MP cost")
        integer(self.sta_cost, 0, 100000, "STA cost")
        integer(self.range_mm, 0, 10000000, "range")
        if self.program is not None:
            bind(self)


def decode(value):
    return construct(Ability, value, {"manifestation": sequence,
        "program": lambda row: None if row is None else program(row)})


def preview(ability, attributes):
    definition = bind(ability).resolution
    bonus = modifier(attributes[definition.attribute]) if definition.attribute else 0
    return {**asdict(ability),
            "calculated_dc": definition.dc_base + bonus + definition.bonus if definition.kind == "SAVE" else None,
            "calculated_attack_bonus": bonus + definition.bonus if definition.kind == "ATTACK" else None}
