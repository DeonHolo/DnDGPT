"""Self-contained dashboard art: no external image requests from the MCP iframe."""
from base64 import b64encode
from functools import lru_cache
import json
from pathlib import Path

from .scenes import PALETTES, SCENES
from .version import APP_VERSION

HERE = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def dashboard_html():
    styles = []
    for scene in SCENES:
        variables = [f'--{key}:{value}' for key, value in PALETTES[scene["palette"]].items()]
        variables.append(f'--scene-opacity:{scene["opacity"]}')
        if asset := scene.get("asset"):
            data = b64encode((HERE / "assets" / asset).read_bytes()).decode("ascii")
            mime = "image/avif" if asset.endswith(".avif") else "image/webp"
            variables.append(f'--scene-art:url("data:{mime};base64,{data}")')
        styles.append(f'html[data-scene="{scene["id"]}"]{{' + ";".join(variables) + "}")
    catalog = json.dumps([{key: value for key, value in scene.items() if key not in
                          ("asset", "palette", "opacity")} for scene in SCENES], ensure_ascii=False)
    layout_art = []
    for name in ("ivy", "lantern", "orrery", "forge"):
        data = b64encode((HERE / "assets/layouts" / f"{name}.svg").read_bytes()).decode("ascii")
        layout_art.append(f'--layout-{name}:url("data:image/svg+xml;base64,{data}")')
    layouts = ":root{" + ";".join(layout_art) + "}\n" + (HERE / "layouts.css").read_text(encoding="utf-8")
    return ((HERE / "index.html").read_text(encoding="utf-8")
            .replace("__DNDGPT_UI_VERSION__", APP_VERSION)
            .replace("/* scene assets */", "\n".join(styles))
            .replace("/* dashboard layouts */", layouts)
            .replace("/* campaign tools styles */", (HERE / "campaign_tools.css").read_text(encoding="utf-8"))
            .replace("/* campaign tools script */", (HERE / "campaign_tools.js").read_text(encoding="utf-8"))
            .replace("/* journal media styles */", (HERE / "journal_media.css").read_text(encoding="utf-8"))
            .replace("/* journal media script */", (HERE / "journal_media.js").read_text(encoding="utf-8"))
            .replace("<!-- gallery panel -->", (HERE / "gallery.html").read_text(encoding="utf-8"))
            .replace('<script id="sceneCatalog" type="application/json">[]</script>',
                     '<script id="sceneCatalog" type="application/json">' + catalog.replace("<", "\\u003c") + '</script>'))
