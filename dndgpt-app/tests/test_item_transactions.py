from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from app.engine import Engine, EngineError, GEAR_OPERATIONS
from app.gear import Bonuses, Item, decode, encode
from app.server import create_app
from app.storage import Store
from .conftest import commit
from .test_item_runtime import loadout, potion, wand
from .test_powers import Rolls, actor
from .test_server import rpc, tool


@pytest.fixture
def inventory_engine(tmp_path):
    store = Store(tmp_path / "inventory.sqlite3")
    store.initialize()
    return Engine(store, enable_combat=True)


def prepare(engine, equipment):
    state = engine.create_sandbox("owner-a", "Disposable item sandbox", "item-create-001")
    return commit(engine, state, "prepare_loadout", {"loadout": encode(equipment)})["campaign"]


def setup_combat(engine, state):
    player = actor("player")
    for key in ("hp", "mp", "sta", "hp_max", "mp_max", "sta_max", "def", "movement_mm"):
        player[key] = state["character"][key]
    state = commit(engine, state, "prepare_combat", {"actors": [player, actor("enemy")],
        "order": ["player", "enemy"], "obstacles": []})["campaign"]
    state = commit(engine, state, "resume")["campaign"]
    return commit(engine, state, "start_combat")["campaign"]


def test_default_server_does_not_expose_inventory_mutations(engine, state):
    assert not set(GEAR_OPERATIONS) & set(engine.dashboard("owner-a")["capabilities"]["operations"])
    with pytest.raises(EngineError) as error:
        commit(engine, state, "prepare_loadout", {"loadout": encode(loadout(wand()))})
    assert error.value.code == "unsupported_action"


def test_equipping_and_attribute_advancement_keep_bonuses_without_refilling_resources(inventory_engine):
    ring = Item("ring", "Fixture stat ring", "COMMON", 10, "EQUIPPED", "Disposable advancement test",
        equip_modes=(("Ring 1",),), bonuses=Bonuses(hp_max=10, mp_max=10, sta_max=10, defense=1))
    engine = inventory_engine
    state = prepare(engine, loadout(ring))
    assert (state["character"]["hp"], state["character"]["hp_max"]) == (95, 105)
    state = commit(engine, state, "resume")["campaign"]
    state = commit(engine, state, "award_xp", {"amount": 100, "reward_id": "item-xp-fixture"})["campaign"]
    assert state["character"]["hp"] == 105 and state["character"]["mp"] == 65
    assert state["character"]["sta"] == 60
    state = commit(engine, state, "spend_attribute", {"attribute": "STR"})["campaign"]
    assert state["character"]["hp_max"] == 115 and state["character"]["hp"] == 105
    assert state["character"]["def"] == 11 and state["character"]["sta"] == 60
    assert state["character"]["carry_capacity_grams"] == 26000
    assert engine.audit("owner-a", state["id"])["integrity_valid"]


def test_outside_equipment_time_and_maximum_changes_do_not_heal(inventory_engine):
    ring = Item("ring", "Fixture vitality ring", "COMMON", 10, "EQUIPPED", "Disposable equipment test",
        equip_modes=(("Ring 1",),), bonuses=Bonuses(hp_max=10), equip_seconds=12)
    engine = inventory_engine
    state = commit(engine, prepare(engine, loadout(ring)), "resume")["campaign"]
    state = commit(engine, state, "unequip_item", {"actor_id": "player", "item_id": "ring"})["campaign"]
    assert state["character"]["hp_max"] == state["character"]["hp"] == 95
    state = commit(engine, state, "equip_item", {"actor_id": "player", "item_id": "ring", "slots": ["Ring 1"]})["campaign"]
    assert state["character"]["hp_max"] == 105 and state["character"]["hp"] == 95
    assert state["fictional_time_seconds"] == 24


def test_outside_consumable_draws_only_after_approval_and_consumes_last_object_once(inventory_engine):
    engine, rolls = inventory_engine, Rolls(4)
    engine.dice = rolls.dice
    state = commit(engine, prepare(engine, loadout(potion(quantity=1))), "resume")["campaign"]
    proposal = engine.propose_action("owner-a", state["id"], "drink-item-once", state["version"], "use_item", {
        "actor_id": "player", "item_id": "potion", "ability_id": "drink-potion", "target_ids": ["player"]})
    assert rolls.sides == [] and engine.get_campaign("owner-a", state["id"]) == state
    args = ("owner-a", proposal["proposal"]["id"], proposal["_meta"]["approval_token"])
    result = engine.execute_confirmed_action(*args)
    reopened = Engine(Store(engine.store.path), Rolls().dice, enable_combat=True)
    assert reopened.execute_confirmed_action(*args) == result
    assert result["campaign"]["loadout"]["items"] == []
    assert result["campaign"]["inventory"] == [] and result["campaign"]["fictional_time_seconds"] == 6
    assert rolls.sides == [6]
    assert reopened.audit("owner-a", state["id"])["integrity_valid"]


def test_combat_item_confirmation_is_concurrent_idempotent_and_updates_both_ledgers(inventory_engine):
    engine, rolls = inventory_engine, Rolls(12, 4)
    engine.dice = rolls.dice
    state = setup_combat(engine, prepare(engine, loadout(wand())))
    proposal = engine.propose_action("owner-a", state["id"], "fire-item-once", state["version"], "use_item", {
        "actor_id": "player", "item_id": "wand", "ability_id": "item-bolt", "target_ids": ["enemy"]})
    assert rolls.sides == []
    expenditure = proposal["proposal"]["combat_preview"]["ledger"][0]["item_expenditure"]
    assert expenditure["charges_before"] == 2 and expenditure["charges_remaining"] == 1
    def confirm(_):
        return engine.execute_confirmed_action("owner-a", proposal["proposal"]["id"], proposal["_meta"]["approval_token"])
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(confirm, range(3)))
    assert all(result == results[0] for result in results)
    result = results[0]["campaign"]
    assert decode(result["loadout"]).items[0].charges.current == 1
    assert result["inventory"][0]["charges"]["current"] == 1
    assert result["enemies"][0]["hp"] == result["encounter"]["actors"]["enemy"]["hp"] == 89
    assert rolls.sides == [20, 6] and engine.audit("owner-a", state["id"])["integrity_valid"]


def test_scenario_cannot_substitute_or_refill_owned_equipment(inventory_engine):
    engine = inventory_engine
    state = prepare(engine, loadout(wand()))
    forged = actor("player")
    forged["loadout"] = encode(loadout(wand(charges=replace(wand().charges, current=3))))
    with pytest.raises(EngineError, match="substitute"):
        commit(engine, state, "prepare_combat", {"actors": [forged, actor("enemy")],
            "order": ["player", "enemy"], "obstacles": []})
    assert engine.get_campaign("owner-a", state["id"]) == state


def test_paused_and_unowned_item_changes_are_rejected_before_rng(inventory_engine):
    engine, rolls = inventory_engine, Rolls()
    engine.dice = rolls.dice
    state = prepare(engine, loadout(potion()))
    with pytest.raises(EngineError) as paused:
        commit(engine, state, "use_item", {"actor_id": "player", "item_id": "potion", "ability_id": "drink-potion", "target_ids": ["player"]})
    assert paused.value.code == "paused"
    state = commit(engine, state, "resume")["campaign"]
    with pytest.raises(EngineError, match="not owned"):
        commit(engine, state, "retrieve_item", {"actor_id": "player", "item_id": "missing"})
    assert engine.get_campaign("owner-a", state["id"]) == state and rolls.sides == []


def test_signed_http_mcp_item_use_shares_owned_state_and_scope_checks(tmp_path, config, verifier, tokens):
    app = create_app(tmp_path / "items-web.sqlite3", config, verifier, enable_combat=True)
    with TestClient(app, base_url="https://dndgpt.example.test", headers={"Authorization": "Bearer " + tokens()}) as web:
        created = tool(web, "create_sandbox", {"name": "Disposable signed item test", "action_id": "signed-item-create"})
        state = created["structuredContent"]["campaign"]
        def transition(kind, payload):
            nonlocal state
            proposal = tool(web, "propose_action", {"campaign_id": state["id"], "action_id": "item-step-" + str(state["version"]),
                "expected_version": state["version"], "kind": kind, "payload": payload})
            assert not proposal.get("isError"), proposal
            result = tool(web, "execute_confirmed_action", {"proposal_id": proposal["structuredContent"]["proposal"]["id"],
                                                          "approval_token": proposal["_meta"]["approval_token"]})
            assert not result.get("isError"), result
            state = result["structuredContent"]["campaign"]
        transition("prepare_loadout", {"loadout": encode(loadout(potion(quantity=1)))})
        transition("resume", {})
        app.state.engine.dice = Rolls(2).dice
        denied = rpc(web, "tools/call", {"name": "propose_action", "arguments": {"campaign_id": state["id"],
            "action_id": "cannot-write-items", "expected_version": state["version"], "kind": "use_item", "payload": {
                "actor_id": "player", "item_id": "potion", "ability_id": "drink-potion", "target_ids": ["player"]}}},
            headers={"Authorization": "Bearer " + tokens(scopes="campaign:read")})
        assert denied["isError"]
        transition("use_item", {"actor_id": "player", "item_id": "potion", "ability_id": "drink-potion", "target_ids": ["player"]})
        assert web.get(f"/api/campaigns/{state['id']}").json()["campaign"] == state
        assert state["inventory"] == [] and state["fictional_time_seconds"] == 6
        assert web.get(f"/api/campaigns/{state['id']}", headers={"Authorization": "Bearer " + tokens(subject="user-b")}).status_code == 404
