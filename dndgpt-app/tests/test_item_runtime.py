from copy import deepcopy
from dataclasses import replace

import pytest

from app import combat, gear
from app.gear import Bonuses, Item, ItemPower, Loadout, Meter, Supply
from app.powers import Effect, Formula, Program
from app.rules import EQUIPMENT_SLOTS
from .test_powers import Rolls, actor, character, power, start


def item_power(item_id="wand", *, id="item-bolt", activation="ACTION", program=None, **costs):
    ability = replace(power(id, activation=activation, program=program, cost=0, sta=0),
                      source_kind="ITEM", source_id=item_id)
    return ItemPower(ability, **costs)


def loadout(*items, supplies=()):
    slots = dict.fromkeys(EQUIPMENT_SLOTS)
    for item in items:
        if item.location == "EQUIPPED":
            slots.update(dict.fromkeys(item.equip_modes[0], item.id))
    return Loadout(tuple(items), tuple(slots.items()), tuple(supplies))


def wand(**changes):
    values = dict(id="wand", name="Fixture charged focus", rarity="COMMON", weight_grams=500,
                  location="EQUIPPED", provenance="Disposable item test", equip_modes=(("Main Hand",),),
                  powers=(item_power(charges_cost=1, battery_cost=2, ammunition_cost=1),),
                  charges=Meter(2, 3), battery=Meter(5, 5), ammunition=Meter(4, 10))
    values.update(changes)
    return Item(**values)


def potion(id="potion", *, access="ACCESSIBLE", quantity=2):
    return Item(id, "Fixture restorative", "COMMON", 100, "CARRIED", "Disposable consumable test", quantity=quantity,
                access=access, powers=(item_power(id, id="drink-" + id, quantity_cost=1, requires_equipped=False,
                    program=Program((Effect("HEAL", Formula(1, 6)),), target_kind="SELF")),))


def prepared(loadout):
    ch = character()
    gear.recalculate(ch, loadout)
    player = actor("player")
    for key in ("hp", "mp", "sta", "hp_max", "mp_max", "sta_max", "def", "movement_mm"):
        player[key] = ch[key]
    player["loadout"] = gear.encode(loadout)
    return combat.prepare(ch, [player, actor("enemy")], ["player", "enemy"], [])


def use(encounter, rolls, *, item_id="wand", ability_id="item-bolt", targets=None, kind="use_item", **kwargs):
    payload = {"actor_id": "player", "ability_id": ability_id, "target_ids": targets or ["enemy"]}
    if kind == "use_item":
        payload["item_id"] = item_id
    return combat.apply(encounter, kind, payload, rolls.dice, **kwargs)


def test_item_contract_roundtrip_and_provenance_are_shared_with_source_powers():
    original = loadout(wand())
    assert gear.decode(gear.encode(original)) == original
    with pytest.raises(ValueError, match="actual item"):
        wand(powers=(item_power("unowned", charges_cost=1),))
    with pytest.raises(ValueError, match="ITEM provenance"):
        ItemPower(power())
    with pytest.raises(ValueError, match="capacity"):
        wand(powers=(item_power(charges_cost=4),))


def test_executed_miss_spends_all_actual_pools_and_preview_never_rolls():
    encounter = start(prepared(loadout(wand())))
    rolls = Rolls(1)
    projected, preview = use(encounter, rolls, preview=True)
    assert rolls.sides == [] and preview["preview"]
    result, receipt = use(encounter, rolls)
    remaining = gear.decode(result["actors"]["player"]["loadout"]).items[0]
    assert remaining.charges.current == 1 and remaining.battery.current == 3 and remaining.ammunition.current == 3
    assert rolls.sides == [20] and result["actors"]["enemy"]["hp"] == 95
    assert result["actors"]["player"]["budget"]["action"] == 0
    assert receipt["ledger"][0]["item_expenditure"]["charges_cost"] == 1
    assert gear.decode(projected["actors"]["player"]["loadout"]) == gear.decode(result["actors"]["player"]["loadout"])


@pytest.mark.parametrize("changes", [{"charges": Meter(0, 3)}, {"battery": Meter(1, 5)}, {"ammunition": Meter(0, 10)},
                                      {"location": "CARRIED"}])
def test_unavailable_item_is_rejected_before_rng_or_expenditure(changes):
    encounter = start(prepared(loadout(wand(**changes))))
    before, rolls = deepcopy(encounter), Rolls()
    with pytest.raises(ValueError):
        use(encounter, rolls)
    assert encounter == before and rolls.sides == []


def test_generic_ability_command_cannot_bypass_item_costs_or_source_identity():
    encounter = start(prepared(loadout(wand())))
    result, _ = use(encounter, Rolls(1), kind="use_ability")
    assert gear.decode(result["actors"]["player"]["loadout"]).items[0].charges.current == 1
    with pytest.raises(ValueError, match="does not belong"):
        use(encounter, Rolls(), item_id="different-object")
    fake = actor("player", abilities=(replace(power(), source_kind="ITEM", source_id="fake"),))
    with pytest.raises(ValueError, match="actual owned loadout"):
        combat.prepare(character(), [fake, actor("enemy")], ["player", "enemy"], [])


def test_illegal_target_does_not_consume_stock_or_pool_costs():
    encounter = start(prepared(loadout(wand())))
    rolls = Rolls()
    with pytest.raises(ValueError, match="Unknown combat actor"):
        use(encounter, rolls, targets=["missing"])
    assert rolls.sides == []
    assert gear.decode(encounter["actors"]["player"]["loadout"]).items[0].charges.current == 2


def test_consumable_uses_action_draw_interaction_stock_and_actual_healing():
    ring = Item("ring", "Fixture vitality ring", "COMMON", 10, "EQUIPPED", "Disposable bonus test",
                equip_modes=(("Ring 1",),), bonuses=Bonuses(hp_max=10))
    encounter = start(prepared(loadout(ring, potion())))
    result, receipt = use(encounter, Rolls(4), item_id="potion", ability_id="drink-potion", targets=["player"])
    player = result["actors"]["player"]
    assert player["hp"] == 99 and player["hp_max"] == 105
    assert player["budget"]["action"] == player["budget"]["item_interaction"] == 0
    assert gear.find(gear.decode(player["loadout"]), "potion").quantity == 1
    assert receipt["ledger"][0]["item_expenditure"]["quantity_cost"] == 1


def test_packed_consumable_requires_real_retrieval_action_then_later_activation():
    encounter = start(prepared(loadout(potion(access="PACKED"))))
    with pytest.raises(ValueError, match="Retrieve"):
        use(encounter, Rolls(), item_id="potion", ability_id="drink-potion", targets=["player"])
    encounter, receipt = combat.apply(encounter, "retrieve_item", {"actor_id": "player", "item_id": "potion"}, Rolls().dice)
    assert receipt["ledger"][0]["combat_cost"] == "action"
    assert encounter["actors"]["player"]["budget"]["action"] == 0
    with pytest.raises(ValueError, match="budget"):
        use(encounter, Rolls(), item_id="potion", ability_id="drink-potion", targets=["player"])
    for id in ("player", "enemy"):
        encounter = combat.apply(encounter, "end_turn", {"actor_id": id}, Rolls().dice)[0]
    result, _ = use(encounter, Rolls(3), item_id="potion", ability_id="drink-potion", targets=["player"])
    assert gear.find(gear.decode(result["actors"]["player"]["loadout"]), "potion").quantity == 1


def test_full_hands_cannot_silently_draw_a_consumable():
    staff = Item("staff", "Fixture staff", "COMMON", 1000, "EQUIPPED", "Disposable hands test",
                 equip_modes=(("Main Hand", "Off-Hand"),))
    encounter = start(prepared(loadout(staff, potion())))
    with pytest.raises(ValueError, match="free hand"):
        use(encounter, Rolls(), item_id="potion", ability_id="drink-potion", targets=["player"])


def test_weapon_rearrangement_spends_action_and_stows_entire_two_hand_object():
    staff = Item("staff", "Fixture staff", "COMMON", 1000, "EQUIPPED", "Disposable swap test",
                 equip_modes=(("Main Hand", "Off-Hand"),))
    focus = wand(location="CARRIED")
    encounter = start(prepared(loadout(staff, focus)))
    result, receipt = combat.apply(encounter, "equip_item", {"actor_id": "player", "item_id": "wand", "slots": ["Main Hand"]}, Rolls().dice)
    equipped = gear.decode(result["actors"]["player"]["loadout"])
    assert receipt["ledger"][0]["displaced"] == ["staff"]
    assert dict(equipped.equipment)["Off-Hand"] is None and gear.find(equipped, "staff").location == "CARRIED"
    assert result["actors"]["player"]["budget"]["action"] == 0
    assert result["actors"]["player"]["budget"]["item_interaction"] == 1


def test_body_equipment_cannot_change_instantly_during_combat():
    coat = Item("coat", "Fixture coat", "COMMON", 1000, "EQUIPPED", "Disposable preparation test",
                equip_modes=(("Chest",),), equip_seconds=60)
    encounter = start(prepared(loadout(coat)))
    with pytest.raises(ValueError, match="outside combat"):
        combat.apply(encounter, "unequip_item", {"actor_id": "player", "item_id": "coat"}, Rolls().dice)


def test_grouped_medicine_consumes_real_quantity_and_aggregate_bulk_once():
    medicine = Supply("medicine", "Basic medicine", 5, "uses", 700, "Disposable supply test", powers=(
        item_power("medicine", id="first-aid", quantity_cost=1, requires_equipped=False,
                   program=Program((Effect("HEAL", Formula(flat=2)),), target_kind="SELF")),))
    encounter = start(prepared(loadout(supplies=(medicine,))))
    result, _ = use(encounter, Rolls(), item_id="medicine", ability_id="first-aid", targets=["player"])
    remaining = gear.decode(result["actors"]["player"]["loadout"]).supplies[0]
    assert remaining.quantity == 4 and remaining.bulk_grams == 560
    with pytest.raises(ValueError, match="stock expenditure"):
        replace(medicine, powers=(replace(medicine.powers[0], quantity_cost=0),))


def test_consuming_and_re_equipping_speed_gear_cannot_reset_movement():
    burst = Item("burst", "Fixture consumed focus", "COMMON", 20, "EQUIPPED", "Disposable movement test",
        equip_modes=(("Main Hand",),), bonuses=Bonuses(movement_mm=3000), powers=(
            item_power("burst", id="consume-burst", activation="FREE_ACTION", quantity_cost=1,
                       program=Program((Effect("RESTORE_MP", Formula(flat=0)),), target_kind="SELF")),))
    spare = Item("spare", "Fixture spare focus", "COMMON", 20, "CARRIED", "Disposable movement test",
        equip_modes=(("Main Hand",),), bonuses=Bonuses(movement_mm=3000))
    encounter = start(prepared(loadout(burst, spare)))
    encounter = combat.apply(encounter, "combat_move", {"actor_id": "player", "path": [[0, 9000, 0]]}, Rolls().dice)[0]
    encounter = use(encounter, Rolls(), item_id="burst", ability_id="consume-burst", targets=["player"])[0]
    encounter = combat.apply(encounter, "equip_item", {"actor_id": "player", "item_id": "spare", "slots": ["Main Hand"]}, Rolls().dice)[0]
    assert encounter["actors"]["player"]["movement_mm"] == 9000
    assert encounter["actors"]["player"]["budget"]["movement_mm"] == 0
    assert encounter["actors"]["player"]["movement_spent_mm"] == 9000


def test_item_passive_requires_actual_equipment_and_does_not_refill_after_stow():
    power_def = item_power("focus", id="focus-regen", activation="PASSIVE", program=Program(
        (Effect("RESTORE_MP", Formula(flat=2)),), target_kind="SELF", passive_trigger="TURN_START"))
    focus = Item("focus", "Fixture focus", "COMMON", 50, "EQUIPPED", "Disposable passive test",
        equip_modes=(("Main Hand",),), bonuses=Bonuses(mp_max=10), powers=(power_def,))
    encounter = start(prepared(loadout(focus)))
    assert encounter["actors"]["player"]["mp"] == 57
    encounter = combat.apply(encounter, "unequip_item", {"actor_id": "player", "item_id": "focus"}, Rolls().dice)[0]
    for id in ("player", "enemy"):
        encounter = combat.apply(encounter, "end_turn", {"actor_id": id}, Rolls().dice)[0]
    assert encounter["actors"]["player"]["mp"] == 55  # Lower maximum clamps; the carried passive did not run.


def test_consumed_loan_item_keeps_its_return_obligation_in_the_receipt():
    borrowed = replace(potion(quantity=1), ownership="BORROWED", return_obligation="Return or replace the loan")
    result, receipt = use(start(prepared(loadout(borrowed))), Rolls(2), item_id="potion",
                          ability_id="drink-potion", targets=["player"])
    assert result["actors"]["player"]["loadout"]["items"] == []
    expenditure = receipt["ledger"][0]["item_expenditure"]
    assert expenditure["ownership"] == "BORROWED" and expenditure["return_obligation"] == "Return or replace the loan"


def test_valid_aggregate_gear_statistics_remain_executable_in_combat():
    equipped = loadout(*(Item(str(index), "Fixture boundary item", "COMMON", 0, "EQUIPPED",
        "Disposable numeric-boundary test; no rarity certification", equip_modes=((slot,),),
        bonuses=Bonuses(hp_max=100000, mp_max=100000, sta_max=100000, defense=100, movement_mm=100000))
        for index, slot in enumerate(EQUIPMENT_SLOTS)))
    stats = gear.calculate(equipped, character()["attributes"])["derived"]
    assert stats["hp_max"] == 1600095 and stats["def"] == 1610 and stats["movement_mm"] == 1606000
    encounter = start(prepared(equipped))
    result, _ = combat.apply(encounter, "combat_move", {"actor_id": "player", "path": [[0, stats["movement_mm"], 0]]}, Rolls().dice)
    player = result["actors"]["player"]
    assert player["budget"]["movement_mm"] == 0 and player["movement_spent_mm"] == stats["movement_mm"]
    with pytest.raises(ValueError, match="Insufficient movement_mm"):
        combat.apply(result, "combat_move", {"actor_id": "player", "path": [[0, stats["movement_mm"] + 1, 0]]}, Rolls().dice)
