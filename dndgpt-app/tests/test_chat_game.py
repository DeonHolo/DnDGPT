import copy
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.chat_game import ChatGame, apply_changes, validate_changes
from app.engine import Engine, EngineError
from app.rules import ATTRIBUTES, derived
from app.storage import Store
from .conftest import commit
from .test_server import rpc, tool


@pytest.fixture
def game(engine):
    return ChatGame(engine)


@pytest.fixture
def draft(game):
    return game.create("owner-a", "Disposable first-play test", "chat-create-001", True)


def save(game, state, changes, action_id=None):
    return game.update("owner-a", state["id"], action_id or f"save-chat-{state['version']:04d}",
                       state["version"], "Test batch", changes)["campaign"]


def ready(game, engine, draft):
    state = save(game, draft, {"character": {"name": "Test Scribe", "class_name": "Door Scribe"}})
    state = commit(engine, state, "confirm_chat_character")["campaign"]
    return save(game, state, {"opening_preview": "A sealed door waits at the test gate."})


def adventure(game, engine, draft):
    return commit(engine, ready(game, engine, draft), "start_chat_adventure")["campaign"]


def test_new_game_is_owned_paused_and_idempotent(game, engine, draft):
    assert draft["mode"] == "chat" and draft["phase"] == "character_draft"
    assert draft["paused"] and draft["disposable"] and draft["fictional_time_seconds"] == 0
    assert game.create("owner-a", "Disposable first-play test", "chat-create-001", True) == draft
    assert engine.audit("owner-a", draft["id"])["event_count"] == 1
    with pytest.raises(EngineError, match="different arguments"):
        game.create("owner-a", "Different game", "chat-create-001", True)


def test_new_campaign_uses_dexterity_with_unchanged_calculations(draft):
    attributes = draft["character"]["attributes"]
    assert set(attributes) == set(ATTRIBUTES) == {"STR", "DEX", "INT", "CHA", "LCK"}
    legacy = {"AGI" if key == "DEX" else key: value for key, value in attributes.items()}
    assert derived(attributes) == derived(legacy)
    assert "DEX" not in legacy  # Compatibility calculation does not mutate input.


@pytest.mark.parametrize("recorded,incoming", [("DEX", "AGI"), ("AGI", "DEX")])
def test_attribute_alias_preserves_the_saved_key(draft, recorded, incoming):
    state = copy.deepcopy(draft)
    state["character"]["attributes"][recorded] = state["character"]["attributes"].pop("DEX")
    before = copy.deepcopy(state)
    changed = apply_changes(state, {"character": {"attributes": {incoming: 8}}})
    assert changed["character"]["attributes"][recorded] == 8
    assert incoming not in changed["character"]["attributes"]
    assert state == before


def test_conflicting_dexterity_keys_are_rejected():
    with pytest.raises(EngineError) as error:
        validate_changes({"character": {"attributes": {"AGI": 5, "DEX": 6}}})
    assert error.value.code == "invalid_chat_update"


def test_separate_confirmation_and_adventure_gates(game, engine, draft):
    for kind in ("resume", "start_chat_adventure", "confirm_chat_character"):
        with pytest.raises(EngineError):
            engine.propose_action("owner-a", draft["id"], "gate-test-" + kind, 1, kind, {})
    with pytest.raises(EngineError) as error:
        save(game, draft, {"fictional_time_seconds": 1})
    assert error.value.code == "adventure_not_authorized"
    state = ready(game, engine, draft)
    assert state["phase"] == "ready" and state["paused"]
    with pytest.raises(EngineError):
        save(game, state, {"character": {"hp": 1}})
    proposal = engine.propose_action("owner-a", state["id"], "start-chat-001", state["version"], "start_chat_adventure", {})
    assert engine.get_campaign("owner-a", state["id"])["paused"]
    with pytest.raises(EngineError) as error:
        engine.execute_confirmed_action("owner-a", proposal["proposal"]["id"], "forged")
    assert error.value.status == 403
    result = engine.execute_confirmed_action("owner-a", proposal["proposal"]["id"], proposal["_meta"]["approval_token"])
    assert not result["campaign"]["paused"] and result["campaign"]["phase"] == "adventure"


def test_all_seven_page_data_in_one_save_retry_and_reopen(game, engine, draft):
    state = adventure(game, engine, draft)
    changes = {"character": {"xp": 8, "hp": 50, "attributes": {"INT": 6}},
               "current_location": "Copper Gate", "fictional_time_seconds": 60,
               "world": {"weather": "Rain"}, "funds": {"saltmarks": 3}, "equipment": {"Main Hand": "test-key"},
               "upsert": {"abilities": [{"id": "ink-door", "name": "Ink Door", "activation": "ACTION", "status": "READY"}],
                          "conditions": [{"id": "wet", "name": "Wet"}],
                          "summons": [{"id": "moth", "name": "Paper Moth"}],
                          "inventory": [{"id": "test-key", "name": "Copper Key", "quantity": 1}],
                          "quest_log": [{"id": "gate-quest", "name": "Open the gate", "status": "active"}],
                          "world_log": [{"id": "arrival", "text": "Reached the copper gate."}],
                          "generation_ledger": [{"id": "seed-1", "mechanic": "write a door"}]}}
    args = ("owner-a", state["id"], "save-all-pages-001", state["version"], "Reached the gate", changes)
    result = game.update(*args)
    assert game.update(*args) == result
    reopened = Engine(Store(engine.store.path)); reopened.store.initialize()
    assert ChatGame(reopened).update(*args) == result
    saved = reopened.get_campaign("owner-a", state["id"])
    assert saved == result["campaign"] and saved["world_log"][0]["text"].startswith("Reached")
    assert saved["character"]["attributes"]["STR"] == 5
    assert saved["character"]["attributes"]["INT"] == 6
    assert saved["funds"] == {"saltmarks": 3}
    assert reopened.audit("owner-a", state["id"])["integrity_valid"]
    assert ChatGame(reopened).version("owner-a", state["id"], saved["version"])["campaign"] == saved


def test_no_writes_to_legacy_campaign(game, engine, state):
    before = copy.deepcopy(state)
    with pytest.raises(EngineError) as error:
        game.update("owner-a", state["id"], "legacy-write-001", 1, "Must fail", {"notes": "changed"})
    assert error.value.code == "chat_mode_required"
    assert engine.get_campaign("owner-a", state["id"]) == before
    with pytest.raises(EngineError):
        engine.propose_action("owner-a", state["id"], "legacy-start-001", 1, "start_chat_adventure", {})


@pytest.mark.parametrize("changes", [
    {"phase": "adventure"}, {"paused": False}, {"owner": "owner-b"}, {"version": 99},
    {"character": {"hp": True}}, {"character": {"hp": -1}}, {"character": {"hp": 9999}},
    {"character": {"attributes": {"STR": 0}}}, {"character": {"attributes": {"FAKE": 5}}},
    {"equipment": {"Fake": None}}, {"equipment": {"Main Hand": "missing"}},
    {"upsert": {"abilities": [{"id": "one", "status": False}]}},
    {"upsert": {"world_log": [{"text": "Missing id"}]}},
    {"upsert": {"inventory": [{"id": "same"}, {"id": "same"}]}},
    {"world": {"not_finite": float("nan")}}, {"world": {"oversized": 10**400}}, {"fictional_time_seconds": True},
    {"upsert": {"unexpected": []}}, {"replace": {"world_log": []}, "upsert": {"world_log": []}},
])
def test_bad_batch_is_atomic(game, engine, draft, changes):
    with pytest.raises(EngineError):
        save(game, draft, {"notes": "Must not be saved", **changes})
    assert engine.get_campaign("owner-a", draft["id"]) == draft
    assert engine.audit("owner-a", draft["id"])["event_count"] == 1


def test_concurrent_updates_stale_version_and_changed_retry(game, engine, draft):
    def write(index):
        try:
            return game.update("owner-a", draft["id"], f"concurrent-{index}", 1, "Concurrent", {"notes": str(index)})
        except EngineError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(write, range(8)))
    assert sum(type(result) is dict for result in results) == 1
    assert results.count("version_conflict") == 7
    winner = next(i for i, result in enumerate(results) if type(result) is dict)
    with pytest.raises(EngineError) as error:
        game.update("owner-a", draft["id"], f"concurrent-{winner}", 1, "Changed", {"notes": str(winner)})
    assert error.value.code == "idempotency_conflict"
    assert engine.audit("owner-a", draft["id"])["event_count"] == 2


def test_history_and_reviewed_correction_preserve_lifecycle(game, engine, draft):
    state = adventure(game, engine, draft)
    old = save(game, state, {"character": {"hp": 48}, "fictional_time_seconds": 30})
    mistaken = save(game, old, {"character": {"hp": 40}, "fictional_time_seconds": 60})
    paused = commit(engine, mistaken, "pause")["campaign"]
    with pytest.raises(EngineError):
        save(game, paused, {"character": {"hp": 48}})
    historical = game.version("owner-a", state["id"], old["version"])
    assert historical["historical"] and historical["current_version"] == paused["version"]
    payload = {"changes": {"character": {"hp": historical["campaign"]["character"]["hp"]}, "fictional_time_seconds": 30},
               "reason": "Correct duplicate damage and time"}
    fixed = commit(engine, paused, "correct_chat_state", payload)["campaign"]
    assert fixed["character"]["hp"] == 48 and fixed["fictional_time_seconds"] == 30
    assert fixed["paused"] and fixed["phase"] == "adventure"
    assert game.version("owner-a", state["id"], mistaken["version"])["campaign"] == mistaken
    assert engine.audit("owner-a", state["id"])["integrity_valid"]


def test_cross_owner_read_write_history_and_approval_are_hidden(game, engine, draft):
    for operation in (
        lambda: game.update("owner-b", draft["id"], "forbidden-001", 1, "Forbidden", {"notes": "no"}),
        lambda: game.version("owner-b", draft["id"], 1),
        lambda: engine.get_campaign("owner-b", draft["id"]),
    ):
        with pytest.raises(EngineError) as error:
            operation()
        assert error.value.status == 404


def test_legacy_engine_commands_cannot_bypass_chat_gates(game, engine, draft):
    state = adventure(game, engine, draft)
    with pytest.raises(EngineError) as error:
        engine.propose_action("owner-a", state["id"], "legacy-roll-001", state["version"], "roll_dice", {"sides": 20, "count": 1})
    assert error.value.code == "chat_gm_adjudicates"


def test_http_save_routes_scopes_and_recovery(web, tokens):
    created = web.post("/api/chat-games", json={"name": "HTTP disposable test", "action_id": "http-chat-create", "disposable": True})
    assert created.status_code == 200
    state = created.json()["campaign"]
    path = f"/api/campaigns/{state['id']}"
    body = {"action_id": "http-chat-save", "expected_version": 1, "summary": "Prepared class", "changes": {"character": {"class_name": "Gate Scribe"}}}
    saved = web.post(path + "/chat-updates", json=body)
    assert saved.status_code == 200 and saved.json()["campaign"]["version"] == 2
    assert web.post(path + "/chat-updates", json=body).json() == saved.json()
    assert web.get(path + "/versions/1").json()["campaign"]["version"] == 1
    assert web.get(path + "/versions/1", headers={"Authorization": "Bearer " + tokens("user-b")}).status_code == 404
    assert web.post(path + "/chat-updates", json=body, headers={"Authorization": "Bearer " + tokens(scopes="campaign:read")}).status_code == 403
    assert web.post(path + "/chat-updates", json={**body, "expected_version": True}).status_code == 422


def test_mcp_chat_tools_real_transport_scope_and_hidden_gate_token(web, tokens):
    definitions = {item["name"]: item for item in rpc(web, "tools/list")["tools"]}
    assert {"create_chat_game", "save_chat_update", "get_chat_version", "roll_game_random", "get_game_roll"} <= definitions.keys()
    created = tool(web, "create_chat_game", {"name": "MCP disposable test", "action_id": "mcp-chat-create", "disposable": True})
    state = created["structuredContent"]["campaign"]
    args = {"campaign_id": state["id"], "action_id": "mcp-chat-update", "expected_version": 1,
            "summary": "Prepare character", "changes": {"character": {"class_name": "Copper Scribe"}}}
    saved = tool(web, "save_chat_update", args)
    assert not saved.get("isError") and saved["structuredContent"]["campaign"]["version"] == 2
    assert tool(web, "save_chat_update", args) == saved
    readonly = rpc(web, "tools/call", {"name": "save_chat_update", "arguments": args},
                   headers={"Authorization": "Bearer " + tokens(scopes="campaign:read")})
    assert readonly["isError"] and "insufficient_scope" in readonly["_meta"]["mcp/www_authenticate"][0]
    forbidden = rpc(web, "tools/call", {"name": "get_chat_version", "arguments": {"campaign_id": state["id"], "version": 1}},
                    headers={"Authorization": "Bearer " + tokens("user-b")})
    assert forbidden["isError"] and forbidden["structuredContent"]["status"] == 404
    proposed = tool(web, "propose_action", {"campaign_id": state["id"], "action_id": "mcp-confirm-chat", "expected_version": 2,
                    "kind": "confirm_chat_character", "payload": {}})
    token = proposed["_meta"]["approval_token"]
    assert token not in str(proposed["structuredContent"]) and token not in str(proposed["content"])
    dashboard = tool(web, "render_dashboard", {"campaign_id": state["id"]})
    assert dashboard["_meta"]["approval"]["approval_token"] == token
    assert dashboard["structuredContent"]["campaign"]["paused"]
