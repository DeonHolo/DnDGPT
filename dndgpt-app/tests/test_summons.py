"""Actual summons in disposable encounters; no generated class/tier assertions."""
from copy import deepcopy
from dataclasses import asdict, replace
import json

import pytest

from app import combat
from app.abilities import decode
from app.powers import Condition, Effect, Formula, Program, Resolution
from app.rules import ATTRIBUTES
from app.summons import Behavior, Command, Manifest, Unit
from .test_powers import Rolls, actor, character, power, start


def unit(id="mote", *, control="COMMANDED", behavior=None, **changes):
    strike = replace(power("strike-" + id, cost=0, sta=0, range_mm=2000,
        program=Program((Effect("DAMAGE", Formula(flat=3), "ARCANE"),), resolution=Resolution("ATTACK", "INT"))),
        source_kind="SUMMON", source_id=id)
    values = dict(id=id, name="Fixture " + id, attributes=tuple(dict.fromkeys(ATTRIBUTES, 5).items()),
        hp=8, defense=10, movement_mm=6000, half_extents_mm=(100, 100, 100), abilities=(strike,),
        control=control, utility="Fixture bounded presence", weaknesses="Fixed fragile body",
        special_interactions="No extra unlisted powers", behavior=behavior or Behavior("WAIT"))
    values.update(changes)
    return Unit(**values)


def summon_power(*units, **changes):
    plan_values = dict(family="fixture-family", units=units or (unit(),), max_active=6, duration_rounds=3)
    plan_values.update(changes)
    return power("manifest", cost=4, sta=0, range_mm=10000,
        program=Program((), target_kind="SELF", summon=Manifest(**plan_values)))


def command_power(**changes):
    values = dict(family="fixture-family", max_units=6, range_mm=10000, can_move=True,
                  can_act=True, move_and_act=False)
    values.update(changes)
    return power("direct", activation="FREE_ACTION", cost=2, sta=0,
                 program=Program((), target_kind="SELF", command=Command(**values)))


def scenario(manifest=None, command=None, *, obstacles=(), enemy=None, other=()):
    player = actor("player", abilities=(manifest or summon_power(), command or command_power(), *other))
    return start(combat.prepare(character(), [player, enemy or actor("enemy")],
                                ["player", "enemy"], list(obstacles)))


def manifest(encounter, rolls=None, positions=None, *, preview=False):
    template = decode(encounter["actors"]["player"]["abilities"][0]).program.summon
    placements = [{"template_id": row.id, "position": pos} for row,pos in zip(template.units,
                   positions or [[1000+i*500, i*500, 0] for i in range(len(template.units))])]
    return combat.apply(encounter, "manifest_summons", {"actor_id": "player", "ability_id": "manifest",
                        "placements": placements}, (rolls or Rolls()).dice, preview=preview)


def command(encounter, orders, rolls=None, *, preview=False):
    return combat.apply(encounter, "command_summons", {"actor_id": "player", "ability_id": "direct",
                        "orders": orders}, (rolls or Rolls()).dice, preview=preview)


def cycle(encounter, rolls=None):
    for id in ("player", "enemy"):
        encounter = combat.apply(encounter, "end_turn", {"actor_id": id}, (rolls or Rolls()).dice)[0]
    return encounter


def test_template_and_source_program_roundtrip_with_exact_laws():
    original = summon_power(unit(), unit("other"), duration_rounds=None)
    assert decode(json.loads(json.dumps(asdict(original)))) == original
    assert decode(json.loads(json.dumps(asdict(command_power())))) == command_power()
    with pytest.raises(ValueError, match="provenance"):
        unit(abilities=(power(),))
    with pytest.raises(ValueError, match="autonomous"):
        unit(behavior=Behavior("NEAREST_HOSTILE", "strike-mote"))
    with pytest.raises(ValueError, match="typed formation"):
        Program((), target_kind="SELF", summon={"inferred": "creature"})


def test_formation_has_actual_bodies_and_one_owner_cost_without_free_turns():
    state = scenario(summon_power(*(unit(str(n)) for n in range(4))))
    projected, preview = manifest(state, preview=True)
    result, receipt = manifest(state)
    assert len(result["actors"]) == 6 and result["order"] == ["player", "enemy"]
    assert result["actors"]["player"]["mp"] == 51 and result["actors"]["player"]["budget"]["action"] == 0
    assert all(result["actors"]["summon-"+str(n)]["hp"] == 8 for n in range(1,5))
    assert projected == result and preview["preview"] is True
    assert len([row for row in receipt["ledger"] if row.get("manifested")]) == 4
    with pytest.raises(ValueError, match="active turn"):
        combat.apply(result, "use_ability", {"actor_id":"summon-1", "ability_id":"strike-0", "target_ids":["enemy"]}, Rolls().dice)


@pytest.mark.parametrize("positions", ([[20000,0,0]], [[0,0,0]], [[1000,0,False]]))
def test_illegal_placement_never_spends_or_rolls(positions):
    state, rolls = scenario(), Rolls()
    before = deepcopy(state)
    with pytest.raises(ValueError):
        manifest(state, rolls, positions)
    assert state == before and rolls.sides == []


def test_footprint_not_just_center_is_checked_against_solids():
    state = scenario(obstacles=({"minimum":[1100,-500,-500], "maximum":[1200,500,500]},))
    with pytest.raises(ValueError, match="footprint"):
        manifest(state, positions=[[1050,0,0]])


def test_move_or_act_command_cannot_do_both_and_consumes_no_resources_on_error():
    state = manifest(scenario())[0]
    before, rolls = deepcopy(state), Rolls()
    with pytest.raises(ValueError, match="combinations"):
        command(state, [{"summon_id":"summon-1", "path":[[1100,0,0]],
                         "ability_id":"strike-mote", "target_ids":["enemy"]}], rolls)
    assert state == before and rolls.sides == []


def test_one_shared_command_rolls_each_units_attack_and_spends_each_budget_once():
    state = manifest(scenario(summon_power(unit("a"), unit("b"))))[0]
    orders=[{"summon_id":"summon-1", "ability_id":"strike-a", "target_ids":["enemy"]},
            {"summon_id":"summon-2", "ability_id":"strike-b", "target_ids":["enemy"]}]
    rolls = Rolls(1,12)
    result, _ = command(state, orders, rolls)
    assert rolls.sides == [20,20] and result["actors"]["enemy"]["hp"] == 92
    assert result["actors"]["player"]["mp"] == 49
    assert result["actors"]["player"]["budget"]["free_action"] == 0
    assert result["actors"]["summon-1"]["budget"]["action"] == result["actors"]["summon-2"]["budget"]["action"] == 0


def test_second_illegal_order_is_rejected_before_the_first_attack_draw():
    state = manifest(scenario(summon_power(unit("a"), unit("b"))))[0]
    rolls = Rolls()
    with pytest.raises(ValueError, match="Unknown combat actor"):
        command(state, [{"summon_id":"summon-1", "ability_id":"strike-a", "target_ids":["enemy"]},
                        {"summon_id":"summon-2", "ability_id":"strike-b", "target_ids":["missing"]}], rolls)
    assert rolls.sides == [] and state["actors"]["player"]["mp"] == 51


def test_multiple_attack_followup_stops_after_incapacitation_without_extra_rolls():
    state = manifest(scenario(summon_power(unit("a"), unit("b")), enemy=actor("enemy", hp=2)))[0]
    rolls = Rolls(12)
    result, receipt = command(state, [{"summon_id":"summon-1", "ability_id":"strike-a", "target_ids":["enemy"]},
                                     {"summon_id":"summon-2", "ability_id":"strike-b", "target_ids":["enemy"]}], rolls)
    assert rolls.sides == [20] and result["status"] == "complete"
    assert result["actors"]["summon-2"]["budget"]["action"] == 1
    assert any("skipped" in row for row in receipt["ledger"])


def test_commands_observe_owner_family_control_range_and_duplicate_units():
    autonomous = unit("auto", control="AUTONOMOUS")
    state = manifest(scenario(summon_power(unit(), autonomous)))[0]
    for orders in ([{"summon_id":"summon-2", "path":[[1000,2000,0]]}],
                   [{"summon_id":"summon-1", "path":[[1000,1000,0]]}]*2,
                   [{"summon_id":"enemy", "path":[[1000,1000,0]]}]):
        with pytest.raises(ValueError, match="distinct living owned"):
            command(state, orders)
    short = manifest(scenario(command=command_power(range_mm=500)))[0]
    with pytest.raises(ValueError, match="command range"):
        command(short, [{"summon_id":"summon-1", "path":[[1000,1000,0]]}])


def test_declared_move_and_act_uses_actual_unit_movement_and_action():
    state = manifest(scenario(command=command_power(move_and_act=True), enemy=actor("enemy",position=[5000,0,0])))[0]
    result,_ = command(state,[{"summon_id":"summon-1", "path":[[3000,0,0]],
                              "ability_id":"strike-mote", "target_ids":["enemy"]}],Rolls(12))
    assert result["actors"]["summon-1"]["movement_spent_mm"] == 2000
    assert result["actors"]["summon-1"]["budget"]["movement_mm"] == 4000
    assert result["actors"]["summon-1"]["budget"]["action"] == 0


def test_autonomous_units_follow_their_own_phase_without_owner_command_cost():
    autonomous = unit(control="AUTONOMOUS",behavior=Behavior("NEAREST_HOSTILE","strike-mote"))
    state = manifest(scenario(summon_power(autonomous)))[0]
    rolls = Rolls(12)
    result,_=combat.apply(state,"end_turn",{"actor_id":"player"},rolls.dice)
    assert result["actors"]["enemy"]["hp"] == 92 and rolls.sides == [20]
    assert result["actors"]["player"]["mp"] == 51 and result["active"] == "enemy"
    with pytest.raises(ValueError,match="active turn"):
        combat.apply(result,"end_turn",{"actor_id":"player"},rolls.dice)


def test_autonomous_move_or_attack_does_not_secretly_do_both():
    autonomous = unit(control="AUTONOMOUS",behavior=Behavior("NEAREST_HOSTILE","strike-mote",True,False))
    state = manifest(scenario(summon_power(autonomous),enemy=actor("enemy",position=[7000,0,0])))[0]
    rolls=Rolls()
    result,_=combat.apply(state,"end_turn",{"actor_id":"player"},rolls.dice)
    assert result["actors"]["summon-1"]["position"] == [5000,0,0]
    assert result["actors"]["enemy"]["hp"] == 95 and rolls.sides == []


def test_duration_and_replacement_are_actual_rules_not_resource_refills():
    state = manifest(scenario(summon_power(duration_rounds=1)))[0]
    state=cycle(state)
    assert "summon-1" not in state["actors"] and state["round"] == 2
    state=manifest(state)[0]
    assert "summon-2" in state["actors"] and state["actors"]["player"]["mp"] == 47
    state=manifest(scenario(summon_power(max_active=1,duration_rounds=None)))[0]
    state=cycle(state)
    with pytest.raises(ValueError,match="active summon cap"):
        manifest(state)
    state=manifest(scenario(summon_power(max_active=1,duration_rounds=None,replacement="REPLACE_FAMILY")))[0]
    state=cycle(state)
    result,receipt=manifest(state)
    assert "summon-1" not in result["actors"] and "summon-2" in result["actors"]
    assert any(row.get("departure")=="REPLACED" for row in receipt["ledger"])


def test_destroyed_units_leave_the_actual_roster_and_owner_loss_dismisses_dependents():
    enemy = actor("enemy", abilities=(power("enemy-hit",cost=0,sta=0,
        program=Program((Effect("DAMAGE",Formula(flat=10),"ARCANE"),))),))
    state=manifest(scenario(enemy=enemy))[0]
    state=combat.apply(state,"end_turn",{"actor_id":"player"},Rolls().dice)[0]
    result,receipt=combat.apply(state,"use_ability",{"actor_id":"enemy","ability_id":"enemy-hit",
                                "target_ids":["summon-1"]},Rolls().dice)
    assert "summon-1" not in result["actors"]
    assert any(row.get("departure")=="DESTROYED" for row in receipt["ledger"])
    enemy = actor("enemy", abilities=(power("lethal",cost=0,sta=0,
        program=Program((Effect("DAMAGE",Formula(flat=1000),"ARCANE"),))),))
    state=manifest(scenario(enemy=enemy))[0]
    state=combat.apply(state,"end_turn",{"actor_id":"player"},Rolls().dice)[0]
    result,receipt=combat.apply(state,"use_ability",{"actor_id":"enemy","ability_id":"lethal",
                                "target_ids":["player"]},Rolls().dice)
    assert "summon-1" not in result["actors"] and result["status"] == "complete"
    assert any(row.get("departure")=="OWNER_LOST" for row in receipt["ledger"])


def test_preview_of_autonomous_phase_draws_nothing_and_does_not_resolve_damage():
    autonomous=unit(control="AUTONOMOUS",behavior=Behavior("NEAREST_HOSTILE","strike-mote"))
    state=manifest(scenario(summon_power(autonomous)))[0]
    rolls=Rolls()
    projected,receipt=combat.apply(state,"end_turn",{"actor_id":"player"},rolls.dice,preview=True)
    assert rolls.sides == [] and receipt["preview"]
    assert projected["actors"]["enemy"]["hp"] == state["actors"]["enemy"]["hp"] == 95
    assert state["actors"]["summon-1"]["summon"]["last_autonomous_round"] == 0


def test_a_command_does_not_reset_a_units_budget_or_uses():
    # Separate owned Action and Free Action commands still cannot refresh a unit.
    direct=command_power()
    extra=replace(direct,id="extra-command",activation="ACTION")
    state=cycle(manifest(scenario(other=(extra,)))[0])
    orders=[{"summon_id":"summon-1","ability_id":"strike-mote","target_ids":["enemy"]}]
    state=command(state,orders,Rolls(12))[0]
    rolls=Rolls()
    with pytest.raises(ValueError,match="budget"):
        combat.apply(state,"command_summons",{"actor_id":"player","ability_id":"extra-command","orders":orders},rolls.dice)
    assert rolls.sides == [] and state["actors"]["player"]["budget"]["action"] == 1


def test_conditional_followup_movement_stops_if_an_earlier_effect_blocks_it():
    first,second=unit("a"),unit("b")
    root=Condition("rooted","Fixture root",2,blocks=("MOVEMENT",))
    binding=replace(first.abilities[0],program=Program((Effect("CONDITION",condition=root),),
                    resolution=Resolution("ATTACK","INT"),target_kind="ALLY"))
    first=replace(first,abilities=(binding,))
    state=manifest(scenario(summon_power(first,second)))[0]
    rolls=Rolls(12)
    result,receipt=command(state,[{"summon_id":"summon-1","ability_id":"strike-a","target_ids":["summon-2"]},
                                 {"summon_id":"summon-2","path":[[2000,1000,0]]}],rolls)
    assert rolls.sides == [20] and result["actors"]["summon-2"]["position"] == [1500,500,0]
    assert result["actors"]["summon-2"]["conditions"][0]["definition"]["id"] == "rooted"
    assert any("skipped" in row for row in receipt["ledger"])


def test_unit_body_volume_and_declared_blocking_affect_real_movement():
    wall={"minimum":[1800,200,-200],"maximum":[2200,400,200]}
    state=manifest(scenario(summon_power(unit(half_extents_mm=(100,300,100))),obstacles=(wall,)))[0]
    # Center line y=0 clears the wall, but the declared body does not.
    with pytest.raises(ValueError,match="geometry"):
        command(state,[{"summon_id":"summon-1","path":[[3000,0,0]]}])
    state=manifest(scenario(summon_power(unit(blocks_movement=True))))[0]
    with pytest.raises(ValueError,match="blocking creature"):
        combat.apply(state,"combat_move",{"actor_id":"player","path":[[2000,0,0]]},Rolls().dice)


def test_autonomous_move_and_act_and_obstruction_obey_the_written_rule():
    autonomous=unit(control="AUTONOMOUS",behavior=Behavior("NEAREST_HOSTILE","strike-mote",True,True))
    state=manifest(scenario(summon_power(autonomous),enemy=actor("enemy",position=[7000,0,0])))[0]
    result,_=combat.apply(state,"end_turn",{"actor_id":"player"},Rolls(12).dice)
    assert result["actors"]["summon-1"]["position"] == [5000,0,0] and result["actors"]["enemy"]["hp"] == 92
    wall={"minimum":[2500,-500,-500],"maximum":[2600,500,500]}
    state=manifest(scenario(summon_power(autonomous),enemy=actor("enemy",position=[7000,0,0]),obstacles=(wall,)))[0]
    rolls=Rolls()
    result,_=combat.apply(state,"end_turn",{"actor_id":"player"},rolls.dice)
    assert result["actors"]["summon-1"]["position"] == [1000,0,0] and rolls.sides == []


def test_generic_cast_cannot_bypass_manifest_placement_or_command_permissions():
    state=scenario()
    for id in ("manifest","direct"):
        with pytest.raises(ValueError,match="explicit"):
            combat.apply(state,"use_ability",{"actor_id":"player","ability_id":id,"target_ids":["player"]},Rolls().dice)


def test_a_summoner_label_cannot_publish_an_ordinary_attack_as_summoning():
    from app import creation
    from .test_creation import concepts,offers,power as source_power,roll_board
    from app.rules import Dice
    draft=roll_board(creation.allocate_luck(creation.Draft("Fixture world"),0),"classes",concepts("classes"),Dice(lambda _:0))
    proposed=list(offers(draft,"classes"))
    proposed[0]=replace(proposed[0],abilities=(source_power("classes",proposed[0].candidate_id,proposed[0].rarity),))
    with pytest.raises(ValueError,match="actual supported summoning"):
        creation.complete_board(draft,"classes",tuple(proposed))
    valid=creation.complete_board(draft,"classes",offers(draft,"classes"))
    assert creation.public_preview(valid)["board_programs"]["classes"]["programs_validated"]


@pytest.mark.parametrize("policy,remaining",[("CONSERVE",2),("MITIGATE",7)])
def test_summon_reaction_obeys_its_actual_declared_policy_and_budget(policy,remaining):
    creature=unit(reaction_policy=policy)
    ward=replace(creature.abilities[0],id="unit-ward",activation="REACTION",program=Program(
        (Effect("WARD",Formula(flat=5),duration_turns=1),),target_kind="SELF",reaction_trigger="INCOMING_DAMAGE"))
    creature=replace(creature,abilities=(*creature.abilities,ward))
    enemy=actor("enemy",abilities=(power("hit",cost=0,sta=0,program=Program((Effect("DAMAGE",Formula(flat=6),"ARCANE"),))),))
    state=manifest(scenario(summon_power(creature),enemy=enemy))[0]
    state=combat.apply(state,"end_turn",{"actor_id":"player"},Rolls().dice)[0]
    result,_=combat.apply(state,"use_ability",{"actor_id":"enemy","ability_id":"hit","target_ids":["summon-1"]},Rolls().dice)
    assert result["actors"]["summon-1"]["hp"] == remaining
    assert result["actors"]["summon-1"]["budget"]["reaction"] == (0 if policy=="MITIGATE" else 1)


def test_commanded_unit_cooldown_is_not_reset_by_owner_commands_or_new_rounds():
    creature=unit()
    creature=replace(creature,abilities=(replace(creature.abilities[0],program=replace(creature.abilities[0].program,cooldown_turns=1)),))
    state=manifest(scenario(summon_power(creature)))[0]
    orders=[{"summon_id":"summon-1","ability_id":"strike-mote","target_ids":["enemy"]}]
    state=command(state,orders,Rolls(12))[0]
    state=cycle(state)
    with pytest.raises(ValueError,match="cooling down"):
        command(state,orders)
    assert state["actors"]["player"]["mp"] == 49
    state=cycle(state)
    result,_=command(state,orders,Rolls(12))
    assert result["actors"]["enemy"]["hp"] == 89


def test_generated_identity_skips_existing_actor_ids_without_aliasing_or_rng():
    state=start(combat.prepare(character(),[actor("player",abilities=(summon_power(),command_power())),
                actor("summon-1")],["player","summon-1"],[]))
    result,_=manifest(state)
    assert result["actors"]["summon-1"]["team"] == "foes" and result["actors"]["summon-1"]["hp"] == 95
    assert result["actors"]["summon-2"]["summon"]["owner_id"] == "player"
    assert result["summon_serial"] == 2


def test_owner_incapacitation_mid_action_advances_when_other_teams_remain():
    source=summon_power()
    backlash=replace(source,program=replace(source.program,effects=(Effect("DAMAGE",Formula(flat=1000),"ARCANE"),)))
    state=start(combat.prepare(character(),[actor("player",abilities=(backlash,command_power())),
        actor("enemy"),actor("ally",team="heroes",position=[0,3000,0])],["player","enemy","ally"],[]))
    result,receipt=manifest(state)
    assert result["actors"]["player"]["hp"] == 0 and result["active"] == "enemy"
    assert result["status"] == "active" and "summon-1" not in result["actors"]
    assert receipt["elapsed_seconds"] == 0
