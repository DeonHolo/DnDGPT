"""Replace only reviewed Sovereign sections; keep shared source byte-for-byte intact."""
import hashlib
import json


def compose_personal_rules(text, document):
    from .game_profiles import RULES, compose
    from .rule_sections import sections
    root = RULES / "sovereign/personal"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    audit = []
    for entry in manifest[document]:
        if document == "rulebook":
            selection = sections(text)[entry["section"]]
            old = text[selection["start"]:selection["end"]]
            if hashlib.sha256(old.encode()).hexdigest() != entry["source_sha256"]:
                raise ValueError("Sovereign personal rules source changed: " + entry["section"])
            new = (root / entry["file"]).read_text(encoding="utf-8").rstrip() + ("\n" if selection["end"] == len(text) else "\n\n")
        else:
            old, new = entry["old"], entry["new"]
        text, edits = compose(text, [{"id": "personal-" + entry.get("section", entry.get("id", "")),
                                      "old": old, "new": new}])
        audit.extend(edits)
    return text, audit
