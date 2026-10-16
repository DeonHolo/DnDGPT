import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["rulebook-v1.0.txt", "rule-hardener.txt"])
def test_complete_rules_preserved_except_authorized_edition_labels_and_additions(name):
    manifest = json.loads((ROOT / "rules/integrity.json").read_text())
    entry = manifest[name]
    data = (ROOT / "rules" / name).read_bytes()
    assert len(data) == entry["bytes"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    original = data
    for amendment in reversed(entry.get('amendments', [])):
        # Only explicit additive revisions may be reversed; the original source
        # hash below still proves that no unrelated byte was changed or removed.
        assert amendment['source'] == 'skill-originality-v1.0.json'
        source = json.loads((ROOT / 'rules' / amendment['source']).read_text(encoding='utf-8'))
        assert source['id'] == amendment['id']
        edits = source['files'][name]
        assert len(edits) == amendment['insertions']
        for edit in reversed(edits):
            inserted = edit['text'].encode('utf-8')
            assert inserted and original.count(inserted) == 1
            original = original.replace(inserted, b'', 1)
    assert hashlib.sha256(original).hexdigest() == entry.get('edition_sha256', entry['sha256'])
    assert len(original) == entry.get('edition_bytes', entry['bytes'])
    for before, after in reversed(entry["replacements"]):
        original = original.replace(after.encode(), before.encode())
    assert hashlib.sha256(original).hexdigest() == entry["original_sha256"]
    assert len(original) == entry["original_bytes"]
    packaged = ROOT.parent / "dndgpt-system-rebirth/skills/game-master/references" / name
    if packaged.exists():
        assert packaged.read_bytes() == data


def test_no_model_api_dependency_or_client_in_engine():
    # Protect the architectural requirement that ordinary narration stays in chat.
    import ast
    for path in (ROOT / "app").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] not in {"openai", "anthropic"} for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in {"openai", "anthropic"}
        assert "api.openai.com" not in path.read_text(encoding="utf-8")
