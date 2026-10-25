"""Build dashboard modules. Node/npm is needed only by maintainers."""
import hashlib
import re
from pathlib import Path
import shutil
import subprocess

SOURCES = ("combat_roster.js", "campaign_tools.js", "journal_media.js", "sovereignty.js", "campaign_life.js",
           "campaign_focus.js", "dashboard_search.js")

def dashboard_source(root):
    core = re.findall(r"<script>\s*([\s\S]*?)</script>", (root / "index.html").read_text(encoding="utf-8"))
    if len(core) != 1:
        raise ValueError("Expected one dashboard application script")
    modules = "\n;\n".join((root / name).read_text(encoding="utf-8") for name in SOURCES)
    source = core[0].replace("/* campaign tools script */", modules)
    return re.sub(r"/\* (?:journal media|sovereign|campaign life|dashboard search) script \*/", "", source)

def main():
    root = Path(__file__).resolve().parents[1] / "app"
    source = dashboard_source(root)
    compiler = shutil.which("npx")
    if not compiler:
        raise SystemExit("Install Node/npm to rebuild the search script")
    result = subprocess.run([compiler, "--yes", "terser@5.44.0", "--compress", "--mangle"],
                            input=source.encode("utf-8"), check=True, capture_output=True)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    (root / "dashboard_modules.min.js").write_bytes(b"// Source SHA256: " + digest.encode() + b"\n" + result.stdout)


if __name__ == "__main__":
    main()
