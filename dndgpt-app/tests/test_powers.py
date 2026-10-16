from copy import deepcopy
from dataclasses import asdict, replace
import json

import pytest

from app import combat
from app.creation import Ability, Imprint
from app.creation_codec import ability as decode_ability, imprint as decode_imprint
from app.powers import Condition, Effect, Formula, Program, Resolution, Rider, program as decode_program
from app.rules import ATTRIBUTES, Dice, derived


def data(value):
    return json.loads(json.dumps(asdict(value)))


def power(id="bolt", *, activation="ACTION", program=None, cost=3, sta=2, range_mm=10000):
    return Ability(id=id, name=id.title(), source_kind="CLASS", source_id="fixture-class", rarity="COMMON",
                   activation=activation, manifestation=("Gesture", "Sound", "Motion", "Contact", "Aftermath"),
                   mp_cost=cost, sta_cost=sta, range_mm=range_mm, targets="Explicit program targets",
                   resolution="Executable program", trigger="Executable program", duration="Executable program",
                   cooldown="Executable program", prerequisites="Executable program", stacking="Executable program",
                   limits="Executable program", program=program or Program((Effect("DAMAGE", Formula(1, 6, 2, "INT"), "ARCANE"),),
                       resolution=Resolution("ATTACK", "INT")))


def character():
    attributes = dict.fromkeys(ATTRIBUTES, 5)
    stats = derived(attributes)
    return {"attributes": attributes, **stats, "hp": stats["hp_max"], "mp": stats["mp_max"], "sta": stats["sta_max"]}


def actor(id, *, abilities=(), position=None, team=None, **changes):
    result = {"id": id, "name": id.title(), "team": team or ("heroes" if id == "player" else "foes"),
              **character(), "position": position or [0 if id == "player" else 3000, 0, 0],
              "abilities": [data(ability) for ability in abilities]}
    result.pop("carry_capacity_kg")
    result.update(changes)
    return result


def scenario(player_powers=(), *, enemy_powers=(), other_actors=(), player_changes=None, enemy_changes=None, solids=None):
    actors = [actor("player", abilities=player_powers, **(player_changes or {})),
              actor("enemy", abilities=enemy_powers, **(enemy_changes or {})), *other_actors]
    return combat.prepare(character(), actors, [row["id"] for row in actors], solids or [])


class Rolls:
    def __init__(self, *values):
        self.values, self.sides = iter(values), []
        self.dice = Dice(self.draw)

    def draw(self, sides):
        self.sides.append(sides)
        return next(self.values) - 1


def start(encounter, rolls=None):
    return combat.apply(encounter, "start_combat", {}, (rolls or Rolls()).dice)[0]


def cast(encounter, rolls, id="bolt", targets=None, caster="player", **kwargs):
    return combat.apply(encounter, "use_ability", {"actor_id": caster, "ability_id": id,
                        "target_ids": targets or ["enemy"]}, rolls.dice, **kwargs)


def next_round(encounter):
    for id in ("player", "enemy"):
        encounter = combat.apply(encounter, "end_turn", {"actor_id": id}, Rolls().dice)[0]
    return encounter


def test_executable_contract_round_trips_and_legacy_text_is_not_execution():
    original = power()
    assert decode_ability(data(original)) == original
    imprint = Imprint(original.id, "Integrated light", "Parent timing only", Rider((Effect("DAMAGE", Formula(flat=1), "LIGHT"),)))
    assert decode_imprint(data(imprint)) == imprint
    legacy = replace(original, program=None)
    assert decode_ability(data(legacy)) == legacy
    with pytest.raises(ValueError, match="executable"):
        scenario((legacy,))


@pytest.mark.parametrize("change", [
    {"effects": []}, {"python": "arbitrary code"}, {"resolution": {"kind": "SCRIPT"}},
    {"cooldown_turns": True}, {"max_targets": 0}, {"required_conditions": [{"bad": "value"}]},
    {"effects": [{"kind": "HEAL", "amount": {"flat": 3}, "condition": {"arbitrary": True}}]},
    {"effects": [{"kind": "DAMAGE", "amount": {"flat": 3}, "damage_type": "ARCANE", "save_half": True}]},
])
def test_unknown_or_inconsistent_mechanics_are_rejected(change):
    definition = data(power().program)
    definition.update(change)
    with pytest.raises(ValueError):
        decode_program(definition)


def test_miss_spends_actual_costs_once_and_preview_draws_nothing():
    encounter = start(scenario((power(),)))
    original = deepcopy(encounter)
    rolls = Rolls(1)
    projected, receipt = cast(encounter, rolls, preview=True)
    assert rolls.sides == []
    assert receipt["preview"] and projected["actors"]["player"]["mp"] == character()["mp"] - 3
    committed, receipt = cast(encounter, rolls)
    assert encounter == original
    assert rolls.sides == [20]  # No damage die on a miss.
    assert committed["actors"]["enemy"]["hp"] == character()["hp"]
    assert committed["actors"]["player"]["mp"] == character()["mp"] - 3
    assert committed["actors"]["player"]["sta"] == character()["sta"] - 2
    assert committed["actors"]["player"]["budget"]["action"] == 0
    assert receipt["ledger"][0]["targets"][0]["success"] is False


def test_critical_doubles_base_dice_but_not_modifiers_or_integrated_rider():
    imprint = {"id": "background-one", "parent_id": "bolt",
               "rider": data(Rider((Effect("DAMAGE", Formula(1, 4, 1), "LIGHT"),)))}
    encounter = start(scenario((power(),), player_changes={"imprints": [imprint]}))
    rolls = Rolls(20, 6, 5, 4)
    result, receipt = cast(encounter, rolls)
    assert rolls.sides == [20, 6, 6, 4]
    assert result["actors"]["enemy"]["hp"] == character()["hp"] - (6 + 5 + 2 + 4 + 1)
    effects = receipt["ledger"][0]["targets"][0]["effects"]
    assert effects[0]["rolls"] == [6, 5] and effects[0]["bonus"] == 2
    assert effects[1]["rolls"] == [4] and not effects[1]["critical"]
    assert result["actors"]["player"]["budget"]["free_action"] == 1


def test_save_half_resistance_and_immunity_preserve_real_costs():
    spell = power(program=Program((Effect("DAMAGE", Formula(1, 6, 3), "FIRE", save_half=True),),
                                  resolution=Resolution("SAVE", "INT", save_attribute="AGI")))
    for ratio, expected in (([1, 2], 2), ([0, 1], 0), ([2, 1], 8)):
        encounter = start(scenario((spell,), enemy_changes={"resistances": {"FIRE": ratio}}))
        result, receipt = cast(encounter, Rolls(12, 6))
        assert receipt["ledger"][0]["targets"][0]["dc"] == 12
        assert result["actors"]["enemy"]["hp"] == character()["hp"] - expected
        assert result["actors"]["player"]["mp"] == character()["mp"] - 3


@pytest.mark.parametrize("mutation,targets", [
    ({}, ["enemy", "missing"]), ({}, ["enemy", "enemy"]), ({}, ["player"]),
    ({"position": [20000, 0, 0]}, ["enemy"]),
])
def test_every_target_is_validated_before_rng_and_spending(mutation, targets):
    spell = power(program=Program(power().program.effects, max_targets=2, resolution=Resolution("ATTACK", "INT")))
    encounter = start(scenario((spell,), enemy_changes=mutation))
    original, rolls = deepcopy(encounter), Rolls()
    with pytest.raises(ValueError):
        cast(encounter, rolls, targets=targets)
    assert encounter == original and rolls.sides == []


def test_solid_cover_rejects_cast_before_roll_and_movement_cannot_cross_wall():
    box = {"minimum": [1000, -1000, -1000], "maximum": [2000, 1000, 1000]}
    encounter = start(scenario((power(),), solids=[box]))
    rolls = Rolls()
    with pytest.raises(ValueError, match="cover"):
        cast(encounter, rolls)
    with pytest.raises(ValueError, match="geometry"):
        combat.apply(encounter, "combat_move", {"actor_id": "player", "path": [[3000, 0, 0]]}, rolls.dice)
    assert rolls.sides == []


def test_movement_uses_entire_three_dimensional_path_and_preserves_action():
    encounter = start(scenario())
    with pytest.raises(ValueError, match="movement_mm"):
        combat.apply(encounter, "combat_move", {"actor_id": "player", "path": [[3000, 0, 0], [3000, 0, 4000]]}, Rolls().dice)
    result, receipt = combat.apply(encounter, "combat_move", {"actor_id": "player", "path": [[3000, 0, 4000]]}, Rolls().dice)
    assert receipt["ledger"][0]["movement_mm"] == 5000
    assert result["actors"]["player"]["budget"]["movement_mm"] == 1000
    assert result["actors"]["player"]["budget"]["action"] == 1


def test_cooldown_blocks_whole_subsequent_turn_and_encounter_uses_do_not_reset():
    spell = power(program=replace(power().program, cooldown_turns=1, uses_per_encounter=2))
    encounter, _ = cast(start(scenario((spell,))), Rolls(1))
    encounter = next_round(encounter)
    with pytest.raises(ValueError, match="cooling"):
        cast(encounter, Rolls())
    encounter = next_round(encounter)
    encounter, _ = cast(encounter, Rolls(1))
    encounter = next_round(next_round(encounter))
    with pytest.raises(ValueError, match="encounter limit"):
        cast(encounter, Rolls())
    assert encounter["round"] == 5


def test_free_action_is_separate_and_per_turn_limit_blocks_duplicate_use():
    free = power("quick", activation="FREE_ACTION")
    encounter, _ = cast(start(scenario((power(), free))), Rolls(1))
    encounter, _ = cast(encounter, Rolls(1), "quick")
    assert encounter["actors"]["player"]["budget"]["action"] == 0
    assert encounter["actors"]["player"]["budget"]["free_action"] == 0
    with pytest.raises(ValueError, match="budget"):
        cast(encounter, Rolls(), "quick")


def test_condition_blocks_activation_then_expires_on_targets_turn():
    stun = power("stun", program=Program((Effect("CONDITION", condition=Condition("stunned", "Stunned", 1, blocks=("ACTION",))),)))
    encounter, _ = cast(start(scenario((stun,), enemy_powers=(power(),))), Rolls(), "stun")
    encounter = combat.apply(encounter, "end_turn", {"actor_id": "player"}, Rolls().dice)[0]
    with pytest.raises(ValueError, match="cannot activate"):
        cast(encounter, Rolls(), caster="enemy", targets=["player"])
    encounter = combat.apply(encounter, "end_turn", {"actor_id": "enemy"}, Rolls().dice)[0]
    assert encounter["actors"]["enemy"]["conditions"] == []


def test_conflicting_condition_definition_rejected_before_attack_die():
    first = power("first", activation="FREE_ACTION", program=Program((Effect("CONDITION", condition=Condition("mark", "Marked", 3)),)))
    second = power("second", program=Program((Effect("CONDITION", condition=Condition("mark", "Different", 1)),),
                                             resolution=Resolution("ATTACK", "INT")))
    encounter, _ = cast(start(scenario((first, second))), Rolls(), "first")
    rolls = Rolls()
    with pytest.raises(ValueError, match="conflicting"):
        cast(encounter, rolls, "second")
    assert rolls.sides == []


def test_caster_effect_applies_once_for_many_targets_and_healing_is_capped():
    drain = power("drain", program=Program((Effect("DAMAGE", Formula(flat=2), "ARCANE"),
        Effect("HEAL", Formula(flat=20), recipient="CASTER")), max_targets=2))
    encounter = start(scenario((drain,), other_actors=(actor("second"),)))
    # Pure effect fixture: begin with seven missing HP.
    encounter["actors"]["player"]["hp"] -= 7
    result, receipt = cast(encounter, Rolls(), "drain", ["enemy", "second"])
    assert result["actors"]["player"]["hp"] == character()["hp"]
    assert len(receipt["ledger"][0]["caster_effects"]) == 1
    assert receipt["ledger"][0]["caster_effects"][0]["restored"] == 7


def test_passive_uses_real_turn_trigger_and_cannot_be_cast():
    passive = power("renew", activation="PASSIVE", cost=0, sta=0, range_mm=0,
                    program=Program((Effect("RESTORE_MP", Formula(flat=2)),), target_kind="SELF", passive_trigger="TURN_START"))
    encounter = start(scenario((power(), passive)))
    with pytest.raises(ValueError, match="internal trigger"):
        cast(encounter, Rolls(), "renew", ["player"])
    encounter, _ = cast(encounter, Rolls(1))
    encounter = next_round(encounter)
    assert encounter["actors"]["player"]["mp"] == character()["mp"] - 1
    assert encounter["actors"]["player"]["budget"]["action"] == 1


def test_defensive_reaction_only_runs_on_incoming_damage_with_committed_policy():
    guard = power("guard", activation="REACTION", cost=2, sta=0, range_mm=0,
                  program=Program((Effect("WARD", Formula(flat=8), duration_turns=1),), target_kind="SELF",
                                  reaction_trigger="INCOMING_DAMAGE"))
    strike = power("strike", program=Program((Effect("DAMAGE", Formula(flat=10), "PHYSICAL"),)))
    encounter = start(scenario((guard,), enemy_powers=(strike,), player_changes={"reaction_policy": "MITIGATE"}))
    with pytest.raises(ValueError, match="internal trigger"):
        cast(encounter, Rolls(), "guard", ["player"])
    encounter = combat.apply(encounter, "end_turn", {"actor_id": "player"}, Rolls().dice)[0]
    result, receipt = cast(encounter, Rolls(), "strike", ["player"], "enemy")
    player = result["actors"]["player"]
    assert player["hp"] == character()["hp"] - 2
    assert player["mp"] == character()["mp"] - 2 and player["budget"]["reaction"] == 0
    assert receipt["ledger"][1]["trigger"] == "INCOMING_DAMAGE"
    assert receipt["ledger"][0]["targets"][0]["effects"][0]["ward_absorbed"] == 8


def test_unavailable_reaction_and_immunity_never_spend_reaction_resources():
    guard = power("guard", activation="REACTION", cost=2, sta=0, range_mm=0,
        program=Program((Effect("WARD", Formula(flat=8), duration_turns=1),), target_kind="SELF",
                        reaction_trigger="INCOMING_DAMAGE", uses_per_encounter=1))
    strike = power("strike", program=Program((Effect("DAMAGE", Formula(flat=10), "PHYSICAL"),)))
    for changes in ({"reaction_policy": "CONSERVE"}, {"reaction_policy": "MITIGATE"},
                    {"reaction_policy": "MITIGATE", "resistances": {"PHYSICAL": [0, 1]}}):
        encounter = start(scenario((guard,), enemy_powers=(strike,), player_changes=changes))
        encounter = combat.apply(encounter, "end_turn", {"actor_id": "player"}, Rolls().dice)[0]
        result, receipt = cast(encounter, Rolls(), "strike", ["player"], "enemy")
        assert result["actors"]["player"]["mp"] == character()["mp"]
        assert result["actors"]["player"]["budget"]["reaction"] == 1
        assert len(receipt["ledger"]) == 1


def test_incapacitation_ends_combat_and_stops_followup_damage_rolls():
    finisher = power(program=Program((Effect("DAMAGE", Formula(flat=1000), "ARCANE"),
                                     Effect("DAMAGE", Formula(1, 6), "ARCANE"))))
    rolls = Rolls()
    result, receipt = cast(start(scenario((finisher,))), rolls)
    assert result["status"] == "complete" and result["actors"]["enemy"]["hp"] == 0
    assert rolls.sides == [] and len(receipt["ledger"][0]["targets"][0]["effects"]) == 1
    assert receipt["elapsed_seconds"] == 6
    with pytest.raises(ValueError, match="active turn"):
        combat.apply(result, "end_turn", {"actor_id": "player"}, rolls.dice)


@pytest.mark.parametrize("program,cost", [
    (Program(power().program.effects, minimum_attributes=(("INT", 9),)), 3),
    (Program(power().program.effects, required_conditions=("focus",)), 3),
    (power().program, 1000),
])
def test_unmet_prerequisites_and_resources_fail_before_any_roll(program, cost):
    encounter = start(scenario((power(program=program, cost=cost),)))
    rolls = Rolls()
    with pytest.raises(ValueError):
        cast(encounter, rolls)
    assert rolls.sides == [] and encounter["actors"]["player"]["mp"] == character()["mp"]


def test_damage_formula_adds_attribute_only_once_on_critical():
    rolls = Rolls(5, 6)
    amount, receipt = Formula(1, 6, 2, "INT").resolve({"INT": 9}, rolls.dice, critical=True)
    assert amount == 15 and receipt["bonus"] == 4 and receipt["rolls"] == [5, 6]


def test_execution_imprint_follows_parent_miss_without_a_separate_action():
    imprint = {"id": "background-one", "parent_id": "bolt", "rider": data(Rider((
        Effect("RESTORE_STA", Formula(flat=1), recipient="CASTER"),), trigger="EXECUTION"))}
    encounter = start(scenario((power(),), player_changes={"imprints": [imprint]}))
    result, receipt = cast(encounter, Rolls(1))
    assert result["actors"]["player"]["sta"] == character()["sta"] - 1
    assert len(receipt["ledger"]) == 1 and receipt["ledger"][0]["caster_effects"][0]["source"] == "EXECUTION"
    with pytest.raises(ValueError, match="not owned"):
        cast(start(scenario((power(),), player_changes={"imprints": [imprint]})), Rolls(), "background-one")


def test_self_ward_never_refills_hp_and_expires_after_its_defined_turns():
    ward = power("ward", activation="FREE_ACTION", program=Program((
        Effect("WARD", Formula(flat=10), duration_turns=1),), target_kind="SELF"))
    encounter, _ = cast(start(scenario((ward,))), Rolls(), "ward", ["player"])
    assert encounter["actors"]["player"]["ward"]["amount"] == 10
    assert encounter["actors"]["player"]["hp"] == character()["hp"]
    encounter = next_round(encounter)
    assert encounter["actors"]["player"]["ward"]["amount"] == 10
    encounter = combat.apply(encounter, "end_turn", {"actor_id": "player"}, Rolls().dice)[0]
    assert encounter["actors"]["player"]["ward"] is None


def test_condition_penalty_defense_and_removal_use_the_written_definition():
    snare = power("snare", program=Program((Effect("CONDITION", condition=Condition(
        "snare", "Snared", 2, defense_bonus=-2, movement_penalty_mm=4000)),)))
    cure = power("cure", activation="FREE_ACTION", program=Program((
        Effect("REMOVE_CONDITION", condition_id="snare"),), target_kind="SELF"))
    encounter, _ = cast(start(scenario((snare,), enemy_powers=(cure,))), Rolls(), "snare")
    encounter = combat.apply(encounter, "end_turn", {"actor_id": "player"}, Rolls().dice)[0]
    assert encounter["actors"]["enemy"]["budget"]["movement_mm"] == 2000
    assert combat.Runtime(encounter, Rolls().dice, False).bonus(encounter["actors"]["enemy"], "defense_bonus") == -2
    encounter, _ = cast(encounter, Rolls(), "cure", ["enemy"], "enemy")
    assert encounter["actors"]["enemy"]["conditions"] == []
    # Removing a penalty does not silently refund movement already lost this turn.
    assert encounter["actors"]["enemy"]["budget"]["movement_mm"] == 2000


def test_three_dimensional_range_uses_actual_distance():
    spell = power(range_mm=5000)
    encounter = start(scenario((spell,), enemy_changes={"position": [3000, 0, 4000]}))
    result, _ = cast(encounter, Rolls(10, 2))
    assert result["actors"]["enemy"]["hp"] == character()["hp"] - 4
    encounter = start(scenario((spell,), enemy_changes={"position": [3000, 0, 4001]}))
    with pytest.raises(ValueError, match="range"):
        cast(encounter, Rolls())


@pytest.mark.parametrize("player_changes", [{"mp": 1}, {"hp_max": 1000}, {"attributes": dict.fromkeys(ATTRIBUTES, 9)}])
def test_scenario_cannot_grant_player_resources_or_attributes(player_changes):
    with pytest.raises(ValueError, match="cannot change"):
        scenario(player_changes=player_changes)


def test_nonmagical_enemy_can_have_no_mp_and_imprint_cannot_add_activation_fields():
    encounter = scenario(enemy_changes={"mp": 0, "mp_max": 0})
    assert encounter["actors"]["enemy"]["mp"] == 0
    imprint = {"id": "background-one", "parent_id": "bolt", "rider": data(Rider((
        Effect("DAMAGE", Formula(flat=1), "LIGHT"),))), "mp_cost": 0}
    with pytest.raises(ValueError, match="fields"):
        scenario((power(),), player_changes={"imprints": [imprint]})
