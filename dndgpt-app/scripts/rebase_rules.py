"""One-time edition relabeling; no mechanics or historical-edition changes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPLACEMENTS = [(b"V4.2", b"V1.0"), (b"VERSION 4.2", b"VERSION 1.0"),
                (b"Version 4.2", b"Version 1.0")]


def main():
    manifest = {}
    directories = [ROOT / "dndgpt-app/rules",
                   ROOT / "dndgpt-system-rebirth/skills/game-master/references"]
    for folder in directories:
        for name in ("rulebook-v4.2.txt", "rule-hardener.txt"):
            path = folder / name
            original = path.read_bytes()
            replacements = ([(b"V4.2-R1", b"V1.0")] if name == "rule-hardener.txt"
                            else REPLACEMENTS)
            updated = original
            for before, after in replacements:
                updated = updated.replace(before, after)
            target = path.with_name(name.replace("v4.2", "v1.0"))
            target.write_bytes(updated)
            if target != path:
                path.unlink()
            key = target.name
            entry = {"original_sha256": hashlib.sha256(original).hexdigest(),
                     "sha256": hashlib.sha256(updated).hexdigest(),
                     "original_bytes": len(original), "bytes": len(updated),
                     "replacements": [[a.decode(), b.decode()] for a, b in replacements]}
            if key in manifest:
                assert manifest[key] == entry, "Packaged and engine rules differ"
            manifest[key] = entry
    (ROOT / "dndgpt-app/rules/integrity.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
