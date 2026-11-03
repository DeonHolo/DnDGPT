"""Pin reviewed Sovereign replacements against the pre-existing scoped source.

Development maintenance only. Re-run deliberately after reviewing upstream edits;
normal builds verify these pins and never silently update them.
"""
import hashlib
import json
import re
from pathlib import Path

from app.game_profiles import RULES, compose
from app.rule_sections import sections
from app.sovereign_rules import compose_personal_rules


def previous(document):
    name = "rulebook-v1.0.txt" if document == "rulebook" else "rule-hardener.txt"
    text = (RULES / name).read_text(encoding="utf-8")
    overlay = json.loads((RULES / "sovereign/overlay.json").read_text(encoding="utf-8"))
    text, _ = compose(text, overlay[document])
    return compose_personal_rules(text, document)[0]


def pin():
    root = RULES / "sovereign/embodied"
    content = json.loads((root / "sections.json").read_text(encoding="utf-8"))
    source = previous("rulebook")
    # Keep useful shared clauses verbatim, replacing their retired acquisition wording.
    entries = sections(source)
    for key in ("10", "11", "14", "16", "20", "24", "27", "29", "starting-gear", "reach"):
        entry = entries[key]
        text = source[entry["start"]:entry["end"]]
        if key in {"10", "11"}:
            text = text.replace("Preserve the eligible creation rarity override and independent natural receipts.",
                                "Use normal independent rarity/Luck unless the player explicitly requests an override for this board.")
            text = text.replace("and the existing creation-only UNIQUE override", "and only an explicitly player-requested scoped override")
        elif key == "14":
            text = text.replace("Talent Web powers", "owned powers").replace("high-rarity Talent", "high-rarity feature")
            text = text.replace("Hybrid Class Breakthrough", "major personal refinement")
        elif key == "16":
            text = re.sub(r"- Grant \+1 Skill Point\.\s*- Grant \+1 Talent Point\.",
                          "- Grant the campaign's earned personal and Sovereign development choices through its automatic progression records.", text)
        elif key == "24":
            text = text.replace("**Sixteen equipped gear slots remain binding:**", "**The body's actual equipment locations remain binding:**")
        elif key == "29":
            text = text.replace("## Summon evolution through Skill Points", "## Developing summon powers")
            text = text.replace("are eligible for V4.0's five integrated passive Skill Evolution choices.",
                                "develop inside their actual owned core power or lasting owner foundation, using the earned refinement/development choices.")
        elif key == "20":
            text = text.replace("guaranteed permanent Sovereign Evolution", "separately earned permanent Sovereign developments")
        elif key == "starting-gear":
            text = text.replace("completed Age of Convergence build", "completed Sovereign build")
            text = text.replace("selected Signatures", "selected core powers")
            text = text.replace("Start all sixteen legal equipment slots at weight 1 (plausible).",
                "Use the body's mapped equipment locations at weight 1; precommit weight 0 for EVERY unmapped location so it cannot be drawn.")
        elif key == "reach":
            text = text.replace("Signature and Background boards", "personal-refinement and Background boards")
            heading, rest = text.split("\n", 1)
            text = heading + "\n\nRead sovereign-body and bound-dominion: the actual body governs effective reach/movement. Bound powers use Domain-wide operational reach; numerical area geometry, target counts and costs remain. The descriptive display below is for applicable mobile/source ranges.\n" + rest
        content[key] = text
    # This shared preface still described an older two-Signature Background.
    entry = entries["story"]
    text = source[entry["start"]:entry["end"]]
    text = text.replace("two selected Signature Skills", "selected core powers")
    content["story"] = text
    content["quest-journal"] = '''## Finite quests, System rewards and completion

Use finite named quests with clear goals and objective lists: each objective has stable id, readable text and pending/done/failed status. Keep completed, failed, abandoned and paused history. Main arcs have chapters with real endings. A completed objective stays completed; new trouble becomes a separate objective/quest instead of moving the finish line.

Publish actual System rewards separately from NPC contract payment or physical salvage. system_reward supports xp,currency,items,evolution_credits (0..3) and summary. The server settles earned rewards once into actual XP, funds, inventory and reward_credits; never also add those manually. Physical spoils still need recovery. NPC contract_payment has creditor,condition,status and a currency/items reward, collected separately only when its actual terms are met. Do not count one payment twice.

A free quest refinement improves a real owned core power. Offer five compatible normal rarity/Luck directions on completion, choose the earned quantity or explicitly bank; banking remains voluntary and does not freeze ordinary play. When a level is also earned, show compatible personal and free quest selections together, plus actual Sovereign growth. No new Talent or standalone skill board. Save spend_evolution_credit={ability_id,evolution_id}, the named nested child and consolidated current rules with the selection. It uses only its once-earned quest reward, not personal or Sovereign development. Current validators accept personal refinements and a quest refinement on one parent in the same normal batch.

Objectives, known danger, practical next step, deadline, promised rewards and ending consequence belong in the Quest Journal. Default substantial System completion XP is 20 easy,50 standard,120 dangerous,250 extreme, tailored to actual level/effort. Significant chapters may grant meaningful equipment or a free refinement. Show a tangible aftermath: a cleared route, captured asset, integrated holding, resolved threat or changed relationship. Reuse actual saved commitments and retry-safe settlement. No extra approval, verification read or reward tool roundtrip.

'''
    # The player's clarification removes all automatic creation grade overrides.
    for key, text in content.items():
        text = text.replace("EIGHT distinct UNIQUE", "EIGHT distinct").replace("EIGHT mechanically different UNIQUE", "EIGHT mechanically different")
        text = text.replace("eight distinct UNIQUE", "eight distinct").replace("eight UNIQUE", "eight independently rarity-rolled")
        text = text.replace("Three UNIQUE passive", "Three class-grade passive").replace("three separate UNIQUE passive", "three separate class-grade passive")
        text = text.replace("eligible creation offers use the established UNIQUE override while preserving genuine underlying natural/Luck receipts", "eligible creation offers use normal independent natural/Luck receipts")
        text = text.replace("Eligible creation offers use the established UNIQUE override while preserving genuine underlying natural/Luck receipts", "Eligible creation offers use normal independent natural/Luck receipts")
        content[key] = text
    (root / "sections.json").write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {"rulebook": [{"section": key,
                 "source_sha256": hashlib.sha256(source[entries[key]["start"]:entries[key]["end"]].encode()).hexdigest()}
                 for key in content],
                "hardener_sha256": hashlib.sha256(previous("hardener").encode()).hexdigest()}
    # Explicit preface corrections are independently reversible and source-pinned.
    old = source.splitlines()[4]
    manifest["preface"] = [{"id": "embodied-tagline", "old": old,
        "new": "FOUR CORE POWERS · MOBILE, BOUND OR DISTRIBUTED · DOMAIN, COMMANDER AND FORCES · NORMAL RARITY / PLAYER-REQUESTED OVERRIDES"}]
    for key, prefix, replacement in (
        ("background", "**V1.0 Background redesign amendment", "**Sovereign Background:** Five normally rarity-rolled offers provide identity, one nested imprint on an owned core power and an optional world connection. Preserve parent mechanics, rarity and history; the imprint is not another standalone power. Chapter 11 governs. No retired Signature/Talent/3+2 acquisition model applies."),
        ("precedence", "V4.1 changes that *do* have priority", "Sovereign's effective chapters and saved play profile govern current creation, four-power growth, body, Domain and presentation. Shared honest rarity, independent Luck, real resources/actions, committed opposition, world continuity and finite consequences remain. Older edition acquisition checklists are historical and do not create additional boards.")):
        old = next(line for line in source.splitlines() if line.startswith(prefix))
        manifest["preface"].append({"id": "embodied-"+key, "old": old, "new": replacement})
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    module = (root / "system.txt").read_text(encoding="utf-8")
    module = module.replace("EIGHT distinct UNIQUE", "EIGHT distinct").replace("eight UNIQUE", "eight independently rarity-rolled")
    module = module.replace("Three UNIQUE passive", "Three class-grade passive").replace("three separate UNIQUE passive", "three separate class-grade passive")
    module = module.replace("Normal creation UNIQUE overrides, natural receipts and fixed choice dependencies remain honest.",
                            "Normal independent creation rarity/Luck applies unless the player explicitly requests a scoped override.")
    (RULES / "sovereign/system.txt").write_text(module, encoding="utf-8")
    (RULES / "sovereign/checklist.txt").write_text(
        "# Sovereign System — embodied play\n\nRead sovereign-body and the actual saved campaign profile. "
        "New characters use normal rarity/Luck, four core powers, functional class-grade foundations, "
        "body-appropriate equipment and two personal/two Sovereign developments. Only the player's "
        "explicit prompt may override creation rarity. Mobile, bound and distributed forms are supported. "
        "Use close-up scenes and normal batched saves; preserve older campaigns.\n", encoding="utf-8")
    print(f"Pinned {len(content)} reviewed Sovereign sections")


if __name__ == "__main__":
    pin()
