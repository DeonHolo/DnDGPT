"""Game identity and lossless, scoped rule composition. No campaign writes."""
from functools import lru_cache
import hashlib
import json
import re
from pathlib import Path

AGE = "age-of-convergence"
SOVEREIGN = "sovereign-system"
SOVEREIGN_LAWS = "sovereign-laws-2026-11-05"
DND = "dnd-2024"
DEFAULT_GAME = None
VERSION = "1.0"
GAMES = ({"id": DND, "name": "D&D 2024", "rules_version": "5.2.1"},
         {"id": AGE, "name": "Age of Convergence", "rules_version": VERSION},
         {"id": SOVEREIGN, "name": "Sovereign System", "rules_version": VERSION})
GAME_INTRODUCTIONS = {
    DND: "D&D's revised 2024 rules: classic classes, species, spells and character sheets. Choose a published adventure or an original D&D story, solo or with a party.",
    AGE: "A power-fantasy RPG where Earth meets other worlds. Discover generated classes and powers, rarity-ranked rewards and flexible personal builds.",
    SOVEREIGN: "An Age of Convergence power fantasy: play an extraordinary being with four core powers, a living domain and distinctive allies. Begin with its world's story, then choose a Class and grow through numbered levels.",
}
RULES = Path(__file__).resolve().parent.parent / "rules"


def game_id(state):
    return state.get("game_id", AGE)


def uses_sovereign_laws(state):
    return game_id(state) == SOVEREIGN and state.get("rules_profile") == SOVEREIGN_LAWS


def rules_version(value):
    return "5.2.1" if value == DND else VERSION


def validate_game(value, version=None):
    if type(value) is not str or value not in {row["id"] for row in GAMES} or version is not None and version != rules_version(value):
        raise ValueError("Choose dnd-2024 (SRD 5.2.1), age-of-convergence or sovereign-system (1.0)")
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


@lru_cache(maxsize=8)
def rule_source(selected=AGE, document="rulebook", profile=None):
    validate_game(selected)
    if document not in {"rulebook", "hardener"}:
        raise ValueError("Choose rulebook or hardener")
    if selected == DND:
        from .dnd_reference import rules_source
        return rules_source(document)
    if selected == SOVEREIGN and profile == SOVEREIGN_LAWS:
        data = (RULES / "sovereign" / "laws" / (document + ".txt")).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        return {"content": data.decode("utf-8"), "source_sha256": digest,
                "base_sha256": digest, "replacements": []}
    path = RULES / ("rulebook-v1.0.txt" if document == "rulebook" else "rule-hardener.txt")
    data = path.read_bytes()
    if selected == AGE:
        return {"content": data.decode("utf-8"), "source_sha256": hashlib.sha256(data).hexdigest(),
                "base_sha256": hashlib.sha256(data).hexdigest(), "replacements": []}
    overlay = json.loads((RULES / "sovereign/overlay.json").read_text(encoding="utf-8"))
    text, audit = compose(data.decode("utf-8"), overlay[document])
    from .sovereign_rules import compose_personal_rules, compose_embodied_rules
    text, personal_audit = compose_personal_rules(text, document)
    audit.extend(personal_audit)
    text, embodied_audit = compose_embodied_rules(text, document)
    audit.extend(embodied_audit)
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
