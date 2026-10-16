from pathlib import Path
import subprocess
import sys

from app.engine import Engine
from app.storage import Store


def test_online_backup_restore_and_no_overwrite(engine, state, tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts/backup_db.py"
    output = tmp_path / "backup.sqlite3"
    command = [sys.executable, str(script), str(engine.store.path), str(output)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    restored = Engine(Store(output))
    assert restored.get_campaign("owner-a", state["id"]) == state
    assert restored.audit("owner-a", state["id"])["integrity_valid"]
    before = output.read_bytes()
    assert subprocess.run(command, capture_output=True, timeout=20).returncode != 0
    assert output.read_bytes() == before
