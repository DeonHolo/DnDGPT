"""Synchronize the plugin's rule references from the backend's canonical documents."""
import argparse
from pathlib import Path

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
    return len(mismatches)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(f"Plugin reference differences: {sync(args.check)}")
