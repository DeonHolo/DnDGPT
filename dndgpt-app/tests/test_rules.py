import pytest

from app.rules import ATTRIBUTES, BANDS, RARITIES, Dice, TurnBudget, derived, modifier
from app.spatial import Point, SolidBox, in_range, legal_target


@pytest.mark.parametrize("score,expected", [(1, -2), (4, -1), (5, 0), (6, 0), (7, 1), (9, 2), (20, 7)])
def test_modifier_floor(score, expected):
    assert modifier(score) == expected


def test_base_statistics():
    assert derived(dict.fromkeys(ATTRIBUTES, 5)) == {
        "hp_max": 95, "mp_max": 55, "sta_max": 60, "carry_capacity_kg": 22,
        "def": 10, "movement_mm": 6000}


def test_every_rarity_boundary_and_exact_distribution():
    counts = dict.fromkeys(RARITIES, 0)
    for natural in range(1, 10001):
        dice = Dice(lambda _, value=natural: value - 1)
        roll = dice.rarity(5)
        counts[roll["final_rarity"]] += 1
        assert roll["luck_roll"] is None
    assert list(counts.values()) == [2000, 3000, 2500, 1500, 700, 300]


@pytest.mark.parametrize("luck,roll,enhanced", [(7, 500, True), (7, 501, False), (9, 1000, True),
                                             (20, 3500, True), (20, 3501, False)])
def test_independent_luck_threshold(luck, roll, enhanced):
    calls = []
    values = iter([2000, roll])
    def randbelow(sides):
        calls.append(sides)
        return next(values) - 1
    result = Dice(randbelow).rarity(luck)
    assert calls == [10000, 10000]
    assert result["enhanced"] is enhanced
    assert result["final_rarity"] == ("UNCOMMON" if enhanced else "COMMON")


def test_unique_still_records_independent_luck_without_second_promotion():
    values = iter([9999, 0])
    result = Dice(lambda _: next(values)).rarity(20)
    assert result["base_rarity"] == result["final_rarity"] == "UNIQUE"
    assert result["luck_roll"] == 1


def test_advantage_disadvantage_and_cancellation():
    values = iter([2, 17])
    assert Dice(lambda _: next(values)).check(11, 0, advantage=True)["natural"] == 18
    calls = []
    result = Dice(lambda sides: calls.append(sides) or 9).check(11, 2, True, True)
    assert calls == [20] and result["natural"] == 10


def test_turn_resources_are_distinct_and_no_extra_free_action():
    before = TurnBudget()
    after = before.spend("free_action")
    assert after.action == after.reaction == after.item_interaction == 1
    with pytest.raises(ValueError):
        after.spend("free_action")
    assert before.free_action == 1
    assert after.spend("movement_mm", 3500).movement_mm == 2500


def test_exact_range_elevation_and_committed_cover():
    origin = Point(0, 0)
    assert in_range(origin, Point(3000, 4000), 5000)
    assert not in_range(origin, Point(3000, 4001), 5000)
    assert not in_range(origin, Point(3000, 4000, 1), 5000)
    wall = SolidBox(Point(1000, -100, -100), Point(1100, 100, 2000))
    assert legal_target(origin, Point(2000, 0), 6000, [wall])["reason"] == "Blocked by solid cover"
    assert legal_target(origin, Point(2000, 1000), 6000, [wall])["legal"]
