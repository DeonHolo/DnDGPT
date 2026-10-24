"""One recorded starting-equipment draw; points buy gear, never campaign money."""

TIERS = ("COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY", "UNIQUE")
COSTS = dict(zip(TIERS, (1, 3, 8, 20, 50, 120)))
BUDGETS = dict(zip(TIERS, (12, 24, 48, 96, 192, 320)))
SUPPORT = dict(zip(TIERS, ("COMMON", "UNCOMMON", "UNCOMMON", "RARE", "EPIC", "EPIC")))
ROLES = ("Class focus or weapon", "Protection", "Movement or fieldcraft", "Accessory or command implement")
ESSENTIALS = 6


def starting_outfit(rarity, dice):
    """Reserve affordable floors BEFORE each draw; record every draw without rerolls."""
    budget = BUDGETS[rarity]
    floor = SUPPORT[rarity]
    anchor = "LEGENDARY" if rarity == "UNIQUE" else rarity
    remaining = budget - ESSENTIALS
    items = []
    for index, role in enumerate(ROLES):
        base = anchor if index == 0 else floor
        higher = TIERS[min(TIERS.index(base) + 1, len(TIERS) - 1)]
        reserve = COSTS[floor] * (len(ROLES) - index - 1)
        chance = 75 if index == 0 and rarity == "UNIQUE" else 20
        if higher == base or COSTS[higher] > remaining - reserve:
            chance = 0
        draw = dice.roll(100)
        tier = higher if draw <= chance else base
        remaining -= COSTS[tier]
        items.append({"role": role, "rarity": tier, "cost": COSTS[tier],
                      "roll": draw, "promotion_chance": chance})
    return {"class_rarity": rarity, "budget": budget, "essentials_budget": ESSENTIALS,
            "equipment_budget_spent": sum(item["cost"] for item in items),
            "unspent": remaining, "items": items,
            "essentials": "Suitable weatherwear, storage, tools and finite ordinary supplies",
            "instruction": "Create four distinct, immediately useful equipped items for the actual build, "
                           "with full effects at each recorded rarity. Fit roles to the class; a weapon is "
                           "optional. Add suitable essentials within their reserve. Points are an outfitting "
                           "allowance, not money or sale prices. Save this receipt and item provenance once; "
                           "never reroll it or substitute cosmetics for functional equipment."}
