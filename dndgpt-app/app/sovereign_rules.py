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


def compose_embodied_rules(text, document):
    from .game_profiles import RULES, compose
    from .rule_sections import sections
    root = RULES / "sovereign/embodied"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if document == "hardener":
        if hashlib.sha256(text.encode()).hexdigest() != manifest["hardener_sha256"]:
            raise ValueError("Sovereign embodied hardener source changed")
        return compose(text, [{"id": "embodied-hardener", "old": text,
                               "new": (root / "hardener.txt").read_text(encoding="utf-8")}])
    content = json.loads((root / "sections.json").read_text(encoding="utf-8"))
    audit = []
    for entry in manifest["rulebook"]:
        selected = sections(text)[entry["section"]]
        old = text[selected["start"]:selected["end"]]
        if hashlib.sha256(old.encode()).hexdigest() != entry["source_sha256"]:
            raise ValueError("Sovereign embodied source changed: " + entry["section"])
        new = content[entry["section"]].rstrip() + ("\n" if selected["end"] == len(text) else "\n\n")
        text, edits = compose(text, [{"id": "embodied-" + entry["section"], "old": old, "new": new}])
        audit.extend(edits)
    text, edits = compose(text, manifest["preface"])
    return text, audit + edits
