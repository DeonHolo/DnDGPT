import json
from pathlib import Path
import shutil
import zipfile

import pytest

from scripts.build_plugin import APP, LICENSE_FILES, build


def test_release_contains_canonical_source_and_complete_rules_without_runtime_data(tmp_path):
    original = APP.parent / "dndgpt-system-rebirth"
    plugin_version = json.loads((original / "plugin.json").read_text())["version"]
    plugin = tmp_path / "dndgpt-system-rebirth"
    shutil.copytree(original / "skills", plugin / "skills")
    shutil.copytree(original / "brand", plugin / "brand")
    shutil.copyfile(original / "plugin.json", plugin / "plugin.json")
    binding = original / ".app.json"
    declarations = (json.loads(binding.read_text()) if binding.exists() else
                    {"apps": {"engine": {"id": "asdk_app_packaging_fixture"}}})
    (plugin / ".app.json").write_text(json.dumps(declarations))
    output = tmp_path / "release.zip"
    result = build(plugin, output)
    assert result["version"] == plugin_version
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in names)
        assert not any(name.endswith((".sqlite3", ".db", ".pyc", ".env")) for name in names)
        assert not any(part in {".venv", "__pycache__", ".test-tmp", ".browser-tmp"}
                       for name in names for part in Path(name).parts)
        for name in LICENSE_FILES:
            assert archive.read(name) == (APP.parent / name).read_bytes()
        manifest = json.loads(archive.read("plugin.json"))
        legacy = json.loads(archive.read(".codex-plugin/plugin.json"))
        assert manifest["version"] == legacy["version"] == plugin_version
        assert manifest["extensions"]["com.openai"]["interface"] == legacy["interface"]
        for key in ("logo", "composerIcon"):
            asset = manifest["extensions"]["com.openai"]["interface"][key].removeprefix("./")
            assert archive.read(asset) == (original / asset).read_bytes()
        assert manifest["extensions"]["com.openai"]["apps"] == legacy["apps"] == "./.app.json"
        assert json.loads(archive.read(".app.json")) == declarations
        assert archive.read("skills/game-master/references/presentation.txt") == (APP / "PRESENTATION.md").read_bytes()
        assert archive.read("assets/prototype/PRESENTATION.md") == (APP / "PRESENTATION.md").read_bytes()
        assert "assets/prototype/INTELLIGENT_UI_RESEARCH.md" in names
        for name in ("rulebook-v1.0.txt", "rule-hardener.txt"):
            authoritative = (APP / "rules" / name).read_bytes()
            assert archive.read("skills/game-master/references/" + name) == authoritative
            assert archive.read("assets/prototype/rules/" + name) == authoritative
        for source in (APP / "app").iterdir():
            if source.is_file() and source.suffix in {".py", ".html"}:
                assert archive.read("assets/prototype/app/" + source.name) == source.read_bytes()
        for source in (APP / "app/assets").glob("*.webp"):
            assert archive.read("assets/prototype/app/assets/" + source.name) == source.read_bytes()
        assert "skills/game-master/references/rulebook-v4.2.txt" not in names


@pytest.mark.parametrize("app_id", ["plugin_asdk_app_example", "https://example.com/mcp", "asdk_app_"])
def test_private_dependency_rejects_plugin_ids_urls_and_incomplete_ids(tmp_path, app_id):
    plugin = tmp_path / "candidate"
    plugin.mkdir()
    shutil.copyfile(APP.parent / "dndgpt-system-rebirth/plugin.json", plugin / "plugin.json")
    (plugin / ".app.json").write_text(json.dumps({"apps": {"engine": {"id": app_id}}}))
    with pytest.raises(ValueError, match="actual App ID"):
        build(plugin, tmp_path / "invalid.zip")
    assert not (tmp_path / "invalid.zip").exists()


def test_undeclared_app_file_is_not_silently_dropped(tmp_path):
    plugin = tmp_path / "candidate"
    plugin.mkdir()
    manifest = json.loads((APP.parent / "dndgpt-system-rebirth/plugin.json").read_text())
    del manifest["extensions"]["com.openai"]["apps"]
    (plugin / "plugin.json").write_text(json.dumps(manifest))
    (plugin / ".app.json").write_text('{"apps": {}}')
    with pytest.raises(ValueError, match="no manifest reference"):
        build(plugin, tmp_path / "invalid.zip")
