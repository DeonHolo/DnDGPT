"""Signed adapters enforce private pre-roll preparation without a new player turn."""
from fastapi.testclient import TestClient

from app.rules import Dice
from app.server import create_app
from .class_review_fixtures import roll_payload
from .test_creation import concepts
from .test_server import tool


def test_signed_http_and_mcp_require_private_review_before_any_class_roll(tmp_path, config, verifier, tokens):
    app = create_app(tmp_path / "class-review-transport.sqlite3", config, verifier, enable_creation_drafts=True)
    with TestClient(app, base_url="https://dndgpt.example.test", headers={"Authorization": "Bearer " + tokens()}) as web:
        draws = []
        app.state.creation_repository.dice = Dice(lambda sides: draws.append(sides) or 0)
        def approve(pending):
            response = tool(web, "confirm_creation_transition", {
                "proposal_id": pending["proposal"]["id"],
                "approval_token": pending["_meta"]["creation_approval"]["approval_token"]})
            assert not response.get("isError"), response
            return response["structuredContent"]
        draft = approve(web.post("/api/creation-drafts", json={"world_preview": "Transport fixture",
                                    "action_id": "review-start-001"}).json())["draft"]
        path = f"/api/creation-drafts/{draft['id']}"
        pending = web.post(path + "/proposals", json={"action_id": "review-luck-001", "expected_version": 1,
                          "kind": "allocate_luck", "payload": {"points": 2}}).json()
        draft = approve(pending)["draft"]
        payload = roll_payload("classes", concepts("classes"))
        bare = {key: value for key, value in payload.items() if key != "review"}
        request = {"action_id": "review-class-roll", "expected_version": 2, "kind": "roll_board", "payload": bare}
        denied = web.post(path + "/proposals", json=request)
        assert denied.status_code == 422 and denied.json()["code"] == "invalid_creation"
        denied = tool(web, "propose_creation_transition", {"draft_id": draft["id"], **request})
        assert denied["isError"] and not draws
        assert web.get(path).json()["draft"] == draft
        request["payload"] = payload
        response = tool(web, "propose_creation_transition", {"draft_id": draft["id"], **request})
        assert not response.get("isError"), response
        assert "_meta" not in response["structuredContent"]
        pending = {**response["structuredContent"], "_meta": response["_meta"]}
        assert not draws and "Private rejected fixture" not in str(pending)
        other = web.get(path, headers={"Authorization": "Bearer " + tokens(subject="user-b")})
        assert other.status_code == 404
        denied = web.post(path + "/proposals", json=request,
                          headers={"Authorization": "Bearer " + tokens(scopes="campaign:read")})
        assert denied.status_code == 403 and not draws
        result = approve(pending)
        assert approve(pending) == result and draws == [10000] * 10
        assert result["draft"]["version"] == 3 and result["draft"]["phase"] == "class"
        assert result["draft"]["boards"]["classes"] == []
        assert "Private rejected fixture" not in str(result)
        private = tool(web, "get_creation_draft", {"draft_id": draft["id"], "include_preparation": True})
        assert not private.get("isError"), private
        preparation = private["structuredContent"]["preparation"]
        assert preparation["class_review"] == payload["review"]
        assert preparation["known_classes"] == [] and preparation["semantic_tier_certification"] is False
        assert web.get("/api/campaigns").json()["campaigns"] == []
        assert not result["draft"]["fictional_time_advanced"] and not result["draft"]["playable"]
