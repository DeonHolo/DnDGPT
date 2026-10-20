import copy
from contextlib import contextmanager
import json

import pytest

from app.campaign_archive import CampaignArchive, digest
from app.chat_game import ChatGame
from app.continuity import model_view
from app.engine import EngineError
from app.save_history import SaveHistory
from app.save_history import changes_between
from .test_server import rpc, tool


@pytest.fixture
def draft(engine):
    return ChatGame(engine).create("owner-a", "Continuity fixture", "create-continuity-001", True)


def save(engine, state, changes, summary="Fixture update"):
    return ChatGame(engine).update("owner-a", state["id"], "save-continuity-" + str(state["version"]),
                                  state["version"], summary, changes)["campaign"]


def test_continuity_merges_in_same_save_and_read_never_resumes(engine, draft):
    state = save(engine, draft, {"continuity": {"last_player_intent": "Investigate the reported predator",
                  "unresolved_threads": ["Water intake remains unsafe"], "npc_commitments": ["The mason will inspect tomorrow"]}})
    state = save(engine, state, {"continuity": {"scene": "The mineral lick", "pending_decision": "Approach or observe?"}})
    before = engine.get_campaign("owner-a", state["id"])
    brief = before["resume_brief"]
    assert brief["last_player_intent"] == "Investigate the reported predator"
    assert brief["unresolved_threads"] == ["Water intake remains unsafe"]
    assert brief["npc_commitments"] == ["The mason will inspect tomorrow"]
    assert brief["paused"] and brief["continuation_requires_player_action"]
    assert engine.get_campaign("owner-a", state["id"]) == before
    assert engine.audit("owner-a", state["id"])["event_count"] == state["version"]


@pytest.mark.parametrize("note", [{"scene": "x" * 601}, {"unknown": "invented"},
                                     {"npc_commitments": ["x"] * 9}, {"last_action": 7}])
def test_invalid_continuity_is_atomic(engine, draft, note):
    with pytest.raises(EngineError):
        save(engine, draft, {"continuity": note, "character": {"hp": 1}})
    assert engine.get_campaign("owner-a", draft["id"]) == draft


def test_old_save_brief_marks_unknown_instead_of_inventing_thoughts(draft):
    brief = draft["resume_brief"]
    assert brief["missing_continuity"]
    assert brief["last_player_intent"] == brief["scene"] == brief["pending_decision"] == ""


def test_full_correction_diff_keeps_long_text_and_world_changes_without_hidden_values():
    full_text = "A long saved story. " * 100
    before = {"character": {"story_summary": ""}, "world": {"summary": "Before", "gm_only": {"secret": "HIDDEN BEFORE"}}}
    after = {"world": {"summary": "After", "gm_only": {"secret": "HIDDEN AFTER"}},
             "character": {"story_summary": full_text}}
    report = changes_between(before, after, limit=None, text_limit=None)
    assert next(row for row in report["changes"] if row["path"] == "character.story_summary")["after"]["text"] == full_text
    assert any(row["path"] == "world.summary" for row in report["changes"])
    assert "HIDDEN" not in json.dumps(report)
    hidden_only = changes_between({"world": {"private": "OLD"}}, {"world": {"private": "NEW"}})
    assert hidden_only["withheld_sections"] == ["world"] and hidden_only["changes"] == []


def test_turn_view_bounds_history_but_keeps_current_mechanics(engine, draft):
    state = save(engine, draft, {"world": {"summary": "A frontier settlement", "articles": ["World detail" * 500]},
        "upsert": {"world_log": [{"id": str(i), "text": "Past event. " * 80} for i in range(100)],
                   "abilities": [{"id": "fixture", "name": "Fixture", "mp_cost": 8, "mechanics": "Exact legal limits"}]}})
    turn = model_view(state, "turn")
    assert len(json.dumps(turn)) < len(json.dumps(state)) / 4
    assert turn["abilities"] == state["abilities"] and turn["character"] == state["character"]
    assert len(turn["world_log"]) == 3 and turn["omitted"]["world_log"] == 97
    assert len(state["world_log"]) == 100


def test_current_state_and_approval_read_share_one_transaction(engine, draft, monkeypatch):
    original = engine.store.transaction
    calls = []
    @contextmanager
    def count():
        calls.append(1)
        with original() as db:
            yield db
    monkeypatch.setattr(engine.store, "transaction", count)
    result = engine.campaign_context("owner-a", draft["id"])
    assert len(calls) == 1 and result["campaign"] == draft
    assert result["_meta"] == {"approval": None}


def test_history_pages_and_diffs_without_mutation_or_owner_leak(engine, draft):
    state = draft
    for i in range(5):
        state = save(engine, state, {"character": {"name": "Fixture " + str(i)}}, "Changed name " + str(i))
    history = SaveHistory(engine)
    page = history.list("owner-a", state["id"], limit=2)
    assert [row["version"] for row in page["versions"]] == [6, 5]
    assert [row["version"] for row in history.list("owner-a", state["id"], page["next_before"], 2)["versions"]] == [4, 3]
    diff = history.compare("owner-a", state["id"], 3)
    assert diff["historical"] and diff["previous_version"] == 2
    change = next(row for row in diff["changes"] if row["path"] == "character.name")
    assert change["before"]["text"] == "Fixture 0" and change["after"]["text"] == "Fixture 1"
    assert engine.get_campaign("owner-a", state["id"]) == state
    for operation in (lambda: history.list("owner-b", state["id"]), lambda: history.compare("owner-b", state["id"], 1)):
        with pytest.raises(EngineError) as error:
            operation()
        assert error.value.status == 404


def test_correction_has_readable_preview_and_still_needs_exact_approval(engine, draft):
    proposal = engine.propose_action("owner-a", draft["id"], "correct-fixture-001", 1,
        "correct_chat_state", {"changes": {"character": {"name": "Corrected fixture"}}, "reason": "Typo"})
    fields = proposal["proposal"]["field_changes"]["changes"]
    assert any(row["path"] == "character.name" and row["after"]["text"] == "Corrected fixture" for row in fields)
    assert engine.get_campaign("owner-a", draft["id"]) == draft
    with pytest.raises(EngineError):
        engine.execute_confirmed_action("owner-a", proposal["proposal"]["id"], "forged")
    result = engine.execute_confirmed_action("owner-a", proposal["proposal"]["id"], proposal["_meta"]["approval_token"])
    assert result["campaign"]["character"]["name"] == "Corrected fixture"
    assert result["campaign"]["paused"] and result["campaign"]["phase"] == "character_draft"


def test_portable_export_restore_preserves_source_and_requires_confirmation(engine, draft):
    source = save(engine, draft, {"character": {"story_summary": "A player-authored history"},
                                 "continuity": {"pending_decision": "Choose a class"}})
    service = CampaignArchive(engine)
    exported = service.export("owner-a", source["id"])
    preview = service.preview(exported["archive"])
    assert preview["restored_paused"] and not preview["overwrites_existing"]
    with pytest.raises(EngineError):
        service.restore("owner-a", exported["archive"], "restore-fixture-001", False)
    result = service.restore("owner-b", exported["archive"], "restore-fixture-001", True)
    restored = result["campaign"]
    assert restored["id"] != source["id"] and restored["version"] == 1 and restored["paused"]
    for key in ("character", "abilities", "equipment", "continuity", "fictional_time_seconds", "phase", "level_up_freeze"):
        assert restored[key] == source[key]
    assert service.restore("owner-b", exported["archive"], "restore-fixture-001", True) == result
    assert engine.get_campaign("owner-a", source["id"]) == source
    assert engine.audit("owner-b", restored["id"])["integrity_valid"]
    assert engine.get_campaign("owner-b", restored["id"])["restored_from"]["version"] == source["version"]
    with pytest.raises(EngineError):
        service.export("owner-b", source["id"])


@pytest.mark.parametrize("mutation", [lambda s: s.update(owner="other-account"),
    lambda s: s.update(phase=[]), lambda s: s["character"].update(hp=10**9),
    lambda s: s["character"].update(attributes={}), lambda s: s.update(rarity_candidates={"fake": {}}),
    lambda s: s.update(mode="sandbox")])
def test_malformed_import_rejected_even_with_recomputed_checksum(engine, draft, mutation):
    service = CampaignArchive(engine)
    archive = service.export("owner-a", draft["id"])["archive"]
    mutation(archive["campaign"])
    archive["sha256"] = digest(archive["campaign"])
    with pytest.raises(EngineError):
        service.restore("owner-a", archive, "restore-invalid-001", True)
    assert engine.list_campaigns("owner-a")[0]["id"] == draft["id"]
    assert len(engine.list_campaigns("owner-a")) == 1


def test_corrupted_export_rejected(engine, draft):
    service = CampaignArchive(engine)
    archive = service.export("owner-a", draft["id"])["archive"]
    archive["campaign"]["name"] = "Tampered"
    with pytest.raises(EngineError) as error:
        service.preview(archive)
    assert error.value.code == "archive_checksum"


@pytest.mark.parametrize("checksum", ["é" * 64, {}, "x" * 64])
def test_malformed_checksum_rejected_as_validation_error(engine, draft, checksum):
    service = CampaignArchive(engine)
    archive = service.export("owner-a", draft["id"])["archive"]
    archive["sha256"] = checksum
    with pytest.raises(EngineError) as error:
        service.preview(archive)
    assert error.value.code == "archive_checksum"


def test_transport_resume_turn_view_portability_and_read_scope(web, tokens):
    created = web.post("/api/chat-games", json={"name": "Transport fixture", "action_id": "create-recovery-http", "disposable": True}).json()["campaign"]
    cid = created["id"]
    compact = tool(web, "get_campaign", {"campaign_id": cid, "view": "resume"})
    assert compact["structuredContent"]["campaign"]["resume_brief"]["paused"]
    assert compact["_meta"]["campaign_snapshot"]["character"] == created["character"]
    assert web.get(f"/api/campaigns/{cid}/resume").json()["resume_brief"]["read_only"]
    assert web.get(f"/api/campaigns/{cid}/versions").json()["versions"][0]["version"] == 1
    exported = web.get(f"/api/campaigns/{cid}/export").json()
    body = {"archive": exported["archive"], "action_id": "restore-recovery-http", "confirm_restore": True}
    readonly = {"Authorization": "Bearer " + tokens(scopes="campaign:read")}
    assert web.post("/api/imports", json=body, headers=readonly).status_code == 403
    assert web.post("/api/imports/preview", json={"archive": body["archive"]}).status_code == 200
    restored = web.post("/api/imports", json=body)
    assert restored.status_code == 200 and restored.json()["campaign"]["paused"]
    assert web.get(f"/api/campaigns/{cid}").json()["campaign"] == created
    tools = {row["name"]: row for row in rpc(web, "tools/list")["tools"]}
    for name in ("export_campaign", "preview_campaign_import", "import_campaign", "compare_chat_version"):
        assert tools[name]["_meta"]["ui"]["visibility"] == ["app"]
