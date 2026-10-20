"""Lossless, source-derived section access for the canonical rulebook."""
import re


AMENDMENTS = {
    "loading": "Rules loading and checklist precedence",
    "creation-order": "V1.0 surgical four-turn creation and in-chat continuation precedence",
    "story": "Story flavor, character identity and player voice",
    "generation": "Generation breadth, reaction roles and a playable world",
    "utility": "Utility usefulness and creative application",
    "class-craft": "Class concept diversity and writing craft",
    "world-preview": "World introduction: history, place and the player's footing",
    "reach": "Dexterity and player-facing reach",
    "dashboard-writing": "Player-facing dashboard writing contract",
}


def sections(text):
    chapters = list(re.finditer(r"^# (\d+[A-Z]?)\. (.+)$", text, re.M))
    result = {}
    for index, match in enumerate(chapters):
        end = chapters[index + 1].start() if index + 1 < len(chapters) else len(text)
        result[match[1]] = {"title": match[2], "start": match.start(), "end": end}
    preface_end = chapters[0].start() if chapters else len(text)
    headings = list(re.finditer(r"^## (.+)$", text[:preface_end], re.M))
    for key, title in AMENDMENTS.items():
        matches = [(index, match) for index, match in enumerate(headings) if match[1] == title]
        if len(matches) != 1:
            raise ValueError(f"Missing or ambiguous canonical rule heading: {title}")
        index, match = matches[0]
        end = headings[index + 1].start() if index + 1 < len(headings) else preface_end
        result[key] = {"title": title, "start": match.start(), "end": end}
    return result


def index_text(text):
    entries = sections(text)
    lines = ["# DnDGPT rule index", "",
             "Load the compact hardener first. Fetch relevant amendments and chapters before using their rules.",
             "Use read_rules(document='rulebook', section=KEY, offset=0); follow next_offset with the SAME section.",
             "Offsets are relative to the requested selection. Finishing a section is not a complete manual read.",
             "An omitted section still governs play; fetch it when the situation needs it.", "",
             "World preview: loading, world-preview, story, 4.",
             "Class offers: creation-order, generation, utility, class-craft, reach, 5, 6, 7, 8. Read 9/10/11 for their creation stage.",
             "Utility offers and revisions: utility, generation, class-craft and the applicable acquisition chapter.",
             "Combat: reach, 12, 13, 14; also 15/16/29/30 when applicable.",
             "Advancement: 17, 18 and the applicable track in 19 through 22; interfaces 37/38.",
             "Presentation: story, dashboard-writing, 33, 34, 35, 38, 39. Chapter 33 contains the full inline glossary specification.",
             "Equipment: 23 through 28. Story/quests: 31, 32, 32A. Saves/compatibility: 40 through 42.", "",
             "## Current amendments"]
    for key in AMENDMENTS:
        item = entries[key]
        lines.append(f"{key} | {item['title']} | {item['end'] - item['start']} characters")
    lines += ["", "## Full chapters"]
    for key, item in entries.items():
        if key not in AMENDMENTS:
            lines.append(f"{key} | {item['title']} | {item['end'] - item['start']} characters")
    return "\n".join(lines) + "\n"
