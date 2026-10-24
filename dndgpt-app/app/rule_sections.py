"""Lossless, source-derived section access for the canonical rulebook."""
import re


AMENDMENTS = {
    "loading": "Rules loading and checklist precedence",
    "continuity": "Turn continuity and efficient resolution",
    "creation-order": "V1.0 surgical four-turn creation and in-chat continuation precedence",
    "direct-play": "Direct creation and advancement choices",
    "starting-gear": "Starting equipment by class rarity",
    "quest-journal": "Finite quests, System rewards and completion",
    "gallery": "Campaign Gallery and selected scene images",
    "story": "Story flavor, character identity and player voice",
    "generation": "Generation breadth, reaction roles and a playable world",
    "utility": "Utility usefulness and creative application",
    "class-craft": "Class concept diversity and writing craft",
    "world-preview": "World introduction: history, place and the player's footing",
    "reach": "Dexterity and player-facing reach",
    "clear-story": "Clear story language and names",
    "ancestry": "Player ancestry and nonhuman identity",
    "dashboard-writing": "Player-facing dashboard writing contract",
}

SUBSECTIONS = {
    "story-ui": "Compact Intelligent Story UI contract",
    "enemy-tactics": "Enemy identity, adaptive tactics and visible voice",
}

GAME_SECTIONS = {"sovereign-creation": "Sovereign creation and inherited rules",
                 "sovereign-progression": "Sovereign ownership and progression",
                 "sovereign-warfare": "Sovereign warfare and consequences",
                 "sovereign-dashboard": "Sovereign dashboard and efficient play"}


def sections(text):
    chapters = list(re.finditer(r"^# (\d+[A-Z]?)\. (.+)$", text, re.M))
    result = {}
    for index, match in enumerate(chapters):
        end = chapters[index + 1].start() if index + 1 < len(chapters) else len(text)
        result[match[1]] = {"title": match[2], "start": match.start(), "end": end}
    preface_end = chapters[0].start() if chapters else len(text)
    headings = list(re.finditer(r"^## (.+)$", text[:preface_end], re.M))
    optional = {key: title for key, title in GAME_SECTIONS.items() if any(m[1] == title for m in headings)}
    for key, title in {**AMENDMENTS, **optional}.items():
        matches = [(index, match) for index, match in enumerate(headings) if match[1] == title]
        if len(matches) != 1:
            raise ValueError(f"Missing or ambiguous canonical rule heading: {title}")
        index, match = matches[0]
        end = headings[index + 1].start() if index + 1 < len(headings) else preface_end
        result[key] = {"title": title, "start": match.start(), "end": end}
    for key, title in SUBSECTIONS.items():
        match = re.search(r"^## " + re.escape(title) + r"$", text, re.M)
        if match is None:
            raise ValueError(f"Missing canonical subsection: {title}")
        following = re.search(r"^#{1,2} ", text[match.end():], re.M)
        end = match.end() + following.start() if following else len(text)
        result[key] = {"title": title, "start": match.start(), "end": end}
    return result


def index_text(text):
    entries = sections(text)
    lines = ["# DnDGPT rule index", "",
             "Load the compact hardener first. Fetch relevant amendments and chapters before using their rules.",
             "Use read_rules(document='rulebook', section=KEY, offset=0); follow next_offset with the SAME section.",
             "Offsets are relative to the requested selection. Finishing a section is not a complete manual read.",
             "An omitted section still governs play; fetch it when the situation needs it.", "",
             "World preview: loading, world-preview, story, ancestry, clear-story, 4.",
             "Quests/rewards: quest-journal, 17, 24, 32. Random events: 32A. Saved illustrations: gallery.",
             "Class offers: creation-order, generation, utility, class-craft, reach, 5, 6, 7, 8. Read 9/10/11 for their creation stage.",
             "Utility offers and revisions: utility, generation, class-craft and the applicable acquisition chapter.",
             "Combat: enemy-tactics, reach, 12, 13, 14; also 15/16/29/30 when applicable. Reuse prepared enemy profiles.",
             "Advancement: 17, 18 and the applicable track in 19 through 22; interfaces 37/38. Chapter 19 includes standalone-passive eligibility and nested upgrade saves; 38 distinguishes base skills from dependent riders.",
             "Routine narrative/presentation: continuity and story-ui. Intelligent UI means story, inline glossary, colors and choices in chat; never a seven-chapter dump. Cache current sections; do not reload every turn.",
             "Story styling/tooltips: story-ui; 33 has the full glossary, 35 colors, 39 choices. Story flavor: story. Ability copy/details: dashboard-writing, 34. Dashboard architecture only: 38; full in-chat sheet only on explicit request.",
             "Creation completion/advancement: direct-play. Final creation saves Your story, outfit and opening together with begin_adventure=true; selections need no follow-up approval. Advancement continues automatically when all pending tracks are resolved.",
             "Starting outfit: starting-gear, 23, 27. Equipment: 23 through 28. Story/quests: 31, 32, 32A. Saves/compatibility: 40 through 42.", "",
             "## Current amendments"]
    if "sovereign-creation" in entries:
        lines.insert(2, "Selected game: sovereign-system. Keep game_id='sovereign-system' or the campaign_id on EVERY rules request/page. Begin with sovereign-creation; fetch sovereign-progression/warfare/dashboard when relevant.")
    for key in {**AMENDMENTS, **SUBSECTIONS}:
        item = entries[key]
        lines.append(f"{key} | {item['title']} | {item['end'] - item['start']} characters")
    for key in GAME_SECTIONS:
        if key in entries:
            item = entries[key]
            lines.append(f"{key} | {item['title']} | {item['end'] - item['start']} characters")
    lines += ["", "## Full chapters"]
    for key, item in entries.items():
        if key not in AMENDMENTS and key not in SUBSECTIONS and key not in GAME_SECTIONS:
            lines.append(f"{key} | {item['title']} | {item['end'] - item['start']} characters")
    return "\n".join(lines) + "\n"
