"""Game identity and lossless, scoped rule composition. No campaign writes."""
from functools import lru_cache
import hashlib
import json
import re
from pathlib import Path

AGE = "age-of-convergence"
SOVEREIGN = "sovereign-system"
VERSION = "1.0"
GAMES = ({"id": AGE, "name": "Age of Convergence", "rules_version": VERSION},
         {"id": SOVEREIGN, "name": "Sovereign System", "rules_version": VERSION})
RULES = Path(__file__).resolve().parent.parent / "rules"


def game_id(state):
    return state.get("game_id", AGE)


def validate_game(value, version=VERSION):
    if type(value) is not str or value not in {row["id"] for row in GAMES} or version != VERSION:
        raise ValueError("Choose age-of-convergence or sovereign-system, rules version 1.0")
    return value


def compose(base, operations):
    """Exact anchors fail closed if a shared-source edit needs overlay review."""
    result, audit = base, []
    for row in operations:
        old, new, count = row["old"], row["new"], row.get("count", 1)
        if not old or result.count(old) != count:
            raise ValueError("Sovereign rules overlay anchor changed: " + row["id"])
        locations = [match.start() for match in re.finditer(re.escape(old), result)]
        edits = [{"new_start": start + index * (len(new) - len(old)), "old": old, "new": new}
                 for index, start in enumerate(locations)]
        result = result.replace(old, new)
        audit.append({"id": row["id"], "count": count, "old": old, "new": new, "edits": edits})
    return result, audit


@lru_cache(maxsize=4)
def rule_source(selected=AGE, document="rulebook"):
    validate_game(selected)
    if document not in {"rulebook", "hardener"}:
        raise ValueError("Choose rulebook or hardener")
    path = RULES / ("rulebook-v1.0.txt" if document == "rulebook" else "rule-hardener.txt")
    data = path.read_bytes()
    if selected == AGE:
        return {"content": data.decode("utf-8"), "source_sha256": hashlib.sha256(data).hexdigest(),
                "base_sha256": hashlib.sha256(data).hexdigest(), "replacements": []}
    overlay = json.loads((RULES / "sovereign/overlay.json").read_text(encoding="utf-8"))
    text, audit = compose(data.decode("utf-8"), overlay[document])
    module = (RULES / ("sovereign/system.txt" if document == "rulebook" else "sovereign/checklist.txt")).read_text(encoding="utf-8")
    if document == "rulebook":
        # The module remains in the preface, before the unchanged numbered chapters.
        marker = "## V1.0 surgical-amendment integrity and precedence"
        if text.count(marker) != 1:
            raise ValueError("Shared rulebook preface anchor changed")
        text = text.replace(marker, module + "\n\n" + marker, 1)
    else:
        text = module + "\n\n" + text
    return {"content": text, "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "base_sha256": hashlib.sha256(data).hexdigest(), "replacements": audit}
