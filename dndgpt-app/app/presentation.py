"""Compact dashboard resource with separately cached, first-party background art."""
from base64 import b64encode
from functools import lru_cache
import json
import re
from pathlib import Path

from .scenes import PALETTES, SCENES
from .version import APP_VERSION
from .artwork import artwork_url

HERE = Path(__file__).resolve().parent


@lru_cache(maxsize=8)
def dashboard_html(asset_base_url=""):
    styles = []
    for scene in SCENES:
        variables = [f'--{key}:{value}' for key, value in PALETTES[scene["palette"]].items()]
        variables.append(f'--scene-opacity:{scene["opacity"]}')
        if asset := scene.get("asset"):
            variables.append('--scene-art:url(' + json.dumps(artwork_url(asset, asset_base_url)) + ')')
        styles.append(f'html[data-scene="{scene["id"]}"]{{' + ";".join(variables) + "}")
    catalog = json.dumps([{key: value for key, value in scene.items() if key not in
                          ("asset", "palette", "opacity")} for scene in SCENES], ensure_ascii=False)
    layout_art = []
    for name in ("ivy", "lantern", "orrery", "forge"):
        data = b64encode((HERE / "assets/layouts" / f"{name}.svg").read_bytes()).decode("ascii")
        layout_art.append(f'--layout-{name}:url("data:image/svg+xml;base64,{data}")')
    layouts = ":root{" + ";".join(layout_art) + "}\n" + (HERE / "layouts.css").read_text(encoding="utf-8")
    template = re.sub(r"(<script>)\s*[\s\S]*?(</script>)",
                      lambda match: match[1] + (HERE / "dashboard_modules.min.js").read_text(encoding="utf-8") + match[2],
                      (HERE / "index.html").read_text(encoding="utf-8"))
    return (template
            .replace("__DNDGPT_UI_VERSION__", APP_VERSION)
            .replace("/* scene assets */", "\n".join(styles))
            .replace("/* dashboard layouts */", layouts)
            .replace("/* campaign tools styles */", (HERE / "campaign_tools.css").read_text(encoding="utf-8"))
            .replace("/* journal media styles */", (HERE / "journal_media.css").read_text(encoding="utf-8"))
            .replace("/* journal media script */", "")
            .replace("/* sovereign styles */", (HERE / "sovereignty.css").read_text(encoding="utf-8") + "\n" + (HERE / "dnd_sheet.css").read_text(encoding="utf-8"))
            .replace("/* sovereign script */", "")
            .replace("/* campaign life styles */", (HERE / "campaign_life.css").read_text(encoding="utf-8") + "\n" + (HERE / "campaign_focus.css").read_text(encoding="utf-8"))
            .replace("/* campaign life script */", "")
            .replace("/* dashboard search styles */", (HERE / "dashboard_search.css").read_text(encoding="utf-8"))
            .replace("/* dashboard search script */", "")
            .replace("<!-- dashboard search -->", (HERE / "dashboard_search.html").read_text(encoding="utf-8"))
            .replace("<!-- gallery panel -->", (HERE / "gallery.html").read_text(encoding="utf-8"))
            .replace('<script id="sceneCatalog" type="application/json">[]</script>',
                     '<script id="sceneCatalog" type="application/json">' + catalog.replace("<", "\\u003c") + '</script>'))
