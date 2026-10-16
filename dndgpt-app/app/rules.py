"""Deterministic rules and auditable randomness. No transport or model dependency."""
from __future__ import annotations

import secrets
from dataclasses import dataclass, replace
from typing import Callable

RARITIES = ("COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY", "UNIQUE")
BANDS = (5500, 8000, 9200, 9800, 9970, 10000)
ATTRIBUTES = ("STR", "AGI", "INT", "CHA", "LCK")
EQUIPMENT_SLOTS = ("Head", "Face", "Neck", "Shoulders", "Chest", "Arms", "Hands",
                   "Main Hand", "Off-Hand", "Waist", "Legs", "Feet", "Back",
                   "Ring 1", "Ring 2", "Artifact")


def integer(value, minimum, maximum, name):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")
    return value


def modifier(score: int) -> int:
    return (integer(score, 1, 20, "attribute") - 5) // 2


def derived(attributes: dict) -> dict:
    for key in ATTRIBUTES:
        modifier(attributes[key])
    return {"hp_max": 70 + 5 * attributes["STR"],
            "mp_max": 30 + 5 * attributes["INT"],
            "sta_max": 40 + 4 * attributes["AGI"],
            "carry_capacity_kg": 12 + 2 * attributes["STR"],
            "def": 10 + modifier(attributes["AGI"]), "movement_mm": 6000}


class Dice:
    def __init__(self, randbelow: Callable[[int], int] | None = None):
        self.randbelow = randbelow or secrets.randbelow
        self.source = "test fixture" if randbelow else "secrets.randbelow (OS CSPRNG)"

    def roll(self, sides: int) -> int:
        integer(sides, 2, 10000, "sides")
        value = self.randbelow(sides)
        integer(value, 0, sides - 1, "RNG output")
        return value + 1

    def check(self, dc: int, bonus: int, advantage: bool = False,
              disadvantage: bool = False) -> dict:
        integer(dc, 1, 40, "dc")
        integer(bonus, -20, 40, "modifier")
        rolls = [self.roll(20)]
        if advantage != disadvantage:
            rolls.append(self.roll(20))
        natural = (max(rolls) if advantage else min(rolls))
        return {"rolls": rolls, "natural": natural, "modifier": bonus, "dc": dc,
                "total": natural + bonus, "success": natural == 20 or
                (natural != 1 and natural + bonus >= dc), "rng": self.source}

    def rarity(self, luck: int) -> dict:
        luck_modifier = max(0, modifier(luck))
        threshold = min(3500, 500 * luck_modifier)
        natural = self.roll(10000)
        tier = next(i for i, ceiling in enumerate(BANDS) if natural <= ceiling)
        luck_roll = self.roll(10000) if threshold else None
        enhanced = luck_roll is not None and luck_roll <= threshold
        return {"natural": natural, "base_rarity": RARITIES[tier], "luck": luck,
                "luck_modifier": luck_modifier, "luck_threshold": threshold,
                "luck_roll": luck_roll, "enhanced": enhanced,
                "final_rarity": RARITIES[min(5, tier + int(enhanced))], "rng": self.source}


def xp_threshold(level: int) -> int:
    return 100 + 40 * (integer(level, 1, 1000, "level") - 1)


def award_xp(state: dict, amount: int) -> list[int]:
    """Carry excess XP, award each earned level once, and freeze immediately."""
    integer(amount, 0, 100000, "XP")
    ch = state["character"]
    ch["xp"] += amount
    ch["xp_total"] += amount
    levels = []
    while ch["xp"] >= xp_threshold(ch["level"]):
        ch["xp"] -= xp_threshold(ch["level"])
        ch["level"] += 1
        levels.append(ch["level"])
        for track in ("attribute_points", "skill_points", "talent_points"):
            ch[track] += 1
        ch["hp"] = ch["hp_max"]
        ch["mp"] = ch["mp_max"]
        ch["scene_counter"] = 0
        state["paused"] = state["level_up_freeze"] = True
        state["advancement"]["pending_levels"].append(ch["level"])
    ch["xp_next"] = xp_threshold(ch["level"])
    return levels


@dataclass(frozen=True)
class TurnBudget:
    action: int = 1
    free_action: int = 1
    reaction: int = 1
    movement_mm: int = 6000
    item_interaction: int = 1

    def spend(self, resource: str, amount: int = 1) -> "TurnBudget":
        if resource not in self.__dataclass_fields__:
            raise ValueError("Unknown turn resource")
        integer(amount, 1, 1000000000, "amount")
        available = getattr(self, resource)
        if amount > available:
            raise ValueError(f"Insufficient {resource}")
        return replace(self, **{resource: available - amount})
