from app.gear import Bonuses, Funds, Item, Loadout, Supply
from app.rules import EQUIPMENT_SLOTS


def loadout():
    equipment = dict.fromkeys(EQUIPMENT_SLOTS)
    equipment.update({"Chest": "coat", "Main Hand": "staff", "Off-Hand": "staff", "Feet": "boots", "Back": "pack"})
    return Loadout(items=(
        Item("coat", "Fixture armored coat", "COMMON", 2000, "EQUIPPED", "Disposable starting kit",
             equip_modes=(("Chest",),), bonuses=Bonuses(defense=1)),
        Item("staff", "Fixture two-handed staff", "COMMON", 1600, "EQUIPPED", "Disposable starting kit",
             equip_modes=(("Main Hand", "Off-Hand"),)),
        Item("boots", "Fixture boots", "COMMON", 800, "EQUIPPED", "Disposable starting kit", equip_modes=(("Feet",),)),
        Item("pack", "Fixture pack", "COMMON", 500, "EQUIPPED", "Disposable starting kit", equip_modes=(("Back",),))),
        equipment=tuple(equipment.items()),
        supplies=(Supply("water", "Water", 2, "litres", 2000, "Disposable starting provision"),
                  Supply("food", "Provisions", 2, "portions", 600, "Disposable starting provision")),
        funds=(Funds("fixture units", 10, "Disposable starting provision"),))
