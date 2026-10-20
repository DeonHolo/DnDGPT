"""Audit visible facts in synthetic saves; this does not measure model recall."""
import argparse
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.chat_game import ChatGame
from app.continuity import model_view
from app.engine import Engine
from app.storage import Store


FACTS = {
    "old_promise": ("The ferry keeper", "Mara promised passage after the bronze bell was returned."),
    "world_rule": ("The flooded route", "The east causeway is impassable at high tide."),
    "corrected_fact": ("The current password", "The current gate password is reed-lantern."),
    "pinned_promise": ("A saved commitment", "Iven will repair the west bridge before dawn."),
    "eighth_commitment": ("A commitment beyond the brief's first four", "Sela owes the player three silver hooks."),
    "ability_limit": ("An actual summon rule", "The moth remains when its summoner is unconscious."),
    "active_quest": ("The active objective", "Recover the bronze bell without breaking its seal."),
    "recent_event": ("The latest action", "The player reached the sheltered quay."),
}
QUESTIONS = {
    "old_promise": "We return the bronze bell to Mara. What did she promise us?",
    "world_rule": "It is high tide. Can we use the east causeway?",
    "corrected_fact": "What is the current gate password?",
    "pinned_promise": "When did Iven agree to finish the bridge?",
    "eighth_commitment": "What does Sela owe us?",
    "ability_limit": "My character falls unconscious. Does the moth vanish?",
    "active_quest": "What restriction applies when recovering the bell?",
    "recent_event": "Where did the last action leave us?",
}
OWNER = "synthetic-continuity-audit"


def save(game, state, changes):
    return game.update(OWNER, state["id"], f"context-audit-{state['version']:05d}",
                       state["version"], "Synthetic continuity fixture", changes)["campaign"]


def build_campaign(engine, saves=100):
    game = ChatGame(engine)
    state = game.create(OWNER, "Synthetic continuity audit", "create-context-audit", True)
    state = save(game, state, {
        "world": {"summary": "A tidal town with a ferry and a guarded causeway.",
                  "routes": {"causeway": FACTS["world_rule"][1]},
                  "gate": {"password": FACTS["corrected_fact"][1]}},
        "continuity": {"scene": "The sheltered quay", "pending_decision": "Return the bell or rest?",
                       "npc_commitments": [FACTS["pinned_promise"][1]] +
                           [f"Witness {i} will wait at the quay." for i in range(6)] + [FACTS["eighth_commitment"][1]],
                       "unresolved_threads": ["The ferryman has not received the bell."]},
        "upsert": {
            "world_log": [{"id": "old-promise", "text": FACTS["old_promise"][1]},
                          {"id": "old-password", "text": "The old gate password was ash-drift."}],
            "abilities": [{"id": "moth", "name": "Watchful Moth", "mechanics": FACTS["ability_limit"][1]}],
            "quest_log": [{"id": "bell", "name": "Return the bell", "status": "active",
                           "description": FACTS["active_quest"][1]}],
            "generation_ledger": [{"id": "first-offer", "text": "An old unselected class offer."}],
        },
    })
    original = copy.deepcopy(state)
    for index in range(saves):
        state = save(game, state, {
            "continuity": {"last_action": FACTS["recent_event"][1]},
            "upsert": {"world_log": [{"id": f"later-{index}",
                "text": f"Routine recorded event {index}: " + "The tide laps against the quay. " * 5}],
                "generation_ledger": [{"id": f"review-{index}", "text": "Synthetic record " + str(index)}]},
        })
    return original, state


def audit(state):
    views = {name: model_view(state, name) for name in ("full", "turn", "resume")}
    encoded = {name: json.dumps(view, ensure_ascii=False) for name, view in views.items()}
    rows = [{"id": key, "description": description,
             "visible": {name: fact in text for name, text in encoded.items()}}
            for key, (description, fact) in FACTS.items()]
    return {"provenance": "synthetic_local_save_chain", "scope": "Fact availability, not model recall or played turns",
            "model_calls": 0, "player_campaigns_accessed": 0, "version": state["version"],
            "world_log_entries": len(state["world_log"]), "facts": rows,
            "visible_facts": {name: sum(row["visible"][name] for row in rows) for name in views},
            "json_bytes": {name: len(text.encode()) for name, text in encoded.items()},
            "requires_model_evaluation": True}


def prompts(state):
    instruction = ("This is a synthetic read-only continuity test, not an actual game. Do not use any plugins, "
                   "roll, save or change anything. Use only the supplied save. Answer the questions briefly, "
                   "numbered in order. If a needed fact is missing, request the full save instead of guessing.\n")
    questions = "\n".join(f"{i}. {question}" for i, question in enumerate(QUESTIONS.values(), 1))
    questions += "\n9. How many children does Mara have?"
    return {name: instruction + "\nSAVE:\n" + json.dumps(model_view(state, name), ensure_ascii=False) +
            "\nQUESTIONS:\n" + questions for name in ("full", "turn")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saves", type=int, default=100, choices=range(10, 301), metavar="10..300")
    parser.add_argument("--output", type=Path, default=Path("test-results/continuity-context-audit.json"))
    args = parser.parse_args()
    with TemporaryDirectory(prefix="dndgpt-continuity-") as folder:
        store = Store(Path(folder) / "fixture.sqlite3")
        store.initialize()
        _, state = build_campaign(Engine(store), args.saves)
        report = audit(state)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for name, prompt in prompts(state).items():
            args.output.with_name(f"{args.output.stem}-{name}-prompt.txt").write_text(prompt, encoding="utf-8")
        print(json.dumps({"saves": args.saves, "facts_visible": report["visible_facts"],
                          "model_calls": 0, "player_campaigns_accessed": 0}))


if __name__ == "__main__":
    main()
