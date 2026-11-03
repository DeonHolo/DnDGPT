"""Mode-neutral entry and UI-resource delivery, using real authenticated MCP."""
import pytest

from .test_server import rpc, tool


MODES = ("dnd-2024", "age-of-convergence", "sovereign-system")


@pytest.mark.parametrize("name,args", [
    ("render_dashboard", {}),
    ("read_rules", {"document": "hardener"}),
    ("list_campaigns", {}),
    ("create_chat_game", {"name": "Unchosen mode", "action_id": "no-mode-create"}),
])
def test_unspecified_entry_introduces_three_modes_without_reading_or_creating(web, monkeypatch, name, args):
    # Existing saves must not make the unspecified invocation choose their mode.
    saved = tool(web, "create_chat_game", {"name": "Existing sovereign", "action_id": "existing-mode",
                                           "disposable": True, "game_id": MODES[2]})["structuredContent"]["campaign"]
    before = web.get("/api/campaigns").json()

    def unexpected(*args, **kwargs):
        raise AssertionError("Mode selection must precede rule loading, creation and rolls")

    monkeypatch.setattr("app.chat_game.ChatGame.create", unexpected)
    monkeypatch.setattr("app.mcp_server.rules_page", unexpected)
    monkeypatch.setattr("app.game_random.GameRandom.roll", unexpected)
    result = tool(web, name, args)
    assert not result.get("isError"), result
    data = result["structuredContent"]
    assert data["mode_selection_required"] is True and data["game_id"] is None
    assert data["campaign"] is None and data["campaigns"] == []
    assert tuple(mode["id"] for mode in data["game_modes"]) == MODES
    assert all(mode["name"] and mode["introduction"] for mode in data["game_modes"])
    assert "content" not in data and "source_sha256" not in data
    assert web.get("/api/campaigns").json() == before
    current = tool(web, "get_campaign", {"campaign_id": saved["id"]})["structuredContent"]["campaign"]
    assert current == saved


@pytest.mark.parametrize("mode", MODES)
def test_named_mode_and_targeted_campaign_skip_picker_and_keep_books_isolated(web, mode):
    created = tool(web, "create_chat_game", {"name": "Explicit mode", "action_id": "chosen-mode",
                                             "disposable": True, "game_id": mode})
    assert not created.get("isError"), created
    state = created["structuredContent"]["campaign"]
    assert state["game_id"] == mode
    for args in ({"game_id": mode}, {"campaign_id": state["id"]}):
        data = tool(web, "render_dashboard", args)["structuredContent"]
        assert data["mode_selection_required"] is False and data["game_id"] == mode
        assert all(c["game_id"] == mode for c in data["campaigns"])
        rules = tool(web, "read_rules", {"document": "hardener", **args})["structuredContent"]
        assert rules["game_id"] == mode and rules["source_sha256"]
    assert tool(web, "get_campaign", {"campaign_id": state["id"]})["structuredContent"]["campaign"] == state


def test_first_entry_dashboard_bindings_and_instructions_do_not_reopen_every_turn(web):
    initialized = rpc(web, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                          "clientInfo": {"name": "Entry check", "version": "1"}})
    assert "FIRST call render_dashboard" in initialized["instructions"]
    assert "ask which they want before reading a book" in initialized["instructions"]
    definitions = {t["name"]: t for t in rpc(web, "tools/list")["tools"]}
    entry = definitions["render_dashboard"]["_meta"]
    assert entry["ui"]["resourceUri"] and entry["openai/outputTemplate"]
    for name in ("read_rules", "create_chat_game", "list_campaigns", "get_campaign",
                 "save_chat_update", "roll_game_random", "lookup_dnd_reference"):
        meta = definitions[name]["_meta"]
        assert "resourceUri" not in meta["ui"], name
        assert "openai/outputTemplate" not in meta, name
        assert "openai/ui" not in meta, name
    assert "game_id" not in definitions["create_chat_game"]["inputSchema"]["required"]
    assert web.get("/api/health").json()["default_game_id"] is None


def test_open_once_then_reads_and_saves_deliver_updated_state_without_mounting(web):
    definitions = {t["name"]: t for t in rpc(web, "tools/list")["tools"]}
    opened = []

    def call(name, args):
        result = tool(web, name, args)
        assert not result.get("isError"), result
        meta = definitions[name]["_meta"]
        if meta.get("ui", {}).get("resourceUri") or meta.get("openai/outputTemplate"):
            opened.append(name)
        return result

    call("render_dashboard", {})
    state = call("create_chat_game", {"name": "Open once", "action_id": "open-once-create",
                                       "game_id": "age-of-convergence", "disposable": True})["structuredContent"]["campaign"]
    for turn in range(2):
        call("read_rules", {"document": "index", "campaign_id": state["id"]})
        call("get_campaign", {"campaign_id": state["id"]})
        updated = call("save_chat_update", {"campaign_id": state["id"], "action_id": "open-once-"+str(turn),
                     "expected_version": state["version"], "summary": "Draft view update",
                     "changes": {"character": {"name": "Updated hero "+str(turn)}}})
        state = updated["structuredContent"]["campaign"]
        assert state["character"]["name"] == "Updated hero "+str(turn)
        visible = call("get_campaign", {"campaign_id": state["id"], "view": "turn"})
        assert visible["_meta"]["campaign_snapshot"]["version"] == state["version"]
        assert visible["_meta"]["campaign_snapshot"]["character"]["name"] == state["character"]["name"]
    assert opened == ["render_dashboard"]
