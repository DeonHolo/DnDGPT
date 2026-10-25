"""Build dashboard modules. Node/npm is needed only by maintainers."""
import hashlib
from pathlib import Path
import shutil
import subprocess

SOURCES = ("campaign_tools.js", "journal_media.js", "sovereignty.js", "campaign_life.js",
           "campaign_focus.js", "dashboard_search.js")

def main():
    root = Path(__file__).resolve().parents[1] / "app"
    source = "\n;\n".join((root / name).read_text(encoding="utf-8") for name in SOURCES)
    compiler = shutil.which("npx")
    if not compiler:
        raise SystemExit("Install Node/npm to rebuild the search script")
    result = subprocess.run([compiler, "--yes", "terser@5.44.0", "--compress", "--mangle"],
                            input=source.encode("utf-8"), check=True, capture_output=True)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    (root / "dashboard_modules.min.js").write_bytes(b"// Source SHA256: " + digest.encode() + b"\n" + result.stdout)


if __name__ == "__main__":
    main()
