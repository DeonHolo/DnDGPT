"""Consistent online SQLite backup; refuses to overwrite an existing destination."""
import argparse
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    target = args.destination.resolve()
    if target.exists() or source == target:
        parser.error("Destination must be a new file")
    target.parent.mkdir(parents=True, exist_ok=True)
    # SQLite URI prevents silently creating a missing input database.
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original:
        with sqlite3.connect(target) as backup:
            original.backup(backup)
            result = backup.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise RuntimeError("Backup integrity check failed")
    print(f"Verified SQLite backup: {target}")


if __name__ == "__main__":
    main()
