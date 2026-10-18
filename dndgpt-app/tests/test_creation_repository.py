"""Persistence/approval tests with disposable structural kits, never live saves."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

from app.creation import owned_abilities
from app.creation_repository import CreationRepository
from app.engine import Engine, EngineError
from app.rules import Dice
from app.storage import Store, canonical
from tests.test_creation import concepts, offers
from .build_fixtures import loadout
from .class_review_fixtures import roll_payload


@pytest.fixture
def repository(tmp_path):
    store = Store(tmp_path / "creation.sqlite3")
    store.initialize()
    return CreationRepository(store, Dice(lambda _: 0))


def approve(repository, proposal, owner="owner-a"):
    return repository.confirm(owner, proposal["proposal"]["id"],
                              proposal["_meta"]["creation_approval"]["approval_token"])


def start(repository, owner="owner-a"):
    return approve(repository, repository.propose_start(
        owner, "Neutral development fixture world", "start-fixture-001"), owner)["draft"]


def commit(repository, draft, kind, payload, action_id=None):
    proposal = repository.propose_transition("owner-a", draft["id"],
        action_id or f"fixture-step-{draft['version']:04}", draft["version"], kind, payload)
    return approve(repository, proposal)["draft"]


def current_contract(repository, draft):
    with repository.store.transaction() as db:
        return repository._get(db, "owner-a", draft["id"])


def prepare_board(repository, draft, kind, parent=None):
    draft = commit(repository, draft, "roll_board", roll_payload(kind, concepts(kind, parent)))
    return commit(repository, draft, "complete_board", {"kind": kind,
        "offers": json.loads(canonical([asdict(row) for row in offers(current_contract(repository, draft), kind)]))})


def assert_error(code, operation):
    with pytest.raises(EngineError) as failure:
        operation()
    assert failure.value.code == code


def test_start_is_inert_owner_scoped_and_approved_once(repository):
    proposal = repository.propose_start("owner-a", "Neutral fixture", "start-explicit-001")
    assert repository.list_drafts("owner-a")["drafts"] == []
    assert Engine(repository.store).list_campaigns("owner-a") == []
    token = proposal["_meta"]["creation_approval"]["approval_token"]
    assert token not in json.dumps(proposal["proposal"])
    assert repository.list_drafts("owner-b")["_meta"]["creation_approvals"] == []
    assert_error("not_found", lambda: repository.confirm("owner-b", proposal["proposal"]["id"], token))
    assert_error("approval_required", lambda: repository.confirm("owner-a", proposal["proposal"]["id"], "wrong"))
    assert repository.propose_start("owner-a", "Neutral fixture", "start-explicit-001") == proposal
    assert_error("idempotency_conflict", lambda: repository.propose_start(
        "owner-a", "Different world", "start-explicit-001"))
    result = approve(repository, proposal)
    assert approve(repository, proposal) == result
    assert result["draft"]["phase"] == "luck" and result["draft"]["version"] == 1
    assert result["draft"]["playable_campaign_created"] is False
    assert_error("not_found", lambda: repository.get_draft("owner-b", result["draft"]["id"]))
    assert_error("not_found", lambda: repository.audit("owner-b", result["draft"]["id"]))
    assert repository.audit("owner-a", result["draft"]["id"])["integrity_valid"]
    other = approve(repository, repository.propose_start(
        "owner-b", "Independent account fixture", "start-explicit-001"), "owner-b")["draft"]
    assert other["id"] != result["draft"]["id"]
    assert len(repository.list_drafts("owner-a")["drafts"]) == 1
    assert len(repository.list_drafts("owner-b")["drafts"]) == 1


def test_proposals_inspection_and_retries_do_not_draw_or_replace_rolls(repository):
    calls = []
    repository.dice = Dice(lambda sides: calls.append(sides) or 0)
    draft = commit(repository, start(repository), "allocate_luck", {"points": 2})
    payload = roll_payload("classes", concepts("classes"))
    proposal = repository.propose_transition("owner-a", draft["id"], "roll-board-once", 2, "roll_board", payload)
    assert calls == []
    assert repository.get_draft("owner-a", draft["id"])["draft"] == draft
    assert "natural" not in json.dumps(proposal)
    rolled = approve(repository, proposal)
    assert calls == [10000] * 10
    assert approve(repository, proposal) == rolled and calls == [10000] * 10
    repository = CreationRepository(Store(repository.store.path), Dice(lambda _: pytest.fail("Unexpected RNG")))
    assert repository.get_draft("owner-a", draft["id"])["draft"] == rolled["draft"]
    assert repository.propose_transition("owner-a", draft["id"], "roll-board-once", 2,
                                          "roll_board", payload)["committed"] == rolled
    assert_error("invalid_creation", lambda: repository.propose_transition(
        "owner-a", draft["id"], "try-new-reroll", 3, "roll_board", payload))
    assert "natural" not in json.dumps(repository.get_draft("owner-a", draft["id"], True))
    prepared = repository.get_draft("owner-a", draft["id"], True)["preparation"]
    assert len(prepared["pending_boards"]["classes"]) == 5
    assert all(row["rarity"] == "UNCOMMON" for row in prepared["pending_boards"]["classes"])
    assert rolled["draft"]["boards"]["classes"] == []
    assert "natural" not in json.dumps(repository.audit("owner-a", draft["id"]))
    raw = repository.audit("owner-a", draft["id"], True)
    assert raw["integrity_valid"] and len(raw["events"][-1]["rolls"]) == 5
    assert all(row["luck"] == 7 and row["natural"] == 1 for row in raw["events"][-1]["rolls"])


def test_full_creation_transcript_persists_phases_and_hides_opening(repository):
    untouched = Engine(repository.store).create_sandbox("owner-a", "Unrelated fixture", "other-create-001")
    draft = commit(repository, start(repository), "allocate_luck", {"points": 2})
    draft = prepare_board(repository, draft, "classes")
    draft = commit(repository, draft, "choose_class", {"candidate_id": "classes-candidate-0"})
    draft = prepare_board(repository, draft, "signatures")
    draft = prepare_board(repository, draft, "titles")
    draft = commit(repository, draft, "choose_sources", {
        "signature_ids": ["signatures-candidate-0", "signatures-candidate-1"], "title_id": None})
    parent = owned_abilities(current_contract(repository, draft))[0].id
    draft = prepare_board(repository, draft, "backgrounds", parent)
    draft = commit(repository, draft, "choose_background", {"candidate_id": "backgrounds-candidate-0",
        "allocation": dict(STR=2, DEX=1, INT=1, CHA=0, LCK=0), "name": "Fixture character"})
    assert draft["phase"] == "character_confirmation" and draft["attributes"]["LCK"] == 7
    assert_error("invalid_creation", lambda: repository.propose_transition(
        "owner-a", draft["id"], "skip-confirmation", draft["version"], "authorize_adventure", {"authorized": True}))
    assert_error("invalid_creation", lambda: repository.propose_transition(
        "owner-a", draft["id"], "missing-build-001", draft["version"], "confirm_character", {"confirmed": True}))
    before_build = repository.audit("owner-a", draft["id"], True)["events"]
    pending_build = repository.propose_transition("owner-a", draft["id"], "complete-build-001", draft["version"],
        "prepare_starting_build", {"loadout": json.loads(canonical(asdict(loadout())))})
    assert repository.get_draft("owner-a", draft["id"])["draft"]["starting_build"] is None
    def forbidden(_):
        raise AssertionError("Starting build, confirmation and opening must never reroll")
    repository = CreationRepository(Store(repository.store.path), Dice(forbidden))
    approved_build = approve(repository, pending_build)
    assert approve(repository, pending_build) == approved_build
    draft = approved_build["draft"]
    assert repository.get_draft("owner-a", draft["id"])["draft"] == draft
    assert draft["starting_build"]["carried_weight_grams"] == 7500
    assert repository.audit("owner-a", draft["id"], True)["events"][:-1] == before_build
    draft = commit(repository, draft, "confirm_character", {"confirmed": True})
    secret = "PRIVATE FIXTURE CONVERGENCE"
    opening = {key: secret for key in ("location", "local_date_time", "factions", "opposition",
                                        "hooks_and_rewards", "convergence_truth")}
    proposal = repository.propose_transition("owner-a", draft["id"], "prepare-opening-001", draft["version"],
        "prepare_opening", {"preview": "Public fixture opening", "private_commitment": opening})
    assert secret not in json.dumps(proposal)
    draft = approve(repository, proposal)["draft"]
    assert draft["phase"] == "adventure_authorization"
    draft = commit(repository, draft, "authorize_adventure", {"authorized": True})
    repository = CreationRepository(Store(repository.store.path))
    assert repository.get_draft("owner-a", draft["id"])["draft"] == draft
    assert current_contract(repository, draft).private_opening == tuple(sorted(opening.items()))
    for output in (repository.list_drafts("owner-a"), repository.get_draft("owner-a", draft["id"], True),
                   repository.audit("owner-a", draft["id"], True)):
        assert secret not in json.dumps(output)
    audit = repository.audit("owner-a", draft["id"])
    assert audit["integrity_valid"] and len(audit["events"]) == draft["version"] == 17
    assert audit["events"][-1]["decision"] == {"authorized": True}
    assert draft["playable"] is False and draft["fictional_time_advanced"] is False
    assert Engine(repository.store).get_campaign("owner-a", untouched["id"]) == untouched
    assert len(Engine(repository.store).list_campaigns("owner-a")) == 1


def test_concurrent_duplicate_approval_rolls_once(repository):
    calls = []
    repository.dice = Dice(lambda sides: calls.append(sides) or 0)
    draft = commit(repository, start(repository), "allocate_luck", {"points": 2})
    proposal = repository.propose_transition("owner-a", draft["id"], "concurrent-roll-001", draft["version"],
        "roll_board", roll_payload("classes", concepts("classes")))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: approve(repository, proposal), range(2)))
    assert results[0] == results[1] and calls == [10000] * 10
    assert len(repository.audit("owner-a", draft["id"])["events"]) == 3


def test_competing_versions_expiry_and_failed_commit_do_not_partially_save(repository, monkeypatch):
    draft = start(repository)
    first = repository.propose_transition("owner-a", draft["id"], "luck-choice-one", 1, "allocate_luck", {"points": 1})
    second = repository.propose_transition("owner-a", draft["id"], "luck-choice-two", 1, "allocate_luck", {"points": 2})
    append = repository._append
    def interrupted(*args):
        raise RuntimeError("Simulated interruption before commit")
    monkeypatch.setattr(repository, "_append", interrupted)
    with pytest.raises(RuntimeError, match="interruption"):
        approve(repository, first)
    assert repository.get_draft("owner-a", draft["id"])["draft"] == draft
    assert len(repository.audit("owner-a", draft["id"])["events"]) == 1
    monkeypatch.setattr(repository, "_append", append)
    committed = approve(repository, first)
    assert committed["draft"]["luck_points"] == 1
    assert_error("version_conflict", lambda: approve(repository, second))
    assert_error("version_conflict", lambda: repository.propose_transition(
        "owner-a", draft["id"], "stale-third-choice", 1, "allocate_luck", {"points": 0}))
    with repository.store.transaction() as db:
        db.execute("UPDATE creation_proposals_v1 SET created_at=0")
    assert approve(repository, first) == committed  # A committed retry survives token age.
    assert_error("proposal_expired", lambda: approve(repository, second))
    assert repository.get_draft("owner-a", draft["id"])["_meta"]["creation_approvals"] == []


@pytest.mark.parametrize("kind,payload", [
    ("patch", {"phase": "adventure_authorized"}),
    ("allocate_luck", {"points": True}),
    ("allocate_luck", {"points": 1, "extra": "untrusted"}),
    ("allocate_luck", {}),
    ("roll_board", {"kind": "classes", "concepts": {}}),
    ("roll_board", {"kind": "classes", "concepts": ["untyped"] * 5}),
    ("choose_sources", {"signature_ids": "not-an-array", "title_id": None}),
    ("confirm_character", {"confirmed": True}),
])
def test_invalid_or_out_of_phase_commands_fail_without_draws(repository, kind, payload):
    repository.dice = Dice(lambda _: pytest.fail("Invalid proposal consumed RNG"))
    draft = start(repository)
    assert_error("invalid_creation", lambda: repository.propose_transition(
        "owner-a", draft["id"], "invalid-command-001", 1, kind, payload))
    assert repository.get_draft("owner-a", draft["id"])["draft"] == draft


def test_pending_approval_and_fixed_receipts_survive_process_and_online_backup(repository, tmp_path):
    draft = commit(repository, start(repository), "allocate_luck", {"points": 2})
    draft = commit(repository, draft, "roll_board", roll_payload("classes", concepts("classes")))
    pending = repository.propose_transition("owner-a", draft["id"], "pending-kits-001", draft["version"],
        "complete_board", {"kind": "classes", "offers": json.loads(canonical([
            asdict(row) for row in offers(current_contract(repository, draft), "classes")]))})
    project = Path(__file__).resolve().parents[1]
    backup = tmp_path / "restored.sqlite3"
    result = subprocess.run([sys.executable, str(project / "scripts/backup_db.py"),
                             str(repository.store.path), str(backup)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    program = """
import json, sys
from app.creation_repository import CreationRepository
from app.rules import Dice
from app.storage import Store
def forbidden(_): raise AssertionError('Recovery must not roll')
repo = CreationRepository(Store(sys.argv[1]), Dice(forbidden))
before = repo.audit('owner-a', sys.argv[2], True)
pending = repo.get_draft('owner-a', sys.argv[2])['_meta']['creation_approvals'][0]
result = repo.confirm('owner-a', pending['proposal']['id'], pending['approval_token'])
assert repo.confirm('owner-a', pending['proposal']['id'], pending['approval_token']) == result
after = repo.audit('owner-a', sys.argv[2], True)
assert before['events'][2]['rolls'] == after['events'][2]['rolls']
assert after['integrity_valid'] and result['draft']['version'] == 4
print(json.dumps(result))
"""
    recovered = subprocess.run([sys.executable, "-c", program, str(backup), draft["id"]],
                               cwd=project, capture_output=True, text=True, timeout=20)
    assert recovered.returncode == 0, recovered.stderr
    assert json.loads(recovered.stdout)["receipt"]["proposal_id"] == pending["proposal"]["id"]
    assert repository.get_draft("owner-a", draft["id"])["draft"] == draft  # Restore is independent.


def test_legacy_tables_are_untouched_and_data_corruption_is_detected(repository):
    engine = Engine(repository.store)
    existing = engine.create_sandbox("owner-a", "Legacy fixture", "legacy-fixture-001")
    repository.store.initialize()
    draft = start(repository)
    assert engine.get_campaign("owner-a", existing["id"]) == existing
    assert engine.audit("owner-a", existing["id"])["integrity_valid"]
    with repository.store.transaction() as db:
        stored = json.loads(db.execute("SELECT data FROM creation_drafts_v1 WHERE id=?", (draft["id"],)).fetchone()[0])
        stored["draft"]["world_preview"] = "Tampered fixture"
        db.execute("UPDATE creation_drafts_v1 SET data=? WHERE id=?", (canonical(stored), draft["id"]))
    assert repository.audit("owner-a", draft["id"])["integrity_valid"] is False
    assert_error("integrity_error", lambda: repository.get_draft("owner-a", draft["id"]))
