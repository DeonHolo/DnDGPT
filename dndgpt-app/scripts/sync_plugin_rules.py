"""Synchronize the plugin's rule references from the backend's canonical documents."""
import argparse
from pathlib import Path
from app.rule_sections import index_text

APP = Path(__file__).resolve().parents[1]
REFERENCES = APP.parent / "dndgpt-system-rebirth/skills/game-master/references"


def sync(check=False):
    pairs = [(APP / "rules" / name, REFERENCES / name)
             for name in ("rulebook-v1.0.txt", "rule-hardener.txt")]
    pairs.append((APP / "PRESENTATION.md", REFERENCES / "presentation.txt"))
    mismatches = [target for source, target in pairs if not target.exists() or target.read_bytes() != source.read_bytes()]
    if check and mismatches:
        raise SystemExit("Plugin references differ from backend source; run python -m scripts.sync_plugin_rules")
    if not check:
        for source, target in pairs:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    index = index_text((APP / "rules/rulebook-v1.0.txt").read_text(encoding="utf-8")).encode()
    index_path = REFERENCES / "rule-index.txt"
    if check and (not index_path.exists() or index_path.read_bytes() != index):
        raise SystemExit("Bundled rule index differs from canonical source; run python -m scripts.sync_plugin_rules")
    if not check:
        index_path.write_bytes(index)
    return len(mismatches)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(f"Plugin reference differences: {sync(args.check)}")
