"""Pre-roll evidence, history boundaries and atomic saves; disposable fixtures only."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from app import creation as rules
from app import creation_codec as codec
from app.class_preparation import KnownClass, known_class, review
from app.creation_repository import CreationRepository, digest
from app.engine import Engine, EngineError
from app.rules import Dice
from app.storage import Store, canonical
from .class_review_fixtures import difference, review_for, roll_payload
from .test_creation import at_confirmation, concepts, offers
from .build_fixtures import loadout


@pytest.fixture
def repository(tmp_path):
    store = Store(tmp_path / "private-pool.sqlite3")
    store.initialize()
    return CreationRepository(store, Dice(lambda _: 0))


def confirm(repo, proposal, owner="owner-a"):
    return repo.confirm(owner, proposal["proposal"]["id"],
                        proposal["_meta"]["creation_approval"]["approval_token"])


def advance(repo, draft, kind, payload, owner="owner-a", tag="fixture"):
    pending = repo.propose_transition(owner, draft["id"], f"{tag}-step-{draft['version']}",
                                     draft["version"], kind, payload)
    return confirm(repo, pending, owner)["draft"]


def fresh(repo, tag, owner="owner-a"):
    draft = confirm(repo, repo.propose_start(owner, "Private pool fixture", "pool-start-" + tag), owner)["draft"]
    return advance(repo, draft, "allocate_luck", {"points": 0}, owner, tag)


def choices(tag):
    return tuple(replace(row, id=tag + "-" + row.id, name=tag + " " + row.name,
                         fingerprint=tuple(tag + " " + part for part in row.fingerprint))
                 for row in concepts("classes"))


def available(repo, draft, owner="owner-a"):
    data = repo.get_draft(owner, draft["id"], True)["preparation"]["known_classes"]
    return tuple(known_class({key: value for key, value in row.items() if key != "reference"}) for row in data)


def complete_classes(repo, draft, selected, owner="owner-a", tag="fixture"):
    draft = advance(repo, draft, "roll_board", roll_payload("classes", selected, available(repo, draft, owner)), owner, tag)
    with repo.store.transaction() as db:
        contract = repo._get(db, owner, draft["id"])
    return advance(repo, draft, "complete_board", {"kind": "classes",
        "offers": json.loads(canonical([asdict(row) for row in offers(contract, "classes")]))}, owner, tag)


@pytest.mark.parametrize("size", (12, 15))
def test_only_five_shortlisted_concepts_draw_independent_rarity_and_luck(size):
    selected, draws = choices("shortlist"), []
    evidence = review_for(selected, size=size)
    initial = rules.allocate_luck(rules.Draft("Fixture"), 2)
    result = rules.roll_board(initial, "classes", selected, Dice(lambda sides: draws.append(sides) or 0), evidence)
    assert draws == [10000] * 10 and len(result.boards[0].candidates) == 5
    assert result.class_review == evidence and result.class_context == ()
    assert [row.concept for row in result.boards[0].candidates] == list(selected)
    assert all(dict(row.receipt)["luck"] == 7 for row in result.boards[0].candidates)
    assert "Private rejected fixture" not in json.dumps(rules.public_preview(result))
    assert codec.decode(json.loads(canonical(codec.encode(result)))) == result


@pytest.mark.parametrize("fault", ("small", "large", "duplicate_seed", "missing_decision", "wrong_decision",
    "blank_reason", "missing_pair", "duplicate_pair", "unknown_pair", "unknown_shortlist", "parent_seed", "fake_history"))
def test_incomplete_or_fabricated_reviews_fail_before_any_random_draw(fault):
    selected = choices("invalid")
    packet = json.loads(canonical(asdict(review_for(selected, size=15))))
    if fault == "small": packet["seeds"] = packet["seeds"][:11]
    elif fault == "large": packet["seeds"].append(deepcopy(packet["seeds"][-1]))
    elif fault == "duplicate_seed": packet["seeds"][-1]["id"] = packet["seeds"][0]["id"]
    elif fault == "missing_decision": packet["decisions"].pop()
    elif fault == "wrong_decision": packet["decisions"][-1]["selected"] = True
    elif fault == "blank_reason": packet["decisions"][0]["reason"] = " "
    elif fault == "missing_pair": packet["differences"].pop()
    elif fault == "duplicate_pair": packet["differences"][-1] = packet["differences"][0]
    elif fault == "unknown_pair": packet["differences"][0]["right"] = "invented-finalist"
    elif fault == "unknown_shortlist": packet["shortlist"][-1] = "invented-seed"
    elif fault == "parent_seed": packet["seeds"][-1]["parent_id"] = "borrowed-parent"
    elif fault == "fake_history": packet["history_differences"] = [asdict(difference(selected[0].id, "invented-memory"))]
    def forbidden(_): pytest.fail("Invalid private evidence consumed randomness")
    with pytest.raises(ValueError):
        rules.roll_board(rules.allocate_luck(rules.Draft("Fixture"), 0), "classes", selected,
                         Dice(forbidden), review(packet))


def test_missing_review_and_shortlist_substitution_are_rejected_before_rolls():
    selected = choices("ordered")
    draft, dice = rules.allocate_luck(rules.Draft("Fixture"), 0), Dice(lambda _: pytest.fail("Unexpected roll"))
    with pytest.raises(ValueError, match="private 12"):
        rules.roll_board(draft, "classes", selected, dice)
    with pytest.raises(ValueError, match="shortlist in order"):
        rules.roll_board(draft, "classes", tuple(reversed(selected)), dice, review_for(selected))
    changed = (replace(selected[0], fingerprint=("Swapped law", *selected[0].fingerprint[1:])), *selected[1:])
    with pytest.raises(ValueError, match="shortlist in order"):
        rules.roll_board(draft, "classes", changed, dice, review_for(selected))


def test_history_requires_actual_references_and_exact_mechanical_reuse_ignores_theme():
    selected, prior = choices("current"), KnownClass("prior-draft", choices("prior")[0])
    context = (prior,)
    with pytest.raises(ValueError, match="actual available"):
        review_for(selected).validate(selected, context)
    reviewed = review_for(selected, context)
    reviewed.validate(selected, context)
    with pytest.raises(ValueError, match="actual available"):
        reviewed.validate(selected, ())
    reskin = replace(selected[0], fingerprint=tuple("  " + part.upper() + "  " for part in prior.concept.fingerprint[:6]) + ("New theme",))
    reskins = (reskin, *selected[1:])
    with pytest.raises(ValueError, match="exact mechanical reuse"):
        review_for(reskins, context).validate(reskins, context)


def test_private_review_survives_reopen_without_leaking_through_player_surfaces(repository):
    draft, selected, draws = fresh(repository, "private"), choices("private"), []
    repository.dice = Dice(lambda sides: draws.append(sides) or 0)
    payload = roll_payload("classes", selected)
    pending = repository.propose_transition("owner-a", draft["id"], "private-reviewed-roll", 2, "roll_board", payload)
    assert not draws
    result = confirm(repository, pending)
    reopened = CreationRepository(Store(repository.store.path), Dice(lambda _: pytest.fail("Retry rerolled")))
    assert confirm(reopened, pending) == result and draws == [10000] * 5
    private = reopened.get_draft("owner-a", draft["id"], True)["preparation"]
    assert private["class_review"] == payload["review"]
    assert private["known_classes"] == private["class_review_context"] == []
    assert private["semantic_tier_certification"] is False
    audit = reopened.audit("owner-a", draft["id"], True)
    event = audit["events"][-1]
    assert event["class_review_sha256"] == digest(payload["review"])
    assert event["class_context_sha256"] == digest([]) and event["private_seed_count"] == 12
    assert len(event["rolls"]) == 5 and audit["integrity_valid"]
    for output in (pending, result, reopened.get_draft("owner-a", draft["id"]), reopened.list_drafts("owner-a"), audit):
        assert "Private rejected fixture" not in json.dumps(output)
        assert "Fixture rejected reason" not in json.dumps(output)
    assert Engine(repository.store).list_campaigns("owner-a") == []


def test_history_uses_only_same_owner_completed_class_boards(repository):
    target = fresh(repository, "target")
    untouched = Engine(repository.store).create_sandbox("owner-a", "Unrelated sandbox fixture", "unrelated-history-001")
    hidden = complete_classes(repository, fresh(repository, "other", "owner-b"), choices("hidden"), "owner-b", "other")
    unoffered = fresh(repository, "unoffered")
    advance(repository, unoffered, "roll_board", roll_payload("classes", choices("unoffered")), tag="unoffered")
    assert available(repository, target) == ()
    previous = complete_classes(repository, fresh(repository, "previous"), choices("previous"), tag="previous")
    history = available(repository, target)
    assert len(history) == 5 and {row.draft_id for row in history} == {previous["id"]}
    assert hidden["id"] not in json.dumps(repository.get_draft("owner-a", target["id"], True))
    with pytest.raises(EngineError) as failure:
        repository.propose_transition("owner-a", target["id"], "forged-history-request", 2, "roll_board",
            {**roll_payload("classes", choices("target"), history), "history": []})
    assert failure.value.code == "invalid_creation"
    result = advance(repository, target, "roll_board", roll_payload("classes", choices("target"), history), tag="target")
    with repository.store.transaction() as db:
        assert repository._get(db, "owner-a", result["id"]).class_context == history
    assert Engine(repository.store).get_campaign("owner-a", untouched["id"]) == untouched


def test_new_owned_history_between_proposal_and_approval_invalidates_before_rng(repository):
    draft, selected = fresh(repository, "pending"), choices("pending")
    pending = repository.propose_transition("owner-a", draft["id"], "pending-class-review", 2, "roll_board",
                                            roll_payload("classes", selected))
    complete_classes(repository, fresh(repository, "intervening"), choices("intervening"), tag="intervening")
    before = repository.audit("owner-a", draft["id"], True)
    draws = []
    repository.dice = Dice(lambda sides: draws.append(sides) or 0)
    with pytest.raises(EngineError) as failure:
        confirm(repository, pending)
    assert failure.value.code == "invalid_creation" and not draws
    assert repository.audit("owner-a", draft["id"], True) == before
    with repository.store.transaction() as db:
        assert db.execute("SELECT result FROM creation_proposals_v1 WHERE id=?", (pending["proposal"]["id"],)).fetchone()[0] is None
    history = available(repository, draft)
    saved = advance(repository, draft, "roll_board", roll_payload("classes", selected, history), tag="revised")
    assert saved["version"] == 3 and draws == [10000] * 5


def test_old_pending_five_only_roll_cannot_bypass_current_review_gate(repository):
    draft = fresh(repository, "legacy-pending")
    pending = repository.propose_transition("owner-a", draft["id"], "legacy-pending-roll", 2, "roll_board",
                                            roll_payload("classes", choices("legacy-pending")))
    with repository.store.transaction() as db:
        row = db.execute("SELECT request FROM creation_proposals_v1 WHERE id=?", (pending["proposal"]["id"],)).fetchone()
        request = json.loads(row[0])
        request["payload"].pop("review")
        db.execute("UPDATE creation_proposals_v1 SET request=? WHERE id=?", (canonical(request), pending["proposal"]["id"]))
    repository.dice = Dice(lambda _: pytest.fail("Legacy approval consumed a draw"))
    before = repository.audit("owner-a", draft["id"], True)
    with pytest.raises(EngineError) as failure:
        confirm(repository, pending)
    assert failure.value.code == "invalid_creation"
    assert repository.audit("owner-a", draft["id"], True) == before


def test_legacy_rolled_drafts_cannot_fabricate_a_retroactive_review():
    original = at_confirmation()
    legacy = replace(original, class_review=None, class_context=())
    assert rules.public_preview(legacy)["version"] == original.version
    for operation in (lambda: rules.prepare_starting_build(legacy, loadout()),
                      lambda: rules.confirm_character(replace(legacy, loadout=loadout()), confirmed=True)):
        with pytest.raises(ValueError, match="cannot be silently backfilled"):
            operation()
    assert legacy.class_review is None and legacy.boards == original.boards


def test_pending_review_survives_online_backup_and_a_fresh_process(repository, tmp_path):
    draft = fresh(repository, "recover")
    pending = repository.propose_transition("owner-a", draft["id"], "recover-pool-roll", 2, "roll_board",
                                            roll_payload("classes", choices("recover")))
    project, backup = Path(__file__).resolve().parents[1], tmp_path / "recovered.sqlite3"
    copied = subprocess.run([sys.executable, str(project / "scripts/backup_db.py"), str(repository.store.path), str(backup)],
                            capture_output=True, text=True, timeout=20)
    assert copied.returncode == 0, copied.stderr
    program = """
import sys
from app.creation_repository import CreationRepository
from app.storage import Store
from app.rules import Dice
draws=[]
repo=CreationRepository(Store(sys.argv[1]),Dice(lambda sides:draws.append(sides) or 0))
pending=repo.get_draft('owner-a',sys.argv[2])['_meta']['creation_approvals'][0]
result=repo.confirm('owner-a',pending['proposal']['id'],pending['approval_token'])
assert repo.confirm('owner-a',pending['proposal']['id'],pending['approval_token'])==result
assert draws==[10000]*5
assert len(repo.get_draft('owner-a',sys.argv[2],True)['preparation']['class_review']['seeds'])==12
assert repo.audit('owner-a',sys.argv[2],True)['integrity_valid']
"""
    recovered = subprocess.run([sys.executable, "-c", program, str(backup), draft["id"]], cwd=project,
                               capture_output=True, text=True, timeout=20)
    assert recovered.returncode == 0, recovered.stderr
    assert repository.get_draft("owner-a", draft["id"])["draft"] == draft
    assert confirm(repository, pending)["draft"]["version"] == 3
