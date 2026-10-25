import hashlib
from pathlib import Path


def test_delivered_search_script_matches_its_source():
    from scripts.build_dashboard_scripts import dashboard_source
    root = Path(__file__).resolve().parents[1] / "app"
    source = dashboard_source(root)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert (root / "dashboard_modules.min.js").read_text(encoding="utf-8").splitlines()[0] == "// Source SHA256: " + digest
