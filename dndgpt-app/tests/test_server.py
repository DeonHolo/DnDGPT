import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import AuthConfig
from app.server import create_app
from app.version import APP_VERSION


def rpc(web, method, params=None, *, headers=None):
    response = web.post("/mcp", json={"jsonrpc": "2.0", "id": 1,
                        "method": method, "params": params or {}},
                        headers={"Accept": "application/json, text/event-stream", **(headers or {})})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "error" not in body, body
    return body["result"]


def tool(web, name, arguments=None):
    return rpc(web, "tools/call", {"name": name, "arguments": arguments or {}})


def new_sandbox(web, name="HTTP test"):
    response = web.post("/api/campaigns", json={"name": name, "action_id": "create-http-001"})
    assert response.status_code == 200, response.text
    return response.json()["campaign"]


def test_health_and_default_auth_fail_closed(tmp_path):
    app = create_app(tmp_path / "locked.sqlite3", AuthConfig())
    with TestClient(app) as client:
        health = client.get("/api/health").json()
        assert health["version"] == APP_VERSION and health["rules_version"] == "1.0"
        assert health["chatgpt_integration"] is False
        assert client.get("/api/campaigns").status_code == 503
        assert client.post("/mcp", json={}).status_code == 503
        assert client.get("/").status_code == 200
        assert app.state.engine.list_campaigns("any-user") == []


def test_oauth_challenge_discovery_and_reject_bad_tokens(web, tokens):
    for path in ("/api/campaigns", "/mcp"):
        response = web.get(path, headers={"Authorization": ""})
        assert response.status_code == 401
        assert "resource_metadata=" in response.headers["WWW-Authenticate"]
    discovery = web.get("/.well-known/oauth-protected-resource/mcp").json()
    assert discovery["resource"] == "https://dndgpt.example.test/mcp"
    assert set(discovery["scopes_supported"]) == {"campaign:read", "campaign:write"}
    for token in [tokens(exp=int(time.time()) - 60), tokens(iss="https://wrong.example.test"),
                  tokens(aud="https://wrong.example.test"), "malformed.token"]:
        assert web.get("/api/campaigns", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_owner_comes_from_subject_and_read_scope_cannot_mutate(web, tokens):
    state = new_sandbox(web)
    response = web.get("/api/campaigns/" + state["id"],
                       headers={"Authorization": "Bearer " + tokens(subject="user-b")})
    assert response.status_code == 404
    assert web.get("/api/campaigns", headers={"Authorization": "Bearer " + tokens(subject="user-b")}).json()["campaigns"] == []
    readonly = {"Authorization": "Bearer " + tokens(scopes="campaign:read")}
    assert web.get("/api/campaigns/" + state["id"], headers=readonly).status_code == 200
    assert web.post("/api/campaigns", json={"name": "Blocked", "action_id": "create-read-001"}, headers=readonly).status_code == 403
    # A refreshed token may change client ID without changing campaign ownership.
    refreshed = {"Authorization": "Bearer " + tokens(azp="another-registered-client")}
    assert web.get("/api/campaigns/" + state["id"], headers=refreshed).status_code == 200


def test_http_proposal_confirm_and_legacy_bypass_closed(web):
    state = new_sandbox(web)
    before = web.get("/api/campaigns/" + state["id"]).json()
    proposal = web.post("/api/campaigns/" + state["id"] + "/proposals",
        json={"action_id": "resume-http-001", "expected_version": 1, "kind": "resume", "payload": {}}).json()
    assert web.get("/api/campaigns/" + state["id"]).json() == before
    path = "/api/proposals/" + proposal["proposal"]["id"] + "/confirm"
    assert web.post(path, json={"approval_token": "forged"}).status_code == 403
    arguments = {"approval_token": proposal["_meta"]["approval_token"]}
    response = web.post(path, json=arguments)
    assert response.status_code == 200
    assert web.post(path, json=arguments).json() == response.json()
    assert response.json()["campaign"]["paused"] is False
    assert web.post("/api/campaigns/" + state["id"] + "/commands", json={}).status_code == 404
    assert web.get("/api/campaigns/" + state["id"] + "/events").json()["integrity_valid"]


def test_mcp_initialization_tools_and_ui_resource(web):
    result = rpc(web, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                     "clientInfo": {"name": "DnDGPT-test", "version": "1.0.0"}})
    assert result["serverInfo"]["version"] == APP_VERSION
    definitions = rpc(web, "tools/list")["tools"]
    by_name = {item["name"]: item for item in definitions}
    assert {"get_campaign", "propose_action", "execute_confirmed_action", "roll_dice", "audit", "render_dashboard"} <= set(by_name)
    render = by_name["render_dashboard"]
    assert render["_meta"]["ui"]["resourceUri"].startswith("ui://dndgpt/")
    assert render["_meta"]["openai/ui"]["entrypoints"] == [{"type": "thread"}]
    assert not tool(web, "render_dashboard", {}).get("isError")
    assert by_name["execute_confirmed_action"]["_meta"]["ui"]["visibility"] == ["app"]
    for name, item in by_name.items():
        assert item["securitySchemes"][0]["type"] == "oauth2"
        if name != "render_dashboard":
            assert "resourceUri" not in item["_meta"]["ui"]
    resource = rpc(web, "resources/read", {"uri": render["_meta"]["ui"]["resourceUri"]})["contents"][0]
    assert resource["mimeType"] == "text/html;profile=mcp-app"
    assert resource["_meta"]["ui"]["csp"] == {"connectDomains": [], "resourceDomains": []}
    assert resource["_meta"]["openai/ui"] == {
        "availableDisplayModes": ["inline", "fullscreen"], "preferredDisplayMode": "fullscreen"}
    assert resource["text"].count('data-panel="') == 7
    assert "ui/message" in resource["text"]


def test_mcp_approval_metadata_hidden_and_commit_shared_with_http(web):
    created = tool(web, "create_sandbox", {"name": "MCP test", "action_id": "create-mcp-001"})
    assert not created.get("isError")
    state = created["structuredContent"]["campaign"]
    proposal = tool(web, "propose_action", {"campaign_id": state["id"], "action_id": "resume-mcp-001",
                  "expected_version": 1, "kind": "resume", "payload": {}})
    token = proposal["_meta"]["approval_token"]
    assert token not in json.dumps(proposal["structuredContent"])
    assert token not in json.dumps(proposal["content"])
    assert web.get("/api/campaigns/" + state["id"]).json()["campaign"]["version"] == 1
    view = tool(web, "get_campaign", {"campaign_id": state["id"]})
    assert view["_meta"]["approval"]["approval_token"] == token
    result = tool(web, "execute_confirmed_action", {"proposal_id": proposal["structuredContent"]["proposal"]["id"],
                                                  "approval_token": token})
    assert not result.get("isError"), result
    assert web.get("/api/campaigns/" + state["id"]).json()["campaign"] == result["structuredContent"]["campaign"]
    assert result["structuredContent"]["campaign"]["version"] == 2


def test_mcp_missing_scope_and_cross_owner_denied(web, tokens):
    state = new_sandbox(web)
    readonly = tokens(scopes="campaign:read")
    result = rpc(web, "tools/call", {"name": "create_sandbox",
                  "arguments": {"name": "Forbidden", "action_id": "create-bad-001"}},
                  headers={"Authorization": "Bearer " + readonly})
    assert result["isError"]
    assert "insufficient_scope" in result["_meta"]["mcp/www_authenticate"][0]
    result = rpc(web, "tools/call", {"name": "get_campaign", "arguments": {"campaign_id": state["id"]}},
                 headers={"Authorization": "Bearer " + tokens(subject="user-b")})
    assert result["isError"] and result["structuredContent"]["status"] == 404


def test_origin_attack_rejected_by_mcp_transport(web):
    response = web.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                        headers={"Accept": "application/json, text/event-stream",
                                 "Origin": "https://untrusted.example.test"})
    assert response.status_code in (400, 403, 421)


@pytest.mark.parametrize("document,filename", [("rulebook", "rulebook-v1.0.txt"),
                                               ("hardener", "rule-hardener.txt")])
def test_hosted_rules_are_complete_paginated_read_only_text(web, tokens, document, filename):
    import hashlib
    state = new_sandbox(web)
    readonly = {"Authorization": "Bearer " + tokens(scopes="campaign:read")}
    before = web.get("/api/campaigns/" + state["id"]).json()
    data = (Path(__file__).resolve().parents[1] / "rules" / filename).read_bytes()
    offset, parts = 0, []
    while True:
        result = rpc(web, "tools/call", {"name": "read_rules",
                     "arguments": {"document": document, "offset": offset}}, headers=readonly)
        assert not result.get("isError"), result
        page = result["structuredContent"]
        assert page["offset"] == offset and len(page["content"]) <= 8000
        shown = result["content"][0]["text"]
        assert shown.index('"next_offset"') < shown.index('"content"')
        assert len(shown) < 10000
        assert page["source_sha256"] == hashlib.sha256(data).hexdigest()
        assert page["total_characters"] == len(data.decode("utf-8"))
        parts.append(page["content"])
        if page["next_offset"] is None:
            break
        assert page["next_offset"] == offset + len(page["content"])
        assert page["next_offset"] > offset
        offset = page["next_offset"]
    assert "".join(parts) == data.decode("utf-8")
    assert web.get("/api/campaigns/" + state["id"]).json() == before
    definition = next(t for t in rpc(web, "tools/list")["tools"] if t["name"] == "read_rules")
    assert definition["annotations"]["readOnlyHint"] is True
    assert definition["securitySchemes"][0]["scopes"] == ["campaign:read"]


@pytest.mark.parametrize("arguments", [{"offset": -1}, {"offset": 10**9},
                                       {"document": "../../.env"}])
def test_hosted_rules_reject_invalid_pages_and_arbitrary_files(web, arguments):
    assert tool(web, "read_rules", arguments)["isError"] is True

