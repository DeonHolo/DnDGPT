# How DnDGPT loads its rules

DnDGPT keeps one complete rulebook and a compact execution checklist called the Rule Hardener. The hardener points to the full rules and lists recurring mistakes to check before answering. It is prompting guidance, not a second model or an automatic rules validator.

The previous hardener had grown to 67,534 bytes, with large passages repeated from the manual. The current checklist stays within one 8,000-character rules-tool page. The full manual remains intact. Every revision is recorded in the integrity manifest and can be reversed to verify preservation of the original source.

## Connected play

1. Read `read_rules(document="hardener")` completely.
2. Read `read_rules(document="index")` for current section keys and related rules.
3. Before generating or resolving a situation, fetch the relevant chapters and amendments with `read_rules(document="rulebook", section="KEY")`. Follow `next_offset` with the same document and section until it is null.
4. Reuse material already available in the current context while its source hash remains current. Refresh after a rules update, a changed hash or loss of relevant context.

For example, a world preview requires the world chapter plus the current world-preview and story amendments. A combat decision needs combat and applicable resource, condition or companion rules. The index names creation-stage dependencies so older five-phase wording cannot override the current four-turn sequence.

Finishing a section does not mean the entire manual was read. Missing required material must be fetched before deciding. Full-document reads remain available for audits. Bundled copies include the same complete manual, checklist and index for supported offline readers. A player's explicitly selected custom rulebook still governs that campaign.

The full Interactive Glossary & Tooltip System remains in Chapter 33. Routine story turns use the compact `story-ui` contract and `continuity` amendment, reusing current copies already in context. Fetch Chapter 33 for implementation details, audits or questions the compact contract does not settle. The hardener carries a short rendering checklist and preserves an honest fallback when the host cannot render real interactions.

An ordinary turn reuses the latest successful state/save response and its version, fetches only missing applicable rules, performs genuine necessary rolls and commits one authorized batched update. A successful save response is the commit verification; do not follow it with a routine get/refresh chain. Use `get_campaign(view="turn")` and `save_chat_update(result_view="turn")` when full older logs are unnecessary. Compact views keep current mechanical records and explicitly identify omitted history; `view="full"` remains available when those details matter. Resume and history tools are on demand, not extra steps in every turn.

## Why reduce duplication?

Research found that information position can affect performance in long contexts, with relevant material in the middle sometimes used less reliably. That study tested particular models and retrieval tasks; it does not establish DnDGPT's error rate. [Lost in the Middle](https://arxiv.org/abs/2307.03172).

Another study found that repeating an input improved performance in non-reasoning settings. Its results do not demonstrate that duplicating a large RPG manual improves long-running, tool-using gameplay. Repetition can help in some conditions, so removing it should be evaluated rather than treated as a universal law. [Prompt Repetition Improves Non-Reasoning LLMs](https://arxiv.org/abs/2512.14982).

Anthropic recommends keeping agent context focused and retrieving useful material as needed. DnDGPT's indexed loading follows that engineering approach. Its effectiveness here still needs representative gameplay evaluation. [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

## What verification proves

Tests verify that indexed pages reconstruct exact canonical sections, hashes match, arbitrary file paths are rejected, reads do not write campaign state, and bundled copies match. Tool-call logs can show what was fetched. Neither a hash nor a successful fetch proves that ChatGPT understood or obeyed the text. Rule adherence needs separate evaluations covering creation, combat, advancement, saves and presentation.
