"""A pre-program saved draft must keep its original byte-based integrity proof."""
import hashlib
import json

from app import creation_codec as codec
from app.creation_repository import CreationRepository, digest
from app.rules import Dice
from app.storage import Store, canonical
from .test_creation_repository import commit, prepare_board, start


def test_pre_program_draft_inspection_and_next_selection_preserve_old_receipts(tmp_path):
    store = Store(tmp_path / "legacy-draft.sqlite3")
    store.initialize()
    repository = CreationRepository(store, Dice(lambda _: 0))
    draft = start(repository)
    draft = commit(repository, draft, "allocate_luck", {"points": 0})
    draft = prepare_board(repository, draft, "classes")
    # Reproduce the last released draft schema: these fields did not exist.
    with store.transaction() as db:
        row = db.execute("SELECT data FROM creation_drafts_v1 WHERE id=?", (draft["id"],)).fetchone()
        legacy = json.loads(row["data"])
        legacy["draft"].pop("loadout")
        legacy["draft"].pop("class_review")
        legacy["draft"].pop("class_context")
        for board in legacy["draft"]["boards"]:
            for offer in board["offers"]:
                for power in offer["abilities"]:
                    power.pop("program")
        encoded = canonical(legacy)
        last = db.execute("SELECT * FROM creation_events_v1 WHERE draft_id=? ORDER BY number DESC LIMIT 1",
                          (draft["id"],)).fetchone()
        event = json.loads(last["event"])
        event["draft_sha256"] = digest(legacy)
        event_text = canonical(event)
        event_hash = hashlib.sha256((last["previous_hash"] + event_text).encode()).hexdigest()
        db.execute("UPDATE creation_drafts_v1 SET data=? WHERE id=?", (encoded, draft["id"]))
        db.execute("UPDATE creation_events_v1 SET event=?, hash=? WHERE draft_id=? AND number=?",
                   (event_text, event_hash, draft["id"], draft["version"]))

    def forbidden(_):
        raise AssertionError("Legacy inspection/selection must not reroll")

    reopened = CreationRepository(Store(store.path), Dice(forbidden))
    # Decoding adds optional defaults; hashing that new object would falsely fail.
    assert canonical(codec.encode(codec.decode(legacy))) != encoded
    inspected = reopened.get_draft("owner-a", draft["id"])["draft"]
    assert inspected["phase"] == "class"
    assert inspected["board_programs"]["classes"]["programs_validated"] is False
    assert len(inspected["board_programs"]["classes"]["issues"]) == 5
    assert reopened.audit("owner-a", draft["id"], show_rolls=True)["integrity_valid"]
    with store.transaction() as db:
        assert db.execute("SELECT data FROM creation_drafts_v1 WHERE id=?", (draft["id"],)).fetchone()["data"] == encoded
    previous = reopened.audit("owner-a", draft["id"], show_rolls=True)["events"]
    selected = commit(reopened, draft, "choose_class", {"candidate_id": "classes-candidate-0"})
    assert selected["phase"] == "signatures_titles"
    audit = reopened.audit("owner-a", draft["id"], show_rolls=True)
    assert audit["integrity_valid"] and audit["events"][:-1] == previous
