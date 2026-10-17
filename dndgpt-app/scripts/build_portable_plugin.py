"""Build a portable release with the hosted MCP endpoint, without account bindings."""
import argparse
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from scripts.build_plugin import WORKSPACE, build

HOSTED_MCP = "https://dndgpt-deonholo.fra.appwrite.run/mcp"


def build_portable(output):
    original = WORKSPACE / "dndgpt-system-rebirth"
    with TemporaryDirectory(prefix="dndgpt-release-") as temporary:
        plugin = Path(temporary) / "dndgpt-system-rebirth"
        for name in ("skills", "brand"):
            shutil.copytree(original / name, plugin / name)
        manifest = json.loads((original / "plugin.json").read_text(encoding="utf-8"))
        manifest["extensions"]["com.openai"].pop("apps", None)
        (plugin / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        connection = {"mcpServers": {"dndgpt": {"type": "streamable-http", "url": HOSTED_MCP}}}
        (plugin / "mcp.json").write_text(json.dumps(connection, indent=2) + "\n", encoding="utf-8")
        return build(plugin, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=WORKSPACE / "dist/dndgpt-portable.zip")
    args = parser.parse_args()
    print(json.dumps(build_portable(args.output), indent=2))
