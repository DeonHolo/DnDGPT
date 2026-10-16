from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from fastapi.testclient import TestClient
import pytest

from app.engine import COMBAT_OPERATIONS, Engine, EngineError
from app.server import create_app
from app.storage import Store
from .conftest import commit
from .test_powers import Rolls, actor, power
from .test_server import rpc, tool


@pytest.fixture
def combat_engine(tmp_path):
    store = Store(tmp_path / "combat.sqlite3")
    store.initialize()
    return Engine(store, enable_combat=True)


def setup(engine):
    state = engine.create_sandbox("owner-a", "Disposable power runtime test", "combat-create-001")
    state = commit(engine, state, "prepare_combat", {"actors": [actor("player", abilities=(power(),)),
                   actor("enemy")], "order": ["player", "enemy"], "obstacles": []})["campaign"]
    state = commit(engine, state, "resume")["campaign"]
    return commit(engine, state, "start_combat")["campaign"]


def propose_bolt(engine, state, *, action_id="cast-action-001", **changes):
    return engine.propose_action("owner-a", state["id"], action_id, state["version"], "use_ability",
        {"actor_id": "player", "ability_id": "bolt", "target_ids": ["enemy"], **changes})


def confirm(engine, proposal, owner="owner-a"):
    return engine.execute_confirmed_action(owner, proposal["proposal"]["id"], proposal["_meta"]["approval_token"])


def test_combat_is_disabled_in_default_engine_and_capabilities(engine, state):
    assert not set(COMBAT_OPERATIONS) & set(engine.dashboard("owner-a")["capabilities"]["operations"])
    assert engine.dashboard("owner-a")["capabilities"]["sandbox_combat"] is False
    with pytest.raises(EngineError, match="Unsupported"):
        engine.propose_action("owner-a", state["id"], "disabled-cast-001", state["version"], "start_combat", {})
    assert engine.get_campaign("owner-a", state["id"]) == state


def test_proposal_has_no_rng_and_concurrent_confirmation_spends_once(combat_engine):
    engine, rolls = combat_engine, Rolls(12, 4)
    engine.dice = rolls.dice
    state = setup(engine)
    before = deepcopy(state)
    proposal = propose_bolt(engine, state)
    assert rolls.sides == []
    assert proposal["proposal"]["combat_preview"]["preview"] is True
    assert engine.get_campaign("owner-a", state["id"]) == before
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: confirm(engine, proposal), range(4)))
    assert all(result == results[0] for result in results)
    result = results[0]
    assert rolls.sides == [20, 6]
    assert result["campaign"]["character"]["mp"] == before["character"]["mp"] - 3
    assert result["campaign"]["character"]["sta"] == before["character"]["sta"] - 2
    assert result["campaign"]["encounter"]["actors"]["enemy"]["hp"] == 89
    assert result["campaign"]["version"] == state["version"] + 1
    assert engine.audit("owner-a", state["id"])["integrity_valid"] is True


def test_owner_and_approval_token_are_checked_before_power_rng(combat_engine):
    engine, rolls = combat_engine, Rolls()
    engine.dice = rolls.dice
    state = setup(engine)
    proposal = propose_bolt(engine, state)
    for owner, token, status in (("owner-b", proposal["_meta"]["approval_token"], 404),
                                 ("owner-a", "wrong-token", 403)):
        with pytest.raises(EngineError) as error:
            engine.execute_confirmed_action(owner, proposal["proposal"]["id"], token)
        assert error.value.status == status
    assert rolls.sides == [] and engine.get_campaign("owner-a", state["id"]) == state


def test_reopen_pending_confirmation_and_committed_retry_preserves_result(combat_engine):
    engine = combat_engine
    state = setup(engine)
    proposal = propose_bolt(engine, state)
    rolls = Rolls(1)
    reopened = Engine(Store(engine.store.path), rolls.dice, enable_combat=True)
    result = confirm(reopened, proposal)
    again = Engine(Store(engine.store.path), Rolls().dice, enable_combat=True)
    assert confirm(again, proposal) == result
    assert again.get_campaign("owner-a", state["id"]) == result["campaign"]
    assert rolls.sides == [20]
    assert again.audit("owner-a", state["id"])["integrity_valid"] is True


def test_paused_frozen_stale_and_illegal_actions_leave_no_partial_cost(combat_engine):
    engine, rolls = combat_engine, Rolls()
    engine.dice = rolls.dice
    state = setup(engine)
    proposal = propose_bolt(engine, state)
    paused = commit(engine, state, "pause")["campaign"]
    with pytest.raises(EngineError) as stale:
        confirm(engine, proposal)
    assert stale.value.code == "version_conflict"
    with pytest.raises(EngineError) as error:
        engine.propose_action("owner-a", paused["id"], "paused-cast-001", paused["version"], "use_ability",
            {"actor_id": "player", "ability_id": "bolt", "target_ids": ["enemy"]})
    assert error.value.code == "paused"
    state = commit(engine, paused, "resume")["campaign"]
    with pytest.raises(EngineError):
        propose_bolt(engine, state, action_id="illegal-target-001", target_ids=["missing"])
    assert engine.get_campaign("owner-a", state["id"]) == state and rolls.sides == []


def test_scenario_is_fixed_before_start_and_unrelated_mutations_cannot_desync_resources(combat_engine):
    engine = combat_engine
    state = setup(engine)
    for kind, payload in (("prepare_combat", {"actors": [], "order": [], "obstacles": []}),
                          ("spend_mp", {"cost": 1}), ("award_xp", {"amount": 100, "reward_id": "reward-test-001"})):
        with pytest.raises(EngineError):
            engine.propose_action("owner-a", state["id"], "cannot-rewrite-" + kind, state["version"], kind, payload)
    assert engine.get_campaign("owner-a", state["id"]) == state


def test_full_round_records_time_once_and_pause_blocks_movement(combat_engine):
    engine = combat_engine
    state = setup(engine)
    state = commit(engine, state, "end_turn", {"actor_id": "player"})["campaign"]
    assert state["fictional_time_seconds"] == 0
    state = commit(engine, state, "end_turn", {"actor_id": "enemy"})["campaign"]
    assert state["fictional_time_seconds"] == 6
    assert state["encounter"]["round"] == 2
    state = commit(engine, state, "pause")["campaign"]
    with pytest.raises(EngineError) as error:
        commit(engine, state, "combat_move", {"actor_id": "player", "path": [[1000, 0, 0]]})
    assert error.value.code == "paused"
    assert engine.get_campaign("owner-a", state["id"])["fictional_time_seconds"] == 6


@pytest.mark.parametrize("transport", ["http", "mcp"])
def test_opted_in_signed_transports_share_costs_and_owner_isolation(tmp_path, config, verifier, tokens, transport):
    app = create_app(tmp_path / "combat-web.sqlite3", config, verifier, enable_combat=True)
    with TestClient(app, base_url=config.resource_url.removesuffix("/mcp"),
                    headers={"Authorization": "Bearer " + tokens()}) as web:
        assert web.get("/api/health").json()["sandbox_combat_enabled"] is True
        response = web.post("/api/campaigns", json={"name": "Disposable HTTP combat", "action_id": "http-combat-create"})
        assert response.status_code == 200, response.text
        state = response.json()["campaign"]
        def execute(kind, payload):
            nonlocal state
            response = web.post(f"/api/campaigns/{state['id']}/proposals", json={"action_id": "http-action-" + str(state["version"]),
                "expected_version": state["version"], "kind": kind, "payload": payload})
            assert response.status_code == 200, response.text
            proposal = response.json()
            response = web.post(f"/api/proposals/{proposal['proposal']['id']}/confirm",
                json={"approval_token": proposal["_meta"]["approval_token"]})
            assert response.status_code == 200, response.text
            state = response.json()["campaign"]
            return response.json()
        execute("prepare_combat", {"actors": [actor("player", abilities=(power(),)), actor("enemy")],
                                  "order": ["player", "enemy"], "obstacles": []})
        execute("resume", {})
        execute("start_combat", {})
        # The app owns the very same engine used by HTTP and MCP.
        app.state.engine.dice = Rolls(1).dice
        payload = {"actor_id": "player", "ability_id": "bolt", "target_ids": ["enemy"]}
        if transport == "http":
            execute("use_ability", payload)
        else:
            proposal = tool(web, "propose_action", {"campaign_id": state["id"], "action_id": "mcp-cast-action-001",
                            "expected_version": state["version"], "kind": "use_ability", "payload": payload})
            assert not proposal.get("isError"), proposal
            token = proposal["_meta"]["approval_token"]
            assert token not in str(proposal["structuredContent"])
            denied = rpc(web, "tools/call", {"name": "execute_confirmed_action", "arguments": {
                "proposal_id": proposal["structuredContent"]["proposal"]["id"], "approval_token": token}},
                headers={"Authorization": "Bearer " + tokens(scopes="campaign:read")})
            assert denied["isError"]
            result = tool(web, "execute_confirmed_action", {"proposal_id": proposal["structuredContent"]["proposal"]["id"],
                                                           "approval_token": token})
            assert not result.get("isError"), result
            state = result["structuredContent"]["campaign"]
            assert web.get(f"/api/campaigns/{state['id']}").json()["campaign"] == state
        assert state["character"]["mp"] == 52 and state["character"]["sta"] == 58
        assert web.get(f"/api/campaigns/{state['id']}", headers={"Authorization": "Bearer " + tokens(subject="user-b")}).status_code == 404


@pytest.mark.parametrize("flag", ["true", 1, None])
def test_combat_flag_requires_an_explicit_boolean(tmp_path, flag):
    with pytest.raises(ValueError, match="boolean"):
        Engine(Store(tmp_path / "invalid-flag.sqlite3"), enable_combat=flag)
