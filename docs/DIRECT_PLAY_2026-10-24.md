# Direct play and starting equipment — 2026-10-24

Release: 1.0.37. Sovereign System is deferred.

## Player flow

- Keep the four actual creation-choice turns. After the final Background, attributes and name, the GM writes Your story, equips the starting outfit and saves the first scene in one update. There is no separate character/start approval or dashboard button.
- Advancement selections and banking apply directly. Once all pending tracks resolve, continue an already ordered sequence from its stopping point. Honor an explicit manual pause.
- Opening a dashboard, reading rules or deploying the app does not start or alter a campaign. Corrections to committed history retain their existing review controls.

## Equipment

Starting equipment has its own recorded allocation, separate from money and ordinary loot. Class budgets are Common 12, Uncommon 24, Rare 48, Epic 96, Legendary 192 and Unique 320. Six points cover suitable essentials; the remainder funds four functional equipped pieces: a class focus/weapon, protection, movement/fieldcraft and an accessory/command implement.

Draw promotion chances only after reserving the remaining tier floors. A Unique class receives a Legendary-or-Unique centerpiece and three Epic-or-better supporting pieces. Item names and full effects follow the selected build and existing rarity contracts. Save the immutable receipt and four item IDs; retries reuse the original draw. Existing inventories are not automatically rewritten.

## Dashboard launch

Expose the same dashboard through both standard MCP Apps and the older ChatGPT resource format. Prefer inline display, connect immediately when the compatibility bridge is available, and resolve cached dashboard resource addresses from earlier deployments to current content. Ownership and approval-token handling remain enforced.

## Verification and limits

- Authenticated tool tests cover direct completion, missing-data atomicity, retired creation approvals, exact retries, opening saved state, and advancement continuation.
- Equipment checks exercise 7,776 tier/draw-boundary combinations for budgets, floors and Unique guarantees.
- Appwrite store-contract fixtures cover completion, persistence and exact retries. These are local fixtures, not a test on a player's hosted campaign.
- Browser player-view matrix: 24/24 checks passed. At 390 px, all four layouts loaded through a simulated older ChatGPT bridge without horizontal overflow; Full rules and Upgrades were clicked successfully.
- The actual ChatGPT mobile app has not been tested. Refresh its tools and reopen the dashboard after deployment before judging native-client behavior.
- Package checks and source-integrity checks preserve the complete rulebook and synchronized references. Reversible revision records document the targeted edits.

The release uses the existing Git-linked deployment. No plugin ZIP upload or real campaign mutation is part of this verification.
