"""Complete owned build preparation over authenticated HTTP/MCP fixture adapters."""
from dataclasses import asdict
import json

from fastapi.testclient import TestClient

from app.creation import Board, Candidate, Draft
from app.rules import Dice
from app.server import create_app
from .build_fixtures import loadout
from .class_review_fixtures import roll_payload
from .test_creation import concepts, offers
from .test_server import rpc, tool


def test_signed_creation_build_preview_approval_and_confirmation(tmp_path, config, verifier, tokens):
    app = create_app(tmp_path / "build-transport.sqlite3", config, verifier, enable_creation_drafts=True)
    with TestClient(app, base_url="https://dndgpt.example.test", headers={"Authorization": "Bearer " + tokens()}) as web:
        draws = []
        def deterministic(sides):
            draws.append(sides)
            return 0
        app.state.creation_repository.dice = Dice(deterministic)
        def approve(pending):
            result = tool(web, "confirm_creation_transition", {"proposal_id": pending["proposal"]["id"],
                "approval_token": pending["_meta"]["creation_approval"]["approval_token"]})
            assert not result.get("isError"), result
            return result["structuredContent"]["draft"]
        initial = web.post("/api/creation-drafts", json={"world_preview": "Neutral fixture world",
                                                          "action_id": "build-start-001"}).json()
        draft = approve(initial)
        def propose(kind, payload):
            response = web.post(f"/api/creation-drafts/{draft['id']}/proposals", json={
                "action_id": "build-step-" + str(draft["version"]), "expected_version": draft["version"],
                "kind": kind, "payload": payload})
            assert response.status_code == 200, response.text
            return response.json()
        def transition(kind, payload):
            nonlocal draft
            draft = approve(propose(kind, payload))
        def complete(kind, parent=None):
            choices = concepts(kind, parent)
            transition("roll_board", roll_payload(kind, choices))
            # Offer authoring uses only fixed final tiers exposed by preparation.
            preparation = tool(web, "get_creation_draft", {"draft_id": draft["id"], "include_preparation": True})
            assert not preparation.get("isError"), preparation
            fixed = preparation["structuredContent"]["preparation"]["pending_boards"][kind]
            tiers = {row["concept"]["id"]: row["rarity"] for row in fixed}
            authoring = Draft("Fixture authoring context", boards=(Board(kind, tuple(
                Candidate(row, (("final_rarity", tiers[row.id]),)) for row in choices)),))
            complete_offers = json.loads(json.dumps([asdict(row) for row in offers(authoring, kind)]))
            invalid = json.loads(json.dumps(complete_offers))
            if kind == "backgrounds":
                invalid[-1]["imprint"]["rider"] = None
            else:
                invalid[-1]["abilities"][0]["program"] = None
            request = {"action_id": "build-step-" + str(draft["version"]), "expected_version": draft["version"],
                       "kind": "complete_board", "payload": {"kind": kind, "offers": invalid}}
            before, draws_before = json.loads(json.dumps(draft)), len(draws)
            denied = web.post(f"/api/creation-drafts/{draft['id']}/proposals", json=request)
            assert denied.status_code == 422 and denied.json()["code"] == "invalid_creation"
            denied = tool(web, "propose_creation_transition", {"draft_id": draft["id"], **request})
            assert denied["isError"]
            assert web.get(f"/api/creation-drafts/{draft['id']}").json()["draft"] == before
            assert len(draws) == draws_before
            transition("complete_board", {"kind": kind, "offers": complete_offers})
            assert draft["board_programs"][kind]["programs_validated"] is True
            assert draft["board_programs"][kind]["semantic_tier_certification"] is False
        transition("allocate_luck", {"points": 0})
        complete("classes")
        transition("choose_class", {"candidate_id": "classes-candidate-0"})
        complete("signatures")
        complete("titles")
        transition("choose_sources", {"signature_ids": ["signatures-candidate-0", "signatures-candidate-1"], "title_id": None})
        complete("backgrounds", "classes-candidate-0-power-ACTION")
        transition("choose_background", {"candidate_id": "backgrounds-candidate-0",
                                         "allocation": {"STR": 2, "DEX": 2, "INT": 2, "CHA": 0, "LCK": 0}})
        assert len(draws) == 20 and draft["starting_build"] is None
        before = json.loads(json.dumps(draft))
        forbidden = web.post(f"/api/creation-drafts/{draft['id']}/proposals", json={"action_id": "build-too-early-confirm",
            "expected_version": draft["version"], "kind": "confirm_character", "payload": {"confirmed": True}})
        assert forbidden.status_code == 422
        pending = propose("prepare_starting_build", {"loadout": asdict(loadout())})
        assert web.get(f"/api/creation-drafts/{draft['id']}").json()["draft"] == before
        token = pending["_meta"]["creation_approval"]["approval_token"]
        denied = rpc(web, "tools/call", {"name": "confirm_creation_transition", "arguments": {
            "proposal_id": pending["proposal"]["id"], "approval_token": token}},
            headers={"Authorization": "Bearer " + tokens(scopes="campaign:read")})
        assert denied["isError"]
        assert web.get(f"/api/creation-drafts/{draft['id']}", headers={"Authorization": "Bearer " + tokens(subject="user-b")}).status_code == 404
        draft = approve(pending)
        assert approve(pending) == draft
        preview = draft["starting_build"]
        assert preview["carried_weight_grams"] == 7500 and preview["resources"] == {"hp": 105, "mp": 65, "sta": 68}
        transition("confirm_character", {"confirmed": True})
        assert draft["phase"] == "opening_preparation" and draft["starting_build"] == preview
        assert len(draws) == 20
        assert web.get("/api/campaigns").json()["campaigns"] == []
        assert not draft["fictional_time_advanced"] and not draft["playable"]
