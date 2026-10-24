"""Record the approved shared tooltip change against the checked-in source."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def record():
    revision_id = "tooltip-content-rows-2026-10-24"
    path = ROOT / "rules" / (revision_id + ".json")
    if path.exists():
        raise SystemExit("This revision is already recorded")
    manifest_path = ROOT / "rules/integrity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit = {"id": revision_id, "scope": "Approved tooltip internal rows and spacing only", "files": {}}
    for name in ("rulebook-v1.0.txt", "rule-hardener.txt"):
        before = subprocess.check_output(["rtk", "proxy", "git", "show", "HEAD:dndgpt-app/rules/" + name], cwd=ROOT.parent)
        after = (ROOT / "rules" / name).read_bytes()
        digest = lambda data: hashlib.sha256(data).hexdigest()
        assert digest(before) == manifest[name]["sha256"], "Checked-in source differs from integrity baseline"
        start = 0
        while start < min(len(before), len(after)) and before[start] == after[start]:
            start += 1
        end = 0
        while end < min(len(before), len(after)) - start and before[-end - 1] == after[-end - 1]:
            end += 1
        old = before[start:len(before) - end if end else len(before)]
        new = after[start:len(after) - end if end else len(after)]
        audit["files"][name] = [{"new_start": start, "before": old.decode(), "after": new.decode()}]
        manifest[name].setdefault("revisions", []).append({"id": revision_id, "source": path.name,
                                                         "before_sha256": digest(before), "after_sha256": digest(after)})
        manifest[name].update(bytes=len(after), sha256=digest(after))
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    record()
