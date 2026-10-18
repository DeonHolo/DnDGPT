from dataclasses import asdict, replace
import json

import pytest

from app.creation import (confirm_character, owned_abilities, prepare_starting_build,
                          public_preview, starting_preview)
from app.creation_codec import decode as decode_draft, encode
from app.gear import Bonuses, Funds, Item, Loadout, Meter, Supply, calculate, decode
from app.powers import Program
from app.rules import EQUIPMENT_SLOTS
from .build_fixtures import loadout
from .test_creation import at_confirmation


def json_data(value):
    return json.loads(json.dumps(asdict(value)))


def test_complete_build_calculates_resources_equipment_dc_and_parent_only_imprint():
    draft = at_confirmation()
    before = encode(draft)
    prepared = prepare_starting_build(draft, loadout())
    result = starting_preview(prepared)
    assert encode(draft) == before and draft.loadout is None
    assert prepared.version == draft.version + 1 and prepared.phase == "character_confirmation"
    assert result["resources"] == {"hp": 105, "mp": 65, "sta": 68}
    assert result["derived"]["def"] == 12  # DEX 7 plus the declared coat bonus.
    assert len(result["equipment"]) == 16
    assert result["equipment"]["Main Hand"] == result["equipment"]["Off-Hand"] == "staff"
    assert result["carried_weight_grams"] == 7500  # Both hands refer to one staff.
    assert result["derived"]["carry_capacity_grams"] == 26000
    assert result["inventory_mode"] == "GEAR_FIRST" and len(result["supplies"]) == 2
    assert len(result["abilities"]) == len(owned_abilities(draft)) == 3
    assert sum("imprint" in power for power in result["abilities"]) == 1
    assert all(power["calculated_dc"] == 13 for power in result["abilities"] if power["source_kind"] == "SIGNATURE")
    assert result["sources"]["titles"] == []
    assert result["sources"]["classes"][0]["rarity"] == "COMMON"
    assert result["executable_programs_validated"] and not result["semantic_tier_certification"]
    assert public_preview(prepared)["starting_build"] == result
    assert "natural" not in json.dumps(public_preview(prepared))
    assert decode_draft(json.loads(json.dumps(encode(prepared)))) == prepared


def test_confirmation_requires_build_and_freezes_that_exact_preview():
    draft = at_confirmation()
    with pytest.raises(ValueError, match="Complete the starting build"):
        confirm_character(draft, confirmed=True)
    prepared = prepare_starting_build(draft, loadout())
    snapshot = starting_preview(prepared)
    confirmed = confirm_character(prepared, confirmed=True)
    assert starting_preview(confirmed) == snapshot
    with pytest.raises(ValueError, match="Requires character_confirmation"):
        prepare_starting_build(confirmed, loadout())
    snapshot["items"][0]["name"] = "Tampered inspection"
    assert starting_preview(confirmed)["items"][0]["name"] != "Tampered inspection"


@pytest.mark.parametrize("changes", [{"program": None}, {"program": replace(owned_abilities(at_confirmation())[0].program,
                                                                         minimum_attributes=(("INT", 20),))}])
def test_legacy_or_unusable_selected_power_cannot_be_silently_repaired_in_build(changes):
    draft = at_confirmation()
    classes = draft.boards[0]
    offer = classes.offers[0]
    broken = replace(offer.abilities[0], **changes)
    modified = replace(draft, boards=(replace(classes, offers=(replace(offer, abilities=(broken,)), *classes.offers[1:])),
                                     *draft.boards[1:]))
    with pytest.raises(ValueError):
        prepare_starting_build(modified, loadout())
    assert modified.loadout is None


def test_non_executable_imprint_cannot_become_a_fake_ready_build():
    draft = at_confirmation()
    background = draft.boards[-1]
    selected = background.offers[0]
    modified = replace(draft, boards=(*draft.boards[:-1], replace(background, offers=(
        replace(selected, imprint=replace(selected.imprint, rider=None)), *background.offers[1:]))))
    with pytest.raises(ValueError, match="executable rider"):
        prepare_starting_build(modified, loadout())


@pytest.mark.parametrize("field,value", [("weight_grams", True), ("quantity", 0), ("rarity", "MYTHIC"),
                                         ("charges", {"current": 1, "maximum": 1})])
def test_item_contract_rejects_ambiguous_or_untyped_data(field, value):
    with pytest.raises(ValueError):
        replace(loadout().items[0], **{field: value})


def test_loadout_json_is_strict_and_unimplemented_item_powers_are_not_accepted_as_prose():
    encoded = json_data(loadout())
    assert decode(encoded) == loadout()
    encoded["items"][0]["abilities"] = [{"description": "Unlimited arbitrary power"}]
    with pytest.raises(ValueError, match="fields"):
        decode(encoded)


def test_two_handed_item_cannot_occupy_only_one_hand_or_duplicate_itself():
    original = loadout()
    layout = dict(original.equipment)
    layout["Off-Hand"] = None
    with pytest.raises(ValueError, match="exactly one declared mode"):
        replace(original, equipment=tuple(layout.items()))
    with pytest.raises(ValueError, match="Duplicate owned"):
        replace(original, items=(*original.items, original.items[1]))


@pytest.mark.parametrize("edit", ["missing_slot", "unknown_slot", "unknown_item", "duplicate_slot", "wrong_location"])
def test_equipment_slots_and_physical_ownership_must_agree(edit):
    original = loadout()
    equipment, items = list(original.equipment), original.items
    if edit == "missing_slot":
        equipment.pop()
    elif edit == "unknown_slot":
        equipment.append(("Third Hand", None))
    elif edit == "unknown_item":
        equipment[0] = (equipment[0][0], "unowned-item")
    elif edit == "duplicate_slot":
        equipment.append(equipment[0])
    else:
        items = (replace(items[0], location="CARRIED"), *items[1:])
    with pytest.raises(ValueError):
        replace(original, equipment=tuple(equipment), items=items)


def test_rarity_and_unequipped_gear_do_not_create_unwritten_bonuses():
    original = loadout()
    attributes = dict(at_confirmation().attributes)
    ordinary = calculate(original, attributes)
    legendary = replace(original, items=tuple(replace(item, rarity="LEGENDARY") for item in original.items))
    assert calculate(legendary, attributes)["derived"] == ordinary["derived"]
    layout = dict(original.equipment)
    layout["Chest"] = None
    carried = replace(original, equipment=tuple(layout.items()), items=(replace(original.items[0], location="CARRIED",
        bonuses=Bonuses(defense=50, hp_max=500)), *original.items[1:]))
    stats = calculate(carried, attributes)["derived"]
    assert stats["def"] == 11 and stats["hp_max"] == 105


def test_only_explicit_equipped_bonuses_change_derived_maxima_and_capacity():
    original = loadout()
    bonus = Bonuses(hp_max=5, mp_max=3, sta_max=2, defense=1, movement_mm=500, carry_grams=500)
    revised = replace(original, items=(replace(original.items[0], bonuses=bonus), *original.items[1:]))
    result = calculate(revised, dict(at_confirmation().attributes))
    assert result["resources"] == {"hp": 110, "mp": 68, "sta": 70}
    assert result["derived"]["movement_mm"] == 6500
    assert result["derived"]["carry_capacity_grams"] == 26500


def test_capacity_bulk_and_gear_prerequisites_are_real_limits():
    original = loadout()
    with pytest.raises(ValueError, match="capacity"):
        calculate(replace(original, supplies=(Supply("cargo", "Large cargo", 1, "bundle", 100000,
                                                      "Disposable carry test"),)), dict(at_confirmation().attributes))
    with pytest.raises(ValueError, match="prerequisite"):
        calculate(replace(original, items=(replace(original.items[0], minimum_attributes=(("STR", 20),)),
                                           *original.items[1:])), dict(at_confirmation().attributes))
    with pytest.raises(ValueError, match="Incompatible"):
        replace(original, items=(replace(original.items[0], incompatible_items=("staff",)), *original.items[1:]))


def test_quantity_weight_is_not_confused_with_grouped_supply_bulk():
    item = Item("salvage", "Salvage", "COMMON", 150, "CARRIED", "Disposable inventory test", quantity=3)
    empty_slots = tuple((slot, None) for slot in EQUIPMENT_SLOTS)
    result = calculate(Loadout((item,), empty_slots, supplies=(Supply("rations", "Rations", 5, "portions", 700,
                                                                     "Disposable supplies"),)), dict(at_confirmation().attributes))
    assert result["carried_weight_grams"] == 3 * 150 + 700


def test_empty_pools_and_borrowed_obligations_remain_explicit():
    item = Item("borrowed", "Borrowed tool", "RARE", 100, "CARRIED", "Disposable loan",
                ownership="BORROWED", return_obligation="Return to the fixture lender",
                charges=Meter(0, 3), battery=Meter(0, 0), ammunition=Meter(0, 5))
    assert decode(json_data(Loadout((item,), tuple((slot, None) for slot in EQUIPMENT_SLOTS)))).items[0] == item
    with pytest.raises(ValueError):
        replace(item, return_obligation=None)
    with pytest.raises(ValueError):
        Meter(4, 3)
    with pytest.raises(ValueError):
        Meter(True, 3)
    with pytest.raises(ValueError):
        Funds("fixture units", -1, "Invalid fixture")
