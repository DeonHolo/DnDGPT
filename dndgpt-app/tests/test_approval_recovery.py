import time

from app import records
from .test_server import rpc, tool


def prepared_chat(web):
    created = tool(web, "create_chat_game", {"name": "Disposable approval recovery", "action_id": "recovery-create", "disposable": True})
    state = created["structuredContent"]["campaign"]
    saved = tool(web, "save_chat_update", {"campaign_id": state["id"], "action_id": "recovery-prepare", "expected_version": 1,
                 "summary": "Prepare test character", "changes": {"character": {"name": "Test Scribe", "class_name": "Door Scribe"},
                 "opening_preview": "A sealed test gate."}})
    return saved["structuredContent"]["campaign"]


def propose(web, state, action="recovery-review", kind="confirm_chat_character"):
    return tool(web, "propose_action", {"campaign_id": state["id"], "action_id": action,
                "expected_version": state["version"], "kind": kind, "payload": {}})


def expire(web, proposal):
    with web.app.state.engine.store.transaction() as db:
        records.update(db, "proposals_v1", {"id": proposal["structuredContent"]["proposal"]["id"]}, {"created_at": time.time() - 901})


def test_expired_confirmation_stays_reviewable_without_mutating_campaign(web, tokens):
    state = prepared_chat(web)
    old = propose(web, state)
    token = old["_meta"]["approval_token"]
    expire(web, old)
    before = tool(web, "audit", {"campaign_id": state["id"]})["structuredContent"]
    for name in ("get_campaign", "render_dashboard"):
        result = tool(web, name, {"campaign_id": state["id"]})
        approval = result["_meta"]["approval"]
        assert approval["expired"] and approval["proposal"] == old["structuredContent"]["proposal"]
        assert "approval_token" not in approval
        assert token not in str(result["content"]) + str(result["structuredContent"])
        assert result["structuredContent"]["campaign"] == state
    denied = tool(web, "execute_confirmed_action", {"proposal_id": old["structuredContent"]["proposal"]["id"], "approval_token": token})
    assert denied["isError"] and denied["structuredContent"]["error"] == "proposal_expired"
    refreshed = propose(web, state, "recovery-review-again")
    assert refreshed["_meta"]["approval_token"] != token
    assert tool(web, "get_campaign", {"campaign_id": state["id"]})["structuredContent"]["campaign"] == state
    assert tool(web, "audit", {"campaign_id": state["id"]})["structuredContent"] == before
    pending = tool(web, "render_dashboard", {"campaign_id": state["id"]})["_meta"]["approval"]
    assert not pending["expired"] and pending["proposal"]["id"] == refreshed["structuredContent"]["proposal"]["id"]
    assert pending["expires_at"] == refreshed["_meta"]["approval_expires_at"]
    confirmed = tool(web, "execute_confirmed_action", {"proposal_id": pending["proposal"]["id"], "approval_token": pending["approval_token"]})["structuredContent"]["campaign"]
    assert confirmed["phase"] == "ready" and confirmed["paused"] and confirmed["fictional_time_seconds"] == 0
    assert confirmed["character"] == state["character"] and confirmed["version"] == state["version"] + 1
    assert tool(web, "get_campaign", {"campaign_id": state["id"]})["_meta"]["approval"] is None
    start = propose(web, confirmed, "recovery-start", "start_chat_adventure")
    expire(web, start)
    assert tool(web, "get_campaign", {"campaign_id": state["id"]})["_meta"]["approval"]["expired"]
    assert tool(web, "get_campaign", {"campaign_id": state["id"]})["structuredContent"]["campaign"] == confirmed
    forbidden = rpc(web, "tools/call", {"name": "get_campaign", "arguments": {"campaign_id": state["id"]}}, headers={"Authorization": "Bearer " + tokens("user-b")})
    assert forbidden["isError"] and forbidden["structuredContent"]["error"] == "not_found"


def test_changed_draft_does_not_revive_stale_confirmation(web):
    state = prepared_chat(web)
    old = propose(web, state)
    expire(web, old)
    updated = tool(web, "save_chat_update", {"campaign_id": state["id"], "action_id": "recovery-revision", "expected_version": state["version"],
                   "summary": "Player revised draft", "changes": {"character": {"name": "Revised Scribe"}}})["structuredContent"]["campaign"]
    assert tool(web, "get_campaign", {"campaign_id": state["id"]})["_meta"]["approval"] is None
    proposal = propose(web, updated, "recovery-revised-review")
    assert proposal["structuredContent"]["proposal"]["character_before"]["name"] == "Revised Scribe"
