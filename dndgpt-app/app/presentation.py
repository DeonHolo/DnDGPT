"""Self-contained dashboard art: no external image requests from the MCP iframe."""
from base64 import b64encode
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def dashboard_html():
    styles = []
    for theme, name in (("elderwood", "oakwood.webp"), ("moonkeep", "silent-isle.webp")):
        data = b64encode((HERE / "assets" / name).read_bytes()).decode("ascii")
        styles.append(f'html[data-scene="{theme}"]{{--scene-art:url("data:image/webp;base64,{data}")}}')
    return (HERE / "index.html").read_text(encoding="utf-8").replace("/* scene assets */", "\n".join(styles))
