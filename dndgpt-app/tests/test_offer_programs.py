"""Every displayed offer must compile; semantic/tier judgment is a separate gate."""
from copy import deepcopy
from dataclasses import asdict, replace
import json

import pytest

from app import creation as rules
from app.creation_repository import CreationRepository
from app.engine import EngineError
from app.gear import ItemPower
from app.powers import Effect, Formula, Program
from app.rules import Dice
from app.storage import Store, canonical
from .build_fixtures import loadout
from .test_creation import at_background, at_confirmation, concepts, offers, roll_board
from .class_review_fixtures import roll_payload
from .test_creation_repository import approve, commit, current_contract, start


def pending(kind):
    draft = rules.allocate_luck(rules.Draft("Neutral compiler fixture"), 0)
    if kind in ("signatures", "titles"):
        draft = roll_board(draft, "classes", concepts("classes"), Dice(lambda _: 0))
        draft = rules.complete_board(draft, "classes", offers(draft, "classes"))
        draft = rules.choose_class(draft, "classes-candidate-0")
    elif kind == "backgrounds":
        draft = at_background()
    parent = rules.owned_abilities(draft)[0].id if kind == "backgrounds" else None
    return roll_board(draft, kind, concepts(kind, parent), Dice(lambda _: 0))


@pytest.mark.parametrize("kind", ("classes", "signatures", "titles", "backgrounds"))
@pytest.mark.parametrize("index", range(5))
def test_any_non_executable_offer_blocks_the_whole_board_without_changing_rolls(kind, index):
    draft = pending(kind)
    original, proposed = deepcopy(draft), list(offers(draft, kind))
    offer = proposed[index]
    if kind == "backgrounds":
        proposed[index] = replace(offer, imprint=replace(offer.imprint, rider=None))
    else:
        proposed[index] = replace(offer, abilities=(replace(offer.abilities[0], program=None), *offer.abilities[1:]))
    with pytest.raises(ValueError, match="executable"):
        rules.complete_board(draft, kind, tuple(proposed))
    assert draft == original and rules.board(draft, kind).offers == ()
    # Correct unpublished mechanics at their existing rolled grades, without RNG.
    completed = rules.complete_board(draft, kind, offers(draft, kind))
    assert rules.board(completed, kind).candidates == rules.board(draft, kind).candidates
    assert completed.version == draft.version + 1


@pytest.mark.parametrize("kind", ("classes", "signatures", "titles", "backgrounds"))
def test_program_validation_is_reported_without_claiming_semantic_certification(kind):
    draft = pending(kind)
    before = rules.public_preview(draft)["board_programs"][kind]
    assert before == {"offers_checked": 0, "programs_validated": False,
                      "semantic_tier_certification": False, "issues": []}
    completed = rules.complete_board(draft, kind, offers(draft, kind))
    report = rules.public_preview(completed)["board_programs"][kind]
    assert report == {"offers_checked": 5, "programs_validated": True,
                      "semantic_tier_certification": False, "issues": []}
    assert not rules.public_preview(completed)["playable_campaign_created"]


def test_background_compiles_against_the_actual_owned_reaction_parent():
    draft = pending("classes")
    proposed = list(offers(draft, "classes"))
    base = proposed[0].abilities[0]
    reaction = replace(base, id=base.id + "-ward", activation="REACTION", mp_cost=0, sta_cost=0,
        program=Program((Effect("WARD", Formula(flat=2), duration_turns=1),),
                        target_kind="SELF", reaction_trigger="INCOMING_DAMAGE"))
    proposed[0] = replace(proposed[0], abilities=(reaction,base))
    draft = rules.choose_class(rules.complete_board(draft, "classes", tuple(proposed)), proposed[0].candidate_id)
    for kind in ("signatures", "titles"):
        draft = roll_board(draft, kind, concepts(kind), Dice(lambda _: 0))
        draft = rules.complete_board(draft, kind, offers(draft, kind))
    draft = rules.choose_sources(draft, ("signatures-candidate-0", "signatures-candidate-1"), None)
    draft = roll_board(draft, "backgrounds", concepts("backgrounds", reaction.id), Dice(lambda _: 0))
    # The fixture rider deals damage; it cannot attach to a ward-only Reaction.
    with pytest.raises(ValueError, match="ward semantics"):
        rules.complete_board(draft, "backgrounds", offers(draft, "backgrounds"))


def test_failed_fifth_offer_is_atomic_and_fixed_completion_survives_reopen(tmp_path):
    store = Store(tmp_path / "offer-programs.sqlite3")
    store.initialize()
    repo = CreationRepository(store, Dice(lambda _: 0))
    draft = commit(repo, start(repo), "allocate_luck", {"points": 0})
    draft = commit(repo, draft, "roll_board", roll_payload("classes", concepts("classes")))
    audit = repo.audit("owner-a", draft["id"], True)
    offered = json.loads(canonical([asdict(row) for row in offers(current_contract(repo, draft), "classes")]))
    bad = deepcopy(offered)
    bad[-1]["abilities"][0]["program"] = None
    repo.dice = Dice(lambda _: pytest.fail("Completing or inspecting offers must not roll"))
    with pytest.raises(EngineError) as failure:
        repo.propose_transition("owner-a", draft["id"], "offer-completion-001", draft["version"],
                                "complete_board", {"kind": "classes", "offers": bad})
    assert failure.value.code == "invalid_creation"
    assert repo.audit("owner-a", draft["id"], True) == audit
    assert repo.get_draft("owner-a", draft["id"])["draft"] == draft
    with store.transaction() as db:
        assert db.execute("SELECT count(*) FROM creation_proposals_v1 WHERE action_id=?",
                          ("offer-completion-001",)).fetchone()[0] == 0
    approved = repo.propose_transition("owner-a", draft["id"], "offer-completion-001", draft["version"],
                                      "complete_board", {"kind": "classes", "offers": offered})
    result = approve(repo, approved)
    reopened = CreationRepository(Store(store.path), repo.dice)
    assert approve(reopened, approved) == result
    assert reopened.get_draft("owner-a", draft["id"])["draft"] == result["draft"]
    after = reopened.audit("owner-a", draft["id"], True)
    assert after["events"][:-1] == audit["events"] and after["integrity_valid"]


@pytest.mark.parametrize("kind", ("classes", "signatures", "titles", "backgrounds"))
def test_legacy_unselected_option_remains_readable_but_cannot_bypass_build_validation(kind):
    draft = at_confirmation()
    entry = rules.board(draft, kind)
    last = entry.offers[-1]
    if kind == "backgrounds":
        broken = replace(last, imprint=replace(last.imprint, rider=None))
    else:
        broken = replace(last, abilities=(replace(last.abilities[0], program=None), *last.abilities[1:]))
    legacy = replace(draft, boards=tuple(replace(row, offers=(*row.offers[:-1], broken))
                                        if row.kind == kind else row for row in draft.boards))
    inspected = rules.public_preview(legacy)
    assert inspected["board_programs"][kind]["programs_validated"] is False
    assert inspected["board_programs"][kind]["issues"][0]["candidate_id"] == last.candidate_id
    assert last.candidate_id not in dict(legacy.selections)[kind]
    with pytest.raises(ValueError, match="executable"):
        rules.prepare_starting_build(legacy, loadout())


def test_starting_item_cannot_shadow_an_owned_source_power_id():
    draft, equipment = at_confirmation(), loadout()
    staff = next(item for item in equipment.items if item.id == "staff")
    copied = replace(rules.owned_abilities(draft)[0], source_kind="ITEM", source_id=staff.id, rarity=staff.rarity)
    staff = replace(staff, powers=(ItemPower(copied),))
    equipment = replace(equipment, items=tuple(staff if row.id == staff.id else row for row in equipment.items))
    with pytest.raises(ValueError, match="distinct IDs"):
        rules.prepare_starting_build(draft, equipment)


def test_old_pending_completion_is_revalidated_and_fails_as_a_structured_error(tmp_path):
    store = Store(tmp_path / "old-offer-approval.sqlite3")
    store.initialize()
    repo = CreationRepository(store, Dice(lambda _: 0))
    draft = commit(repo, start(repo), "allocate_luck", {"points": 0})
    draft = commit(repo, draft, "roll_board", roll_payload("classes", concepts("classes")))
    approved = repo.propose_transition("owner-a", draft["id"], "old-completion-001", draft["version"],
        "complete_board", {"kind": "classes", "offers": json.loads(canonical([
            asdict(row) for row in offers(current_contract(repo, draft), "classes")]))})
    # Reproduce a pre-gate pending request: old code accepted missing programs.
    with store.transaction() as db:
        request = json.loads(db.execute("SELECT request FROM creation_proposals_v1 WHERE id=?",
                                        (approved["proposal"]["id"],)).fetchone()[0])
        request["payload"]["offers"][-1]["abilities"][0]["program"] = None
        db.execute("UPDATE creation_proposals_v1 SET request=? WHERE id=?",
                   (canonical(request), approved["proposal"]["id"]))
    before = repo.audit("owner-a", draft["id"], True)
    reopened = CreationRepository(Store(store.path), Dice(lambda _: pytest.fail("Old approval cannot reroll")))
    with pytest.raises(EngineError) as failure:
        approve(reopened, approved)
    assert failure.value.code == "invalid_creation"
    assert reopened.audit("owner-a", draft["id"], True) == before
    assert reopened.get_draft("owner-a", draft["id"])["draft"] == draft
    with store.transaction() as db:
        assert db.execute("SELECT result FROM creation_proposals_v1 WHERE id=?",
                          (approved["proposal"]["id"],)).fetchone()[0] is None
