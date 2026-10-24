import sqlite3

from fastapi.testclient import TestClient

from tests.pip_probe import create_probe


def test_probe_protocol_is_static_read_only_and_has_ui_metadata(monkeypatch):
    def no_database(*args, **kwargs):
        raise AssertionError("The public UI probe must never open a database")
    monkeypatch.setattr(sqlite3, "connect", no_database)
    with TestClient(create_probe(), base_url="http://127.0.0.1:8767",
                    headers={"Accept": "application/json, text/event-stream"}) as client:
        def rpc(method, params=None):
            response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1,
                                                  "method": method, "params": params or {}})
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            return response.json()["result"]
        rpc("initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                           "clientInfo": {"name": "probe-test", "version": "1"}})
        tools = rpc("tools/list")["tools"]
        assert {tool["name"] for tool in tools} == {"render_pip_probe", "get_probe_status"}
        assert all(tool["annotations"]["readOnlyHint"] for tool in tools)
        assert all(tool["securitySchemes"] == [{"type": "noauth"}] for tool in tools)
        rendered = rpc("tools/call", {"name": "render_pip_probe", "arguments": {}})
        assert rendered["structuredContent"] == {"dummy_hp": 20, "campaign_access": False}
        uri = next(tool for tool in tools if tool["name"] == "render_pip_probe")["_meta"]["ui"]["resourceUri"]
        resource = rpc("resources/read", {"uri": uri})["contents"][0]
        assert resource["mimeType"] == "text/html;profile=mcp-app"
        assert resource["_meta"]["ui"]["csp"]["connectDomains"] == []
        assert "Test PiP" in resource["text"]
        assert resource["text"].count('data-panel="') == 8
        assert "SHARED_COMPANION_CSS" not in resource["text"]
        assert "SHARED_COMPANION_NAV" not in resource["text"]
        assert 'aria-label="Companion sections"' in resource["text"]
        assert "function selectCompanionPage" in resource["text"]
        assert "execute_confirmed_action" not in resource["text"]
        status = rpc("tools/call", {"name": "get_probe_status", "arguments": {}})
        assert status["structuredContent"]["campaign_access"] is False
        assert status["structuredContent"]["source_utc"]
        assert client.get("/mcp").status_code == 405  # JSON transport needs no SSE tunnel.


def test_probe_rejects_unconfigured_hosts_and_has_no_game_routes():
    with TestClient(create_probe("https://probe.example.test"), base_url="https://probe.example.test") as client:
        assert client.get("/health").json()["campaign_access"] is False
        assert client.post("/commands", json={}).status_code == 404
        response = client.post("/mcp", headers={"Host": "attacker.example.test"}, json={})
        assert response.status_code == 421
