"""Compose a creation App with the companion's existing local codex styles."""
from pathlib import Path


def html():
    folder = Path(__file__).parent
    companion = (folder / "index.html").read_text(encoding="utf-8")
    style = companion.split("<style>", 1)[1].split("</style>", 1)[0]
    return (folder / "creation.html").read_text(encoding="utf-8").replace("/* CODEX_STYLE */", style)
