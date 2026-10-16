"""Saved summon actions through the same owned approval transaction and transports."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from fastapi.testclient import TestClient
import pytest

from app.engine import Engine, EngineError
from app.server import create_app
from app.storage import Store
from .conftest import commit
from .test_combat_transactions import confirm
from .test_powers import Rolls, actor
from .test_server import rpc, tool
from .test_summons import command_power, summon_power, unit


def setup(engine):
    state=engine.create_sandbox("owner-a","Disposable summon test","summon-create-001")
    state=commit(engine,state,"prepare_combat",{"actors":[actor("player",abilities=(
        summon_power(unit("a"),unit("b")),command_power())),actor("enemy")],
        "order":["player","enemy"],"obstacles":[]})["campaign"]
    state=commit(engine,state,"resume")["campaign"]
    return commit(engine,state,"start_combat")["campaign"]


def placements():
    return {"actor_id":"player","ability_id":"manifest","placements":[
        {"template_id":"a","position":[1000,0,0]}, {"template_id":"b","position":[1500,500,0]}]}


def orders():
    return {"actor_id":"player","ability_id":"direct","orders":[
        {"summon_id":"summon-1","ability_id":"strike-a","target_ids":["enemy"]},
        {"summon_id":"summon-2","ability_id":"strike-b","target_ids":["enemy"]}]}


@pytest.fixture
def summoned_engine(tmp_path):
    store=Store(tmp_path/"summons.sqlite3")
    store.initialize()
    return Engine(store,enable_combat=True)


def test_pending_manifest_reopen_and_concurrent_command_preserve_one_roster_and_result(summoned_engine):
    engine=summoned_engine
    state=setup(engine)
    rolls=Rolls(1,12)
    engine.dice=rolls.dice
    pending=engine.propose_action("owner-a",state["id"],"manifest-once-001",state["version"],"manifest_summons",placements())
    assert engine.get_campaign("owner-a",state["id"]) == state and rolls.sides == []
    reopened=Engine(Store(engine.store.path),rolls.dice,enable_combat=True)
    result=confirm(reopened,pending)
    assert confirm(reopened,pending) == result
    state=result["campaign"]
    assert [row["id"] for row in state["summons"]] == ["summon-1","summon-2"]
    assert state["character"]["mp"] == 51 and state["encounter"]["summon_serial"] == 2
    pending=reopened.propose_action("owner-a",state["id"],"command-once-001",state["version"],"command_summons",orders())
    assert rolls.sides == []
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:confirm(reopened,pending),range(4)))
    assert all(row == results[0] for row in results)
    assert rolls.sides == [20,20]
    state=results[0]["campaign"]
    assert state["character"]["mp"] == 49 and state["enemies"][0]["hp"] == 92
    assert len(state["summons"]) == 2
    recovered=Engine(Store(engine.store.path),Rolls().dice,enable_combat=True)
    assert confirm(recovered,pending) == results[0]
    assert recovered.get_campaign("owner-a",state["id"]) == state
    assert recovered.audit("owner-a",state["id"])["integrity_valid"]


def test_invalid_order_owner_and_pause_cannot_partially_commit_or_roll(summoned_engine):
    engine=summoned_engine
    state=commit(engine,setup(engine),"manifest_summons",placements())["campaign"]
    engine.dice=Rolls().dice
    bad=orders()
    bad["orders"][-1]["target_ids"]=["unknown"]
    before=engine.audit("owner-a",state["id"])
    with pytest.raises(EngineError):
        engine.propose_action("owner-a",state["id"],"bad-command-001",state["version"],"command_summons",bad)
    assert engine.audit("owner-a",state["id"]) == before
    assert engine.get_campaign("owner-a",state["id"]) == state
    with pytest.raises(EngineError) as failure:
        engine.propose_action("owner-b",state["id"],"other-command-001",state["version"],"command_summons",orders())
    assert failure.value.status == 404
    state=commit(engine,state,"pause")["campaign"]
    with pytest.raises(EngineError) as failure:
        engine.propose_action("owner-a",state["id"],"paused-command-001",state["version"],"command_summons",orders())
    assert failure.value.status == 423 and len(state["summons"]) == 2


def test_new_summon_operations_are_absent_and_rejected_without_opt_in(engine,state):
    for name,payload in (("manifest_summons",placements()),("command_summons",orders())):
        assert name not in engine.dashboard("owner-a")["capabilities"]["operations"]
        with pytest.raises(EngineError,match="Unsupported"):
            engine.propose_action("owner-a",state["id"],"disabled-"+name,state["version"],name,payload)


def test_signed_http_mcp_use_actual_roster_with_scope_and_owner_isolation(tmp_path,config,verifier,tokens):
    app=create_app(tmp_path/"summons-web.sqlite3",config,verifier,enable_combat=True)
    with TestClient(app,base_url=config.resource_url.removesuffix("/mcp"),headers={"Authorization":"Bearer "+tokens()}) as web:
        state=web.post("/api/campaigns",json={"name":"Disposable summon HTTP fixture","action_id":"http-summons-create"}).json()["campaign"]
        def execute(kind,payload):
            nonlocal state
            pending=web.post(f"/api/campaigns/{state['id']}/proposals",json={"action_id":"summon-http-"+str(state["version"]),
                "expected_version":state["version"],"kind":kind,"payload":payload})
            assert pending.status_code == 200,pending.text
            pending=pending.json()
            token=pending["_meta"]["approval_token"]
            denied=rpc(web,"tools/call",{"name":"execute_confirmed_action","arguments":{
                "proposal_id":pending["proposal"]["id"],"approval_token":token}},headers={"Authorization":"Bearer "+tokens(scopes="campaign:read")})
            assert denied["isError"]
            result=tool(web,"execute_confirmed_action",{"proposal_id":pending["proposal"]["id"],"approval_token":token})
            assert not result.get("isError"),result
            state=result["structuredContent"]["campaign"]
            assert web.get(f"/api/campaigns/{state['id']}").json()["campaign"] == state
        execute("prepare_combat",{"actors":[actor("player",abilities=(summon_power(unit("a"),unit("b")),command_power())),
            actor("enemy")],"order":["player","enemy"],"obstacles":[]})
        execute("resume",{})
        execute("start_combat",{})
        execute("manifest_summons",placements())
        app.state.engine.dice=Rolls(12,12).dice
        execute("command_summons",orders())
        assert len(state["summons"]) == 2 and state["enemies"][0]["hp"] == 89
        assert web.get(f"/api/campaigns/{state['id']}",headers={"Authorization":"Bearer "+tokens(subject="user-b")}).status_code == 404
        assert app.state.engine.dashboard("unused-owner")["capabilities"]["full_rules_engine"] is False
