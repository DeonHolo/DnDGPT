"""Record an audited working-tree rule revision against the current checked-in source."""
import argparse
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import subprocess

APP = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(name, baseline_directory=None):
    if not re.fullmatch(r"[a-z0-9-]+\.json", name):
        raise ValueError("Use a revision filename, not a path")
    path = APP / "rules" / name
    if path.exists():
        raise ValueError("Preserve the existing revision audit")
    manifest_path = APP / "rules/integrity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    revision = {"id": name.removesuffix(".json"), "files": {}}
    for filename in ("rulebook-v1.0.txt", "rule-hardener.txt"):
        before = ((Path(baseline_directory) / filename).read_bytes() if baseline_directory else
                  subprocess.run(["rtk", "proxy", "git", "show", "HEAD:dndgpt-app/rules/" + filename],
                                 cwd=APP.parent, check=True, capture_output=True).stdout)
        after = (APP / "rules" / filename).read_bytes()
        entry = manifest[filename]
        assert sha(before) == entry["sha256"] and len(before) == entry["bytes"], "Baseline differs from the manifest"
        if before == after:
            continue
        old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
        edits = []
        for kind, a, b, c, d in SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
            if kind != "equal":
                edits.append({"new_start": sum(map(len, new[:c])), "before": b"".join(old[a:b]).decode(),
                              "after": b"".join(new[c:d]).decode()})
        restored = after
        for edit in reversed(edits):
            start = edit["new_start"]
            replacement = edit["after"].encode()
            assert restored[start:start + len(replacement)] == replacement
            restored = restored[:start] + edit["before"].encode() + restored[start + len(replacement):]
        assert restored == before
        revision["files"][filename] = edits
        entry.setdefault("revisions", []).append({"id": revision["id"], "source": name,
            "before_sha256": sha(before), "after_sha256": sha(after)})
        entry.update(sha256=sha(after), bytes=len(after))
    assert revision["files"], "No rule revision to record"
    encoded = (json.dumps(revision, ensure_ascii=False, indent=2) + "\n").encode()
    metadata = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    path.write_bytes(encoded)
    manifest_path.write_bytes(metadata)
    prototype = APP.parent / "dndgpt-system-rebirth/assets/prototype/rules"
    if prototype.exists():
        (prototype / name).write_bytes(encoded)
        (prototype / "integrity.json").write_bytes(metadata)
        for filename in revision["files"]:
            (prototype / filename).write_bytes((APP / "rules" / filename).read_bytes())
    print(json.dumps({"revision": revision["id"], "files": list(revision["files"]),
                      "unrelated_source_reversible": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filename")
    parser.add_argument("--baseline-directory")
    args = parser.parse_args()
    record(args.filename, args.baseline_directory)
