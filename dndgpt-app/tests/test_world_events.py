import copy
import json

import pytest

from app import records
from app.chat_game import ChatGame, apply_changes
from app.engine import EngineError
from app.game_random import GameRandom
from app.rules import Dice
from app.storage import canonical
from app.world_events import CHANCES, CATEGORIES, SEVERITIES, draw_event, validate_pool


def pool():
    return {"events": [{"id": category + "-" + severity, "category": category, "severity": severity,
                       "title": category + " incident", "summary": "A contextual incident at the crossing."}
                      for category in CATEGORIES for severity in SEVERITIES]}


class Draws:
    def __init__(self, values): self.values, self.sides = iter(values), []
    def roll(self, sides):
        self.sides.append(sides)
        value = next(self.values)
        assert 1 <= value <= sides
        return value


@pytest.mark.parametrize("context,chance", CHANCES.items())
def test_exact_trigger_boundary_and_conditional_draws(context, chance):
    no = Draws([chance + 1])
    assert draw_event(context, "t1", pool(), "root", [], no)["outcome"] == "no_event"
    assert no.sides == [100]
    yes = Draws([chance, 30, 50])
    result = draw_event(context, "t1", pool(), "root", [], yes)
    assert result["outcome"] == "event" and result["category"] == "combat" and result["severity"] == "minor"
    assert yes.sides == [100, 100, 100]  # A single candidate needs no fake d1.


def test_selection_and_exhaustion_do_not_reroll():
    candidates = pool(); candidates["events"].append({**candidates["events"][0], "id": "second"})
    roll = Draws([1, 1, 1, 2])
    assert draw_event("safe", "t", candidates, "p", [], roll)["selected"]["id"] == "second"
    exhausted = Draws([1, 1, 1])
    result = draw_event("safe", "t", pool(), "p", ["combat-minor"], exhausted)
    assert result["outcome"] == "no_applicable_event" and len(exhausted.sides) == 3


def setup(engine):
    state = ChatGame(engine).create("owner-a", "Events fixture", "events-create", True)
    state.update(phase="adventure", paused=False)
    with engine.store.transaction() as db:
        records.update(db, "campaigns_v1", {"id": state["id"]}, {"data": canonical(state)})
    return state


def request(state, transition, root=None):
    row = {"label": "Contextual event", "kind": "world_event", "context": "frontier", "transition_id": transition}
    row.update({"pool_action_id": root} if root else {"pool": pool()})
    return "event-" + state["id"] + "-" + transition, [row]


def test_cached_pool_receipts_are_private_and_retries_do_not_draw(engine):
    state = setup(engine); consumed = []
    values = iter([0, 0, 0, 99])
    box = GameRandom(engine.store, Dice(lambda n: consumed.append(n) or next(values)), engine)
    action, rows = request(state, "t1")
    first = box.roll("owner-a", action, rows, state["id"])
    assert first == box.roll("owner-a", action, rows, state["id"])
    assert "_event_pool" not in json.dumps(first) and "_event_pool" not in json.dumps(box.get("owner-a", action, True))
    assert consumed == [100, 100, 100]
    transition = {"id": "t1", "eligible": True, "context": "frontier", "roll_action_id": action}
    game = ChatGame(engine)
    saved = game.update("owner-a", state["id"], "event-save", state["version"], "Crossing", {"event_transition": transition})["campaign"]
    assert saved["event_tracking"]["used_events"][action] == ["combat-minor"]
    assert not saved["event_tracking"]["check_due"]
    with pytest.raises(EngineError): game.update("owner-a", state["id"], "double-event", saved["version"], "Duplicate", {"event_transition": transition})
    second_action, second_rows = request(state, "t2", action)
    assert box.roll("owner-a", second_action, second_rows, state["id"])["results"][0]["result"]["outcome"] == "no_event"
    assert consumed == [100, 100, 100, 100]
    with pytest.raises(EngineError): box.roll("owner-a", action + "-reroll", rows, state["id"])
    with pytest.raises(EngineError): box.roll("owner-b", second_action, second_rows, state["id"])


def test_pool_coverage_validated_before_any_batch_roll(engine):
    state = setup(engine); action, rows = request(state, "invalid")
    rows[0]["pool"]["events"].pop()
    box = GameRandom(engine.store, Dice(lambda _: pytest.fail("Drew before validating the whole batch")), engine)
    with pytest.raises(EngineError): box.roll("owner-a", action, [{"label": "First", "kind": "dice", "sides": 6}] + rows, state["id"])
    with pytest.raises(ValueError): validate_pool({"events": pool()["events"], "category_weights": {"combat": 100}})


def test_missing_check_is_distinct_from_no_event_and_corrections_do_not_roll(engine):
    state = setup(engine)
    moved = apply_changes(state, {"current_location": "Far ridge"})
    assert moved["event_tracking"]["check_due"]
    skipped = apply_changes(moved, {"event_transition": {"id": "menu", "eligible": False, "reason": "Only reviewing the map"}})
    assert not skipped["event_tracking"]["check_due"]
    with pytest.raises(EngineError): apply_changes(state, {"event_transition": {"id": "fake", "eligible": True, "context": "safe", "roll_action_id": "missing"}})
    assert "event_tracking" not in apply_changes(state, {"current_location": "Corrected ridge"}, correction=True)


@pytest.mark.parametrize("frozen", ["paused", "level_up_freeze"])
def test_frozen_clock_blocks_event_rolls(engine, frozen):
    state = setup(engine); state[frozen] = True
    with engine.store.transaction() as db:
        records.update(db, "campaigns_v1", {"id": state["id"]}, {"data": canonical(state)})
    box = GameRandom(engine.store, Dice(lambda _: pytest.fail("Rolled a frozen transition")), engine)
    action, rows = request(state, "frozen")
    with pytest.raises(EngineError) as error: box.roll("owner-a", action, rows, state["id"])
    assert error.value.code == "event_clock_frozen"
