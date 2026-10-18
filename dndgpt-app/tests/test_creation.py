"""Disposable structural fixtures; no gameplay generation or live campaign access."""
from dataclasses import replace
import json

import pytest

from app.creation import (Ability, Concept, Draft, Imprint, Offer, allocate_luck,
                          authorize_adventure, board, choose_background, choose_class,
                          choose_sources, complete_board, confirm_character, prepare_starting_build,
                          owned_abilities, prepare_opening, public_preview, roll_board as _roll_board)
from app.rules import ATTRIBUTES, Dice, RARITIES
from app.powers import Effect, Formula, Program, Resolution, Rider
from .build_fixtures import loadout
from .class_review_fixtures import review_for


def roll_board(draft, kind, choices, dice, review=None, history=()):
    """Existing rule fixtures supply explicit evidence under the new contract."""
    if kind == "classes" and review is None and len(choices) == 5:
        review = review_for(choices, history)
    return _roll_board(draft, kind, choices, dice, review, history)


def concepts(kind, parent=None):
    return tuple(Concept(f"{kind}-candidate-{i}", f"Fixture {kind} {i}",
                         (f"{kind} law {i}", f"loop {i}", f"cycle {i}", f"space {i}",
                          f"utility {i}", f"counterplay {i}", f"theme {i}"),
                         summoner=kind == "classes" and i == 0, parent_id=parent)
                 for i in range(5))


def power(kind, candidate, rarity, activation="ACTION"):
    program = Program((Effect("DAMAGE", Formula(flat=2), "ARCANE"),),
                      resolution=Resolution("SAVE", "INT", save_attribute="DEX") if kind == "signatures" else Resolution("ATTACK", "INT"))
    return Ability(f"{candidate}-power-{activation}", "Structural fixture power",
                   {"classes": "CLASS", "signatures": "SIGNATURE", "titles": "TITLE"}[kind],
                   candidate, rarity, activation,
                   ("Fixture motion", "Fixture source", "Fixture delivery",
                    "Fixture observation", "Fixture ending"),
                   0, 0, 6000, "One legal fixture target", "Bounded fixture program",
                   "When legally activated", "Instant", "None", "Own this source",
                   "Does not stack", "Semantic tier strength is not certified", program)


def offers(draft, kind, *, class_free_action=True):
    result = []
    for candidate in board(draft, kind).candidates:
        identity = candidate.concept.id
        certificate = ("Fixture tier explanation", "Fixture ordinary trigger",
                       "Fixture lower-tier comparison", "Fixture actual limits")
        if kind == "backgrounds":
            result.append(Offer(identity, candidate.rarity, certification=certificate,
                                identity="Fixture lived history",
                                imprint=Imprint(candidate.concept.parent_id,
                                                "Fixture integrated rider", "Parent limits retained",
                                                Rider((Effect("DAMAGE", Formula(flat=1), "LIGHT"),))),
                                world_footprint="Optional fixture opportunity"))
        else:
            powers = (power(kind, identity, candidate.rarity),)
            if kind == "classes" and candidate.concept.summoner:
                from app.summons import Behavior, Manifest
                from .test_summons import unit
                formation = Manifest(identity, (unit(control="AUTONOMOUS",
                    behavior=Behavior("NEAREST_HOSTILE", "strike-mote")),), 1, 3)
                powers = (replace(powers[0], program=Program((), target_kind="SELF", summon=formation)),)
            if kind == "classes" and class_free_action and RARITIES.index(candidate.rarity) >= 3:
                powers += (power(kind, identity, candidate.rarity, "FREE_ACTION"),)
            result.append(Offer(identity, candidate.rarity, powers, certificate))
    return tuple(result)


def prepared(draft, kind, parent=None):
    draft = roll_board(draft, kind, concepts(kind, parent), Dice(lambda _: 0))
    return complete_board(draft, kind, offers(draft, kind))


def at_background(*, luck=0, title=None):
    draft = allocate_luck(Draft("Neutral fixture world preview"), luck)
    draft = choose_class(prepared(draft, "classes"), "classes-candidate-0")
    draft = prepared(prepared(draft, "signatures"), "titles")
    return choose_sources(draft, ("signatures-candidate-0", "signatures-candidate-1"), title)


def at_confirmation():
    draft = at_background()
    draft = prepared(draft, "backgrounds", owned_abilities(draft)[0].id)
    return choose_background(draft, "backgrounds-candidate-0",
                             dict(STR=2, DEX=2, INT=2, CHA=0, LCK=0))


def forbidden_rng(_):
    pytest.fail("A blocked transition or inspection consumed RNG")


def test_turn_one_waits_for_luck_and_never_generates_class_rolls_early():
    draft = Draft("Neutral fixture world preview")
    with pytest.raises(ValueError, match="Requires class"):
        roll_board(draft, "classes", concepts("classes"), Dice(forbidden_rng))
    with pytest.raises(ValueError, match="Wait for"):
        allocate_luck(draft)
    assert draft.phase == "luck" and draft.boards == ()
    defaulted = allocate_luck(draft, explicitly_defaulted=True)
    assert defaulted.luck_points == 0 and defaulted.luck_defaulted


@pytest.mark.parametrize("points", [-1, 5, True, 1.5, "2"])
def test_invalid_preawakening_luck_is_rejected(points):
    with pytest.raises(ValueError):
        allocate_luck(Draft("Fixture world"), points)


def test_future_boards_and_duplicate_concepts_fail_before_rng():
    draft = allocate_luck(Draft("Fixture world"), 0)
    with pytest.raises(ValueError, match="Requires signatures_titles"):
        roll_board(draft, "signatures", concepts("signatures"), Dice(forbidden_rng))
    proposed = list(concepts("classes"))
    proposed[1] = replace(proposed[1], fingerprint=(*proposed[0].fingerprint[:6], "New particles"))
    with pytest.raises(ValueError, match="reskins"):
        roll_board(draft, "classes", tuple(proposed), Dice(forbidden_rng))
    with pytest.raises(ValueError, match="summoner"):
        roll_board(draft, "classes", tuple(replace(c, summoner=False) for c in concepts("classes")),
                   Dice(forbidden_rng))
    with pytest.raises(ValueError, match="5 entries"):
        roll_board(draft, "classes", concepts("classes")[:4], Dice(forbidden_rng))


def test_five_independent_rarity_and_luck_draws_are_fixed_and_not_replayed():
    calls = []
    dice = Dice(lambda sides: calls.append(sides) or 0)
    draft = roll_board(allocate_luck(Draft("Fixture world"), 2), "classes", concepts("classes"), dice)
    assert calls == [10000] * 10
    assert all(dict(c.receipt)["luck"] == 7 for c in board(draft, "classes").candidates)
    assert all(c.rarity == "UNCOMMON" for c in board(draft, "classes").candidates)
    assert public_preview(draft)["boards"]["classes"] == []  # Unfinished kits stay private.
    with pytest.raises(ValueError, match="already rolled"):
        roll_board(draft, "classes", concepts("classes"), Dice(forbidden_rng))
    assert calls == [10000] * 10


def test_epic_plus_free_action_and_same_rarity_repair_before_display():
    draft = roll_board(allocate_luck(Draft("Fixture world"), 0), "classes", concepts("classes"),
                       Dice(lambda _: 9900))
    receipts = tuple(c.receipt for c in board(draft, "classes").candidates)
    with pytest.raises(ValueError, match="class-native starting Free Action"):
        complete_board(draft, "classes", offers(draft, "classes", class_free_action=False))
    wrong_tier = list(offers(draft, "classes"))
    wrong_tier[0] = replace(wrong_tier[0], rarity="COMMON")
    with pytest.raises(ValueError, match="rolled rarity"):
        complete_board(draft, "classes", tuple(wrong_tier))
    fixed = complete_board(draft, "classes", offers(draft, "classes"))
    assert tuple(c.receipt for c in board(fixed, "classes").candidates) == receipts
    with pytest.raises(ValueError, match="immutable"):
        complete_board(fixed, "classes", offers(fixed, "classes"))


def test_owned_power_provenance_and_complete_mechanics_are_required():
    draft = roll_board(allocate_luck(Draft("Fixture world"), 0), "classes", concepts("classes"),
                       Dice(lambda _: 0))
    offered = list(offers(draft, "classes"))
    offered[0] = replace(offered[0], abilities=(replace(offered[0].abilities[0], source_kind="TITLE"),))
    with pytest.raises(ValueError, match="provenance"):
        complete_board(draft, "classes", tuple(offered))
    with pytest.raises(ValueError, match="physical manifestation"):
        replace(offers(draft, "classes")[0].abilities[0], manifestation=("motion", "source", "", "hit", "end"))
    with pytest.raises(ValueError, match="integer"):
        replace(offers(draft, "classes")[0].abilities[0], mp_cost=True)


def test_class_and_both_source_boards_lock_before_backgrounds():
    draft = allocate_luck(Draft("Fixture world"), 0)
    with pytest.raises(ValueError, match="not complete"):
        choose_class(draft, "classes-candidate-0")
    draft = choose_class(prepared(draft, "classes"), "classes-candidate-0")
    with pytest.raises(ValueError, match="Requires background_attributes"):
        roll_board(draft, "backgrounds", concepts("backgrounds"), Dice(forbidden_rng))
    draft = prepared(draft, "signatures")
    with pytest.raises(ValueError, match="not complete"):
        choose_sources(draft, ("signatures-candidate-0", "signatures-candidate-1"), None)
    draft = prepared(draft, "titles")
    for selection in [("signatures-candidate-0",), ("signatures-candidate-0", "signatures-candidate-0")]:
        with pytest.raises(ValueError):
            choose_sources(draft, selection, None)
    assert choose_sources(draft, ("signatures-candidate-0", "signatures-candidate-1"), None).phase == "background_attributes"


@pytest.mark.parametrize("parent", ["titles-candidate-0-power-ACTION", "signatures-candidate-4-power-ACTION", "future-ability"])
def test_title_none_unchosen_and_future_imprint_targets_rejected_before_rolls(parent):
    draft = at_background()
    with pytest.raises(ValueError, match="actually owned"):
        roll_board(draft, "backgrounds", concepts("backgrounds", parent), Dice(forbidden_rng))


@pytest.mark.parametrize("parent_index", [0, 1, 2, 3])
def test_owned_class_signature_and_selected_title_parents_are_eligible(parent_index):
    draft = at_background(title="titles-candidate-0")
    parent = owned_abilities(draft)[parent_index]
    ready = prepared(draft, "backgrounds", parent.id)
    assert all(offer.imprint.parent_id == parent.id for offer in board(ready, "backgrounds").offers)
    assert parent in owned_abilities(ready)


def test_background_cannot_grant_second_power_or_change_locked_parent():
    draft = at_background()
    parent = owned_abilities(draft)[0]
    draft = roll_board(draft, "backgrounds", concepts("backgrounds", parent.id), Dice(lambda _: 0))
    proposed = list(offers(draft, "backgrounds"))
    proposed[0] = replace(proposed[0], abilities=(parent,))
    with pytest.raises(ValueError, match="exactly one integrated"):
        complete_board(draft, "backgrounds", tuple(proposed))
    proposed = list(offers(draft, "backgrounds"))
    proposed[0] = replace(proposed[0], imprint=Imprint("unowned", "rider", "limits"))
    with pytest.raises(ValueError, match="integrated"):
        complete_board(draft, "backgrounds", tuple(proposed))
    with pytest.raises(TypeError):
        Imprint(parent.id, "rider", "limits", activation="REACTION")


def test_remaining_points_cap_and_no_retroactive_luck_change():
    draft = at_background(luck=4)
    draft = prepared(draft, "backgrounds", owned_abilities(draft)[0].id)
    with pytest.raises(ValueError, match="maximum is 9"):
        choose_background(draft, "backgrounds-candidate-0", dict(STR=0, DEX=0, INT=0, CHA=0, LCK=2))
    with pytest.raises(ValueError, match="remaining"):
        choose_background(draft, "backgrounds-candidate-0", dict(STR=0, DEX=0, INT=0, CHA=0, LCK=0))
    final = choose_background(draft, "backgrounds-candidate-0", dict(STR=1, DEX=1, INT=0, CHA=0, LCK=0))
    assert dict(final.attributes) == dict(STR=6, DEX=6, INT=5, CHA=5, LCK=9)
    defaulted = at_background()
    defaulted = prepared(defaulted, "backgrounds", owned_abilities(defaulted)[0].id)
    final = choose_background(defaulted, "backgrounds-candidate-0", dict(STR=2, DEX=0, INT=0, CHA=0, LCK=4))
    assert dict(final.attributes)["LCK"] == 9
    assert all(dict(c.receipt)["luck"] == 5 for entry in final.boards for c in entry.candidates)


def test_character_confirmation_private_preparation_and_adventure_are_separate_gates():
    draft = at_confirmation()
    snapshot = public_preview(draft)
    assert snapshot["derived"]["hp_max"] == 105
    assert snapshot["derived"]["mp_max"] == 65
    assert snapshot["derived"]["sta_max"] == 68
    with pytest.raises(ValueError, match="Requires adventure_authorization"):
        authorize_adventure(draft, authorized=True)
    with pytest.raises(ValueError, match="Explicit character"):
        confirm_character(draft, confirmed=1)
    with pytest.raises(ValueError, match="Complete the starting build"):
        confirm_character(draft, confirmed=True)
    draft = prepare_starting_build(draft, loadout())
    confirmed = confirm_character(draft, confirmed=True)
    assert confirmed.phase == "opening_preparation"
    with pytest.raises(ValueError, match="Requires adventure_authorization"):
        authorize_adventure(confirmed, authorized=True)
    private = dict(location="Fixture position", local_date_time="Fixture date 9:00 AM",
                   factions="Fixture actors", opposition="Fixture precommitted opposition",
                   hooks_and_rewards="Fixture optional hooks", convergence_truth="PRIVATE_FIXTURE_TRUTH")
    ready = prepare_opening(confirmed, "Neutral fixture opening preview", private)
    assert "PRIVATE_FIXTURE_TRUTH" not in json.dumps(public_preview(ready))
    with pytest.raises(ValueError, match="Separate explicit"):
        authorize_adventure(ready, authorized=1)
    authorized = authorize_adventure(ready, authorized=True)
    assert authorized.phase == "adventure_authorized"
    assert public_preview(authorized)["playable_campaign_created"] is False
    assert public_preview(authorized)["fictional_time_advanced"] is False
    assert authorized.world_preview == draft.world_preview
    assert draft.phase == "character_confirmation"  # Prior state is not mutated.


def test_public_inspection_hides_raw_rolls_and_cannot_mutate_fixed_offers():
    draft = at_confirmation()
    snapshot = public_preview(draft)
    serialized = json.dumps(snapshot)
    assert "luck_roll" not in serialized and "natural" not in serialized
    snapshot["boards"]["classes"][0]["abilities"][0]["resolution"] = "Tampered preview"
    assert "Tampered preview" not in json.dumps(public_preview(draft))
    assert set(dict(draft.attributes)) == set(ATTRIBUTES)
