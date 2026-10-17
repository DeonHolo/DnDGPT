"""Self-contained dashboard art: no external image requests from the MCP iframe."""
from base64 import b64encode
from functools import lru_cache
import json
from pathlib import Path

from .scenes import PALETTES, SCENES

HERE = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def dashboard_html():
    styles = []
    for scene in SCENES:
        variables = [f'--{key}:{value}' for key, value in PALETTES[scene["palette"]].items()]
        variables.append(f'--scene-opacity:{scene["opacity"]}')
        if asset := scene.get("asset"):
            data = b64encode((HERE / "assets" / asset).read_bytes()).decode("ascii")
            variables.append(f'--scene-art:url("data:image/webp;base64,{data}")')
        styles.append(f'html[data-scene="{scene["id"]}"]{{' + ";".join(variables) + "}")
    catalog = json.dumps([{key: value for key, value in scene.items() if key not in
                          ("asset", "palette", "opacity")} for scene in SCENES], ensure_ascii=False)
    return ((HERE / "index.html").read_text(encoding="utf-8")
            .replace("/* scene assets */", "\n".join(styles))
            .replace('<script id="sceneCatalog" type="application/json">[]</script>',
                     '<script id="sceneCatalog" type="application/json">' + catalog.replace("<", "\\u003c") + '</script>'))
