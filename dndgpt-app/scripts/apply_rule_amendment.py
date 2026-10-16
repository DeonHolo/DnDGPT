"""Apply the user-authorized additive ability-quality amendment without normalizing source bytes."""
import hashlib
import json
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
NAME = 'skill-originality-v1.0.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def apply():
    amendment = json.loads((APP / 'rules' / NAME).read_text(encoding='utf-8'))
    manifest_path = APP / 'rules/integrity.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    report = APP / 'test-results/skill-hardening-integrity.json'
    assert not report.exists(), 'Preserve prior amendment audit'
    evidence = {'amendment': amendment['id'], 'edition': '1.0', 'files': {},
                'campaigns_changed': False, 'historical_archives_changed': False}
    prepared = []
    for name, edits in amendment['files'].items():
        assert name in {'rulebook-v1.0.txt', 'rule-hardener.txt'}
        entry = manifest[name]
        data = (APP / 'rules' / name).read_bytes()
        assert digest(data) == entry['sha256'] and len(data) == entry['bytes']
        if any(a['id'] == amendment['id'] for a in entry.get('amendments', [])):
            raise ValueError('Amendment already applied; preserve the existing audit')
        before = data
        # The supplied rulebook is LF; its companion is CRLF. Adapt only new
        # insertion data to each file, never normalize the preserved source.
        newline = '\r\n' if data.count(b'\r\n') == data.count(b'\n') else '\n'
        for edit in edits:
            for key in edit:
                edit[key] = edit[key].replace('\r\n', '\n').replace('\n', newline)
        entry.setdefault('edition_sha256', digest(before))
        entry.setdefault('edition_bytes', len(before))
        for edit in edits:
            assert set(edit) in ({'before', 'text'}, {'after', 'text'})
            anchor = edit.get('before', edit.get('after')).encode('utf-8')
            inserted = edit['text'].encode('utf-8')
            assert data.count(anchor) == 1, 'Ambiguous insertion anchor'
            assert inserted and inserted not in data
            at = data.index(anchor) + (len(anchor) if 'after' in edit else 0)
            data = data[:at] + inserted + data[at:]
        restored = data
        for edit in reversed(edits):
            inserted = edit['text'].encode('utf-8')
            assert restored.count(inserted) == 1
            restored = restored.replace(inserted, b'', 1)
        assert restored == before, 'Unrelated source bytes changed'
        original = restored
        for old, new in reversed(entry['replacements']):
            original = original.replace(new.encode(), old.encode())
        assert digest(original) == entry['original_sha256']
        assert len(original) == entry['original_bytes']
        copies = [APP / 'rules' / name,
                  ROOT / 'dndgpt-system-rebirth/skills/game-master/references' / name,
                  ROOT / 'dndgpt-system-rebirth/assets/prototype/rules' / name]
        for path in copies:
            assert path.read_bytes() == before
        entry.update(sha256=digest(data), bytes=len(data))
        entry.setdefault('amendments', []).append({'id': amendment['id'], 'source': NAME,
                                                   'insertions': len(edits)})
        evidence['files'][name] = {'before_sha256': digest(before), 'sha256': digest(data),
            'before_bytes': len(before), 'bytes': len(data), 'insertions': len(edits),
            'all_unrelated_bytes_preserved': True, 'original_reconstructed_sha256': digest(original)}
        prepared.append((copies, data))
    for copies, data in prepared:
        for path in copies:
            path.write_bytes(data)
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
    manifest_path.write_bytes(manifest_bytes)
    amendment_bytes = (json.dumps(amendment, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    (APP / 'rules' / NAME).write_bytes(amendment_bytes)
    packaged = ROOT / 'dndgpt-system-rebirth/assets/prototype/rules'
    (packaged / 'integrity.json').write_bytes(manifest_bytes)
    (packaged / NAME).write_bytes(amendment_bytes)
    report.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(evidence))


if __name__ == '__main__':
    apply()
