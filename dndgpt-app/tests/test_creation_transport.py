"""Authenticated development adapters; signatures verified with disposable keys."""
import json

import pytest
from fastapi.testclient import TestClient

from app.server import create_app
from tests.test_server import rpc, tool


@pytest.fixture
def creation_web(tmp_path, config, verifier, tokens):
    app = create_app(tmp_path / "creation-web.sqlite3", config, verifier, enable_creation_drafts=True)
    with TestClient(app, base_url="https://dndgpt.example.test",
                    headers={"Authorization": "Bearer " + tokens()}) as client:
        yield client


def proposal(web):
    response = web.post("/api/creation-drafts", json={
        "world_preview": "Neutral transport fixture", "action_id": "transport-start-001"})
    assert response.status_code == 200, response.text
    return response.json()


def confirm(web, pending):
    return tool(web, "confirm_creation_transition", {
        "proposal_id": pending["proposal"]["id"],
        "approval_token": pending["_meta"]["creation_approval"]["approval_token"]})


def test_creation_adapter_is_absent_from_default_app(web):
    assert web.get("/api/creation-drafts").status_code == 404
    definitions = rpc(web, "tools/list")["tools"]
    assert not any("creation" in entry["name"] for entry in definitions)
    health = web.get("/api/health").json()
    assert health["creation_drafts_enabled"] is False and health["character_creation"] is False


def test_http_preview_mcp_approval_and_recovery_share_one_draft(creation_web):
    web = creation_web
    pending = proposal(web)
    assert web.get("/api/creation-drafts").json()["drafts"] == []
    committed = confirm(web, pending)
    assert not committed.get("isError"), committed
    draft = committed["structuredContent"]["draft"]
    assert web.get("/api/creation-drafts/" + draft["id"]).json()["draft"] == draft
    assert confirm(web, pending)["structuredContent"] == committed["structuredContent"]
    transition = tool(web, "propose_creation_transition", {"draft_id": draft["id"],
        "action_id": "transport-luck-001", "expected_version": 1,
        "kind": "allocate_luck", "payload": {"points": 2}})
    hidden = transition["_meta"]["creation_approval"]["approval_token"]
    assert hidden not in json.dumps(transition["content"])
    assert hidden not in json.dumps(transition["structuredContent"])
    read = tool(web, "get_creation_draft", {"draft_id": draft["id"]})
    assert read["_meta"]["creation_approvals"][0]["approval_token"] == hidden
    assert read["structuredContent"]["draft"]["version"] == 1
    result = confirm(web, {**transition["structuredContent"], "_meta": transition["_meta"]})
    assert not result.get("isError") and result["structuredContent"]["draft"]["version"] == 2
    audit = web.get("/api/creation-drafts/" + draft["id"] + "/events").json()
    assert audit["integrity_valid"] and len(audit["events"]) == 2
    assert web.get("/api/campaigns").json()["campaigns"] == []
    # No new HTTP commit bypass: approval is exposed only as an app tool.
    assert web.post("/api/creation-proposals/" + pending["proposal"]["id"] + "/confirm", json={}).status_code == 404
    definitions = {entry["name"]: entry for entry in rpc(web, "tools/list")["tools"]}
    approval = definitions["confirm_creation_transition"]
    assert approval["_meta"]["ui"]["visibility"] == ["app"]
    assert set(approval["securitySchemes"][0]["scopes"]) == {"campaign:read", "campaign:write"}
    assert web.get("/api/health").json()["character_creation"] is False


def test_transport_owner_and_scope_boundaries(creation_web, tokens):
    web = creation_web
    pending = proposal(web)
    draft = confirm(web, pending)["structuredContent"]["draft"]
    other = {"Authorization": "Bearer " + tokens(subject="user-b")}
    readonly = {"Authorization": "Bearer " + tokens(scopes="campaign:read")}
    path = "/api/creation-drafts/" + draft["id"]
    assert web.get(path, headers=other).status_code == 404
    assert web.get(path + "/events", headers=other).status_code == 404
    assert web.get("/api/creation-drafts", headers=other).json()["drafts"] == []
    assert web.post(path + "/proposals", headers=other, json={"action_id": "other-luck-001",
        "expected_version": 1, "kind": "allocate_luck", "payload": {"points": 1}}).status_code == 404
    assert web.get(path, headers=readonly).status_code == 200
    assert web.post("/api/creation-drafts", headers=readonly, json={
        "world_preview": "Blocked", "action_id": "readonly-start-001"}).status_code == 403
    assert web.get("/api/creation-drafts", headers={"Authorization": ""}).status_code == 401
    args = {"name": "confirm_creation_transition", "arguments": {
        "proposal_id": pending["proposal"]["id"],
        "approval_token": pending["_meta"]["creation_approval"]["approval_token"]}}
    denied = rpc(web, "tools/call", args, headers=other)
    assert denied["isError"] and denied["structuredContent"]["status"] == 404
    denied = rpc(web, "tools/call", args, headers=readonly)
    assert denied["isError"] and "insufficient_scope" in denied["_meta"]["mcp/www_authenticate"][0]
    # Client registration changes do not change issuer+subject ownership.
    assert web.get(path, headers={"Authorization": "Bearer " + tokens(azp="refreshed-client")}).status_code == 200


def test_transport_rejects_owner_overrides_and_untyped_versions(creation_web):
    web = creation_web
    assert web.post("/api/creation-drafts", json={"world_preview": "Fixture", "action_id": "overpost-001",
                                                 "owner": "someone-else"}).status_code == 422
    draft = confirm(web, proposal(web))["structuredContent"]["draft"]
    response = web.post("/api/creation-drafts/" + draft["id"] + "/proposals", json={
        "action_id": "typed-version-001", "expected_version": True,
        "kind": "allocate_luck", "payload": {"points": 2}})
    assert response.status_code == 422
    invalid_version = tool(web, "propose_creation_transition", {"draft_id": draft["id"],
        "action_id": "mcp-bool-version", "expected_version": True,
        "kind": "allocate_luck", "payload": {"points": 2}})
    assert invalid_version["isError"]
    result = tool(web, "propose_creation_transition", {"draft_id": draft["id"],
        "action_id": "bad-command-001", "expected_version": 1, "kind": "patch",
        "payload": {"phase": "adventure_authorized"}})
    assert result["isError"] and result["structuredContent"]["error"] == "invalid_creation"
