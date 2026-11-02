"""Read the freely accessible official starter on demand; never ship its book text."""
import copy
from functools import lru_cache
import hashlib
from html.parser import HTMLParser
import re
from threading import Lock

import httpx

from .engine import fail

SOURCE_URL = "https://www.dndbeyond.com/sources/dnd/wa/frozen-sick"
STARTER_ID = "frozen-sick"
ADAPTATION = ("Run this published Wildemount adventure with the installed 2024 SRD rules. "
              "Keep its story, clues, locations, treasure and special adventure effects. "
              "Use installed 2024 creature entries where available; identify legacy or source-only "
              "stat blocks explicitly and retrieve their public reference rather than inventing one. "
              "Adjust encounters openly for Solo or the selected party. Cache retrieved sections.")
CHAPTERS = (
    ("FrozenSick", "Starting points"), ("StoryOverview", "Story overview"),
    ("MysteryinPalebankVillage", "Mystery in Palebank Village"),
    ("CroakerCave", "Croaker Cave"), ("JollyDwarf", "Jolly Dwarf"),
    ("TravelingtoEiselcross", "Traveling to Eiselcross"), ("Syrinlya", "Syrinlya"),
    ("IntotheWilds", "Into the wilds"), ("Salsvault", "Salsvault"),
    ("ConcludingtheAdventure", "Concluding the adventure"),
)
STARTER = {
    "id": STARTER_ID, "title": "Frozen Sick", "adventure_type": "published",
    "recommended": True, "ready_to_play": True, "source_required": False,
    "source_url": SOURCE_URL, "setting": "Wildemount (Exandria)",
    "starting_level": 1, "ending_level": 3, "version": 1,
    "summary": "Investigate a deadly illness in a northern village, then cross the frozen wilderness to find a cure.",
    "availability": "Free official adventure. The GM reads its source automatically; choose it and play.",
    "rules": "2024 rules adaptation of the published adventure",
}


def starter_entry(version=None):
    if version is not None and (type(version) is not int or version != 1):
        fail(404, "not_found", "Published starter version not found")
    content = {**STARTER, "credit": "Wizards of the Coast / D&D Beyond, Explorer's Guide to Wildemount",
               "sections": [{"id": key, "title": title} for key, title in CHAPTERS]}
    return {"id": STARTER_ID, "version": 1, "kind": "adventure", "game_id": "dnd-2024",
            "name": STARTER["title"], "content": copy.deepcopy(content)}


class SourceParser(HTMLParser):
    """Extract only the publisher's adventure article, keeping headings and lists."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(); self.depth = 0; self.skip = 0; self.parts = []; self.chapter = None; self.sections = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self.depth:
            if tag == "div" and "p-article-content" in attrs.get("class", "").split():
                self.depth = 1
            return
        if tag not in self.VOID:
            self.depth += 1
        if tag in {"script", "style"}:
            self.skip += 1
        if tag in {"h1", "h2"} and attrs.get("id") in dict(CHAPTERS):
            self.finish_section()
            self.chapter = attrs["id"]
        if tag in {"h1", "h2", "h3", "h4", "p", "li", "tr", "br"}:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("• ")
        if tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if not self.depth or tag in self.VOID:
            return
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)
        if tag in {"p", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")
        self.depth -= 1
        if not self.depth:
            self.finish_section(); self.chapter = None

    def handle_data(self, data):
        if self.depth and self.chapter and not self.skip:
            self.parts.append(re.sub(r"\s+", " ", data))

    def finish_section(self):
        if self.chapter:
            self.sections[self.chapter] = re.sub(r"\n\s*\n+", "\n\n", "".join(self.parts)).strip()
        self.parts = []


_source_lock = Lock()


@lru_cache(maxsize=1)
def source_sections():
    # One fixed HTTPS destination, no redirects/user URLs; bounded download and timeout.
    with httpx.Client(timeout=httpx.Timeout(12, connect=5), follow_redirects=False) as client:
        with client.stream("GET", SOURCE_URL) as response:
            response.raise_for_status()
            if "text/html" not in response.headers.get("content-type", ""):
                raise ValueError("Expected the publisher's HTML article")
            chunks = []; size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 2_000_000:
                    raise ValueError("Adventure source exceeded its download limit")
                chunks.append(chunk)
    parser = SourceParser(); parser.feed(b"".join(chunks).decode("utf-8")); parser.close()
    if set(parser.sections) != {key for key, _ in CHAPTERS} or any(len(text) < 100 for text in parser.sections.values()):
        raise ValueError("Published source is incomplete or its layout has changed")
    digest = hashlib.sha256("\n".join(parser.sections.values()).encode()).hexdigest()
    return parser.sections, digest


def read_starter(section_id=None, version=None):
    entry = starter_entry(version)
    base = {"id": STARTER_ID, "version": 1, "title": STARTER["title"], "setting": STARTER["setting"],
            "source_url": SOURCE_URL, "adaptation": ADAPTATION,
            "visibility": "GM reference; reveal only what the party discovers"}
    if section_id is None:
        return {**base, "summary": STARTER["summary"], "sections": entry["content"]["sections"],
                "first_sections": ["StoryOverview", "MysteryinPalebankVillage"]}
    if section_id not in dict(CHAPTERS):
        fail(404, "not_found", "Adventure section not found")
    try:
        with _source_lock:
            sections, digest = source_sections()
    except (httpx.HTTPError, ValueError, UnicodeError):
        fail(503, "adventure_source_unavailable", "The free official source is temporarily unavailable. Retry later or choose an original adventure; no upload is needed.")
    return {**base, "source_digest": digest,
            "section": {"id": section_id, "title": dict(CHAPTERS)[section_id], "content": sections[section_id]}}
