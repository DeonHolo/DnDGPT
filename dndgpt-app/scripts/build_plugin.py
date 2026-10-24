"""Build the existing private plugin from canonical source, without runtime data."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

import yaml

APP = Path(__file__).resolve().parents[1]
WORKSPACE = APP.parent
LICENSE_FILES = ("LICENSE", "LICENSE-CONTENT.md", "LICENSING.md", "LICENSES/CC-BY-4.0.txt", "docs/ARTWORK.md", "docs/ARTWORK_SOURCES.json", "docs/CREATIVITY_ENGINE.md")
TOP_FILES = ("README.md", "CODEX_HANDOFF.md", "CLIENT_ACCEPTANCE.md", "RULES_COVERAGE.md",
             "PRESENTATION.md", "DESIGN_SYSTEM.md", "INTELLIGENT_UI_RESEARCH.md", "AUTH0_SETUP.md",
             "LAUNCH_PLAN.md", "CREATION_WORKFLOW.md", "POWER_RUNTIME.md", "STARTING_BUILDS.md", "ITEM_RUNTIME.md", "OFFER_VALIDATION.md", "SUMMON_RUNTIME.md",
             "CLASS_PREPARATION.md", "CHAT_LED_PLAY.md", "FIRST_PLAY.md", "SKILL_HARDENING.md", "requirements.txt", "requirements-hosted.txt", "pytest.ini", "conftest.py", "Dockerfile", ".dockerignore", ".env.example")


def build(plugin, output=None):
    plugin = Path(plugin).resolve()
    manifest = json.loads((plugin / "plugin.json").read_text(encoding="utf-8"))
    version = manifest.get("version")
    if (manifest.get("name") != "dndgpt-system-rebirth" or not isinstance(version, str) or
            not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version)):
        raise ValueError("Unexpected plugin identity or release version")
    output = Path(output or WORKSPACE / f"dist/dndgpt-system-rebirth-{version}.zip").resolve()
    if output.is_relative_to(plugin):
        raise ValueError("Archive must be outside the plugin directory")
    openai = manifest["extensions"]["com.openai"]
    app_reference = openai.get("apps")
    if app_reference is not None:
        if app_reference != "./.app.json":
            raise ValueError("Private App reference must use ./.app.json")
        declarations = json.loads((plugin / ".app.json").read_text(encoding="utf-8"))
        apps = declarations.get("apps")
        if not isinstance(apps, dict) or not apps or set(declarations) != {"apps"}:
            raise ValueError("Invalid private App declarations")
        for entry in apps.values():
            if (not isinstance(entry, dict) or set(entry) != {"id"} or
                    not isinstance(entry["id"], str) or not re.fullmatch(
                        r"(?:asdk_app_|connector_|templated_apps_)[A-Za-z0-9][A-Za-z0-9_-]*",
                        entry["id"])):
                raise ValueError("Expected an actual App ID, not a plugin ID or URL")
    elif (plugin / ".app.json").exists():
        raise ValueError("Private App file has no manifest reference")
    interface = openai["interface"]
    if len(interface["shortDescription"]) > 30:
        raise ValueError("Plugin subtitle exceeds 30 characters")
    skill = plugin / "skills/game-master/SKILL.md"
    frontmatter = yaml.safe_load(skill.read_text(encoding="utf-8").split("---", 2)[1])
    if frontmatter.get("name") != "game-master" or not frontmatter.get("description"):
        raise ValueError("Invalid skill frontmatter")
    for name in ("rulebook-v1.0.txt", "rule-hardener.txt"):
        if (APP / "rules" / name).read_bytes() != (skill.parent / "references" / name).read_bytes():
            raise ValueError("Packaged rules differ from the engine's authoritative source")

    shutil.copyfile(APP / "PRESENTATION.md", skill.parent / "references/presentation.txt")

    legacy = {key: manifest[key] for key in ("name", "version", "description", "author")}
    legacy.update(interface=interface, keywords=manifest.get("keywords", []), skills="./skills")
    if app_reference is not None:
        legacy["apps"] = app_reference
    legacy_path = plugin / ".codex-plugin/plugin.json"
    legacy_path.parent.mkdir(exist_ok=True)
    legacy_path.write_text(json.dumps(legacy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    sources = [APP / name for name in TOP_FILES]
    for folder, suffixes in (("app", {".py", ".html", ".css", ".js"}), ("rules", {".txt", ".json"}),
                             ("scripts", {".py"}), ("tests", {".py", ".html"})):
        sources.extend(p for p in (APP / folder).iterdir() if p.is_file() and p.suffix in suffixes)
    sources.extend((APP / "app/assets").glob("*.avif"))
    sources.extend((APP / "app/assets/layouts").glob("*.svg"))
    sources.extend(p for p in (APP / "rules/sovereign").glob("*") if p.suffix in {".txt", ".json"})
    browser_report = APP / "test-results/browser.json"
    if browser_report.exists():
        sources.append(browser_report)
    files = [plugin / "plugin.json", legacy_path, skill,
             *(skill.parent / "references").glob("*.txt")]
    for name in LICENSE_FILES:
        target = plugin / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(WORKSPACE / name, target)
        files.append(target)
    for key in ("logo", "composerIcon", "logoDark", "composerIconDark"):
        if interface.get(key):
            asset = (plugin / interface[key]).resolve()
            if not asset.is_relative_to(plugin) or not asset.is_file():
                raise ValueError("Brand asset must be an existing file inside the plugin")
            if asset not in files:
                files.append(asset)
    if app_reference is not None:
        files.append(plugin / ".app.json")
    connection = plugin / "mcp.json"
    if connection.exists():
        # A real connection is added only after CLIENT_ACCEPTANCE has been completed.
        json.loads(connection.read_text(encoding="utf-8"))
        files.append(connection)
    for source in sources:
        target = plugin / "assets/prototype" / source.relative_to(APP)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files.append(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            name = path.relative_to(plugin).as_posix()
            if any(p in {".venv", "__pycache__", "data", ".test-tmp", ".browser-tmp"} for p in Path(name).parts):
                raise ValueError("Runtime material cannot be packaged")
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Archive integrity check failed")
        if "skills/game-master/references/rulebook-v4.2.txt" in archive.namelist():
            raise ValueError("Old rulebook path remains in release")
    return {"archive": str(output), "files": len(files), "version": manifest["version"],
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", type=Path, default=WORKSPACE / "dndgpt-system-rebirth")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.plugin, args.output), indent=2))
