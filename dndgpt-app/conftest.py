"""Keep pytest cleanup independent of the caller's working directory."""
from pathlib import Path

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    project = Path(__file__).resolve().parent
    target = Path(config.option.basetemp or project / ".test-tmp").resolve()
    live_runtime = project.parent / ".test-tmp" / "live-auth"
    if target == live_runtime or target in live_runtime.parents:
        raise pytest.UsageError("basetemp must not contain the live-auth runtime")
    config.option.basetemp = str(target)
