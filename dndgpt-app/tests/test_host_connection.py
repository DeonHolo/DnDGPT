"""The real browser bootstrap must negotiate hosts, including hybrid bridges."""
from pathlib import Path
import shutil
import subprocess

import pytest


def test_dashboard_bootstrap_protocol_hosts_and_partial_preferences():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the isolated JavaScript bootstrap regression")
    result = subprocess.run([node, str(Path(__file__).with_name("host_connection_unit.cjs"))],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
