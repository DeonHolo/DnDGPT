import copy

import pytest

from app.chat_game import ChatGame, apply_changes
from app.engine import EngineError


def quest():
    return {"id": "clear-crossing", "quest_schema": 1, "name": "Reopen the crossing",
            "finish_condition": "The crossing is passable and its keeper is safe.",
            "objectives": [{"id": "clear", "text": "Clear two fallen beams", "current": 0, "target": 2},
                           {"id": "keeper", "text": "Bring the keeper to safety"},
                           {"id": "bell", "text": "Recover the bell", "optional": True,
                            "reward": {"currency": {"crowns": 5}}}],
            "system_reward": {"xp": 20, "currency": {"crowns": 50}, "evolution_credits": 1,
                              "items": [{"id": "crossing-ring", "name": "Keeper's ring", "rarity": "RARE"}]},
            "contract_payment": {"creditor": "The keeper", "condition": "Return to the lodge",
                                 "reward": {"currency": {"crowns": 10}}}}


def playing(engine):
    state = ChatGame(engine).create("owner-a", "Quest fixture", "quest-create", True)
    state.update(phase="adventure", paused=False)
    return state


def write(state, row):
    return apply_changes(state, {"upsert": {"quest_log": [row]}})


def completed(state):
    row = copy.deepcopy(state["quest_log"][0])
    row["objectives"][0]["current"] = 2
    row["objectives"][1]["status"] = "done"
    return row


def test_completion_settles_once_and_contract_is_separate(engine):
    start = playing(engine)
    active = write(start, quest())
    done = write(active, completed(active))
    assert done["quest_log"][0]["status"] == "completed"
    assert done["quest_log"][0]["reward_status"] == "settled"
    assert done["character"]["xp"] == start["character"]["xp"] + 20
    assert done["funds"]["crowns"] == 50
    assert done["reward_credits"] == {"earned": 1, "spent": []}
    assert [r["id"] for r in done["inventory"]].count("crossing-ring") == 1
    again = write(done, copy.deepcopy(done["quest_log"][0]))
    assert again == done
    payment = copy.deepcopy(done["quest_log"][0]); payment["contract_payment"]["status"] = "collected"
    paid = write(done, payment)
    assert paid["funds"]["crowns"] == 60 and paid["character"]["xp"] == done["character"]["xp"]
    assert write(paid, paid["quest_log"][0]) == paid


@pytest.mark.parametrize("change", ["finish", "reward", "objectives", "delete", "reopen", "reward_status"])
def test_published_quest_cannot_grow_or_repay(engine, change):
    state = write(playing(engine), quest())
    row = copy.deepcopy(state["quest_log"][0]); delta = {"upsert": {"quest_log": [row]}}
    if change == "finish": row["finish_condition"] += " And also rebuild the town."
    if change == "reward": row["system_reward"]["xp"] += 100
    if change == "objectives": row["objectives"].append({"id": "extra", "text": "One more thing"})
    if change == "delete": delta = {"remove": {"quest_log": [row["id"]]}}
    if change == "reward_status": row["reward_status"] = "settled"
    if change == "reopen":
        state = write(state, completed(state)); row = copy.deepcopy(state["quest_log"][0]); row["status"] = "active"
        row["objectives"][0].update(status="pending", current=0)
    before = copy.deepcopy(state)
    with pytest.raises(EngineError): apply_changes(state, delta if change != "reopen" else {"upsert": {"quest_log": [row]}})
    assert state == before


def test_optional_bonus_and_legacy_history(engine):
    state = playing(engine)
    state["quest_log"] = [{"id": "old", "name": "Old record", "status": "completed"}]
    legacy = copy.deepcopy(state)
    assert apply_changes(state, {"notes": "A note"})["quest_log"] == legacy["quest_log"]
    row = quest(); row["id"] = "old"
    row["objectives"][0]["current"] = 2; row["objectives"][1]["status"] = "done"
    converted = write(state, row)
    assert converted["quest_settlements"]["old"]["system"]["historical"]
    assert converted["character"]["xp"] == state["character"]["xp"]
    fresh = write(playing(engine), quest()); bonus = copy.deepcopy(fresh["quest_log"][0])
    bonus["objectives"][2]["status"] = "done"
    updated = write(fresh, bonus)
    assert updated["funds"]["crowns"] == 5 and updated["quest_log"][0]["status"] == "active"
    assert write(updated, updated["quest_log"][0]) == updated


def test_free_credit_is_banked_and_spent_once(engine):
    state = write(playing(engine), quest()); state = write(state, completed(state))
    state["abilities"] = [{"id": "ward", "name": "Ward", "kind": "passive", "rarity": "RARE",
                           "evolutions": [{"id": "old-evo", "name": "Old upgrade"}]}]
    parent = copy.deepcopy(state["abilities"][0]); parent["evolutions"].append({"id": "new-evo", "name": "Wider ward"})
    changes = {"upsert": {"abilities": [parent]}, "spend_evolution_credit": {"ability_id": "ward", "evolution_id": "new-evo"}}
    result = apply_changes(state, changes)
    assert result["reward_credits"]["spent"] == ["new-evo"]
    assert result["character"]["skill_points"] == state["character"]["skill_points"]
    with pytest.raises(EngineError): apply_changes(result, changes)
    parent["evolutions"][0]["name"] = "Rewritten old upgrade"
    with pytest.raises(EngineError): apply_changes(state, changes)


def test_xp_reward_level_freeze_has_no_extra_pause_gate(engine):
    state = playing(engine); row = quest(); row["system_reward"]["xp"] = 100
    active = write(state, row); done = write(active, completed(active))
    assert done["character"]["level"] == 2 and done["level_up_freeze"] and not done["paused"]


@pytest.mark.parametrize("field", ["evolutions", "upgrades"])
def test_credit_preserves_all_existing_child_groups(engine, field):
    state = write(playing(engine), quest()); state = write(state, completed(state))
    base = {"id": "base", "name": "Warden's art", "rarity": "UNIQUE",
            "evolutions": [{"id": "e1", "name": "First evolution"}],
            "upgrades": [{"id": "u1", "name": "Existing upgrade"}],
            "imprints": [{"id": "i1", "name": "Background imprint"}]}
    state["abilities"] = [base]; parent = copy.deepcopy(base)
    parent[field].append({"id": "earned", "name": "Earned evolution"})
    delta = {"upsert": {"abilities": [parent]}, "spend_evolution_credit": {"ability_id": "base", "evolution_id": "earned"}}
    assert apply_changes(state, delta)["reward_credits"]["spent"] == ["earned"]
    parent["imprints"] = []
    with pytest.raises(EngineError): apply_changes(state, delta)


def test_real_saved_completion_is_atomic_and_reopens_without_paying_again(engine):
    from .conftest import commit
    game = ChatGame(engine); state = game.create("owner-a", "Persisted quest fixture", "saved-quest-create", True)
    state = game.update("owner-a", state["id"], "saved-name", state["version"], "Name", {"character": {"name": "Keeper", "class_name": "Warden"}})["campaign"]
    state = commit(engine, state, "confirm_chat_character")["campaign"]
    state = game.update("owner-a", state["id"], "saved-opening", state["version"], "Opening", {"opening_preview": "At the crossing."})["campaign"]
    state = commit(engine, state, "start_chat_adventure")["campaign"]
    active = game.update("owner-a", state["id"], "saved-quest", state["version"], "Quest", {"upsert": {"quest_log": [quest()]}})["campaign"]
    args = ("owner-a", state["id"], "saved-completion", active["version"], "Complete", {"upsert": {"quest_log": [completed(active)]}})
    done = game.update(*args)
    assert game.update(*args) == done
    assert engine.get_campaign("owner-a", state["id"])["funds"]["crowns"] == 50
