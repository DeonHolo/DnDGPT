"""One recorded outfit: class-grade quality, story-weighted slots, no rerolls."""
from .rules import EQUIPMENT_SLOTS

TIERS = ("COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY", "UNIQUE")
COSTS = dict(zip(TIERS, (1, 3, 8, 20, 50, 120)))
BUDGETS = dict(zip(TIERS, (12, 24, 48, 96, 192, 320)))
SUPPORT = dict(zip(TIERS, ("COMMON", "UNCOMMON", "UNCOMMON", "RARE", "EPIC", "EPIC")))
ESSENTIALS = 6
ITEM_COUNT = 4


def slot_pool(preferences):
    """Unspecified slots stay eligible at weight 1; freeze justified overrides before RNG."""
    if type(preferences) is not list or not 1 <= len(preferences) <= len(EQUIPMENT_SLOTS):
        raise ValueError("slot_preferences needs 1..16 justified slot weights")
    slots = {slot: {"slot": slot, "weight": 1, "basis": "Plausible class-appropriate equipment"}
             for slot in EQUIPMENT_SLOTS}
    seen = set()
    for row in preferences:
        if type(row) is not dict or set(row) != {"slot", "weight", "basis"}:
            raise ValueError("Each slot preference needs slot, weight and basis")
        slot, weight, basis = row["slot"], row["weight"], row["basis"]
        if type(slot) is not str or slot not in slots or slot in seen:
            raise ValueError("Use distinct legal equipment slots")
        if type(weight) is not int or not 0 <= weight <= 3:
            raise ValueError("Slot weights are integers 0..3")
        if type(basis) is not str or not 1 <= len(basis.strip()) <= 240:
            raise ValueError("Explain each slot weight using actual class/story facts")
        slots[slot] = {"slot": slot, "weight": weight, "basis": basis.strip()}
        seen.add(slot)
    pool = [row for row in slots.values() if row["weight"]]
    if len(pool) < ITEM_COUNT or not any(row["weight"] > 1 for row in pool):
        raise ValueError("Keep at least four eligible slots and one class/story preference")
    return pool


def take_slot(pool, dice):
    total = sum(row["weight"] for row in pool)
    ticket = dice.roll(total) if total > 1 else 1
    cumulative = 0
    for index, row in enumerate(pool):
        cumulative += row["weight"]
        if ticket <= cumulative:
            return {**pool.pop(index), "slot_roll": ticket, "slot_total_weight": total}
    raise ValueError("Slot roll outside its committed pool")


def starting_outfit(rarity, dice, slot_preferences):
    """Reserve affordable floors BEFORE each draw; record every draw without rerolls."""
    budget = BUDGETS[rarity]
    floor = SUPPORT[rarity]
    premium = "LEGENDARY" if rarity == "UNIQUE" else rarity
    candidates = slot_pool(slot_preferences)
    available = candidates.copy()
    remaining = budget - ESSENTIALS
    items = []
    for index in range(ITEM_COUNT):
        base = premium if index == 0 else floor
        higher = TIERS[min(TIERS.index(base) + 1, len(TIERS) - 1)]
        reserve = COSTS[floor] * (ITEM_COUNT - index - 1)
        chance = 75 if index == 0 and rarity == "UNIQUE" else 20
        if higher == base or COSTS[higher] > remaining - reserve:
            chance = 0
        draw = dice.roll(100)
        tier = higher if draw <= chance else base
        chosen = take_slot(available, dice)
        remaining -= COSTS[tier]
        items.append({**chosen, "role": "Premium item" if index == 0 else "Supporting item",
                      "rarity": tier, "cost": COSTS[tier],
                      "roll": draw, "promotion_chance": chance})
    return {"algorithm": "weighted-slots-v2", "class_rarity": rarity,
            "slot_candidates": candidates, "budget": budget, "essentials_budget": ESSENTIALS,
            "equipment_budget_spent": sum(item["cost"] for item in items),
            "unspent": remaining, "items": items,
            "essentials": "Suitable weatherwear, storage, tools and finite ordinary supplies",
            "instruction": "Create four distinct, useful items in the drawn slots, with full effects at "
                           "each recorded rarity. Any eligible slot can hold the premium item. Weave the "
                           "actual equipment into Your story, preserving player-authored history; awakening "
                           "may explain a newly formed item. Add functional essentials, including an ordinary "
                           "weapon/focus if needed, within their reserve. Points are an outfitting "
                           "allowance, not money or sale prices. Save this receipt and item provenance once; "
                           "never reroll it or substitute cosmetics for functional equipment."}
