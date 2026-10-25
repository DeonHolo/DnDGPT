# Campaign focus release 1.0.45

Published implementation: `86032ca0e71b52a40e58cf6076056190cb8e777b`.

## Behavior

- Both games save independent focus (Mixed, Hunt & Explore, Conquest) and dialogue (Normal, Minimal, On request) through the existing batched save. Partial edits preserve the other preference; full, turn and resume views retain both.
- Sovereign Mixed defaults to **70% personal adventure / 30% strategy**. Conquest can center warfare/expansion. Reduced dialogue supplies direct action routes, finite hunts/conquests, declared System rewards, lasting consequences and authorized delegated upkeep.
- World & Campaign Log → Objectives shows committed preferences, active known objectives, expected benefits, rewards, changed places and known fronts. Controls send an explicit preference-only request to chat; they do not optimistically claim a save.
- Preference-only saves preserve phase, pause, advancement freeze, time and mechanics. Normal ownership, version, exact-retry and history protections remain. Existing campaigns are not retconned or assigned a new focus on publication.
- Portable export/restore retains preferences. Hidden quests/objectives stay out of player-facing journal cards.
- Added a 4,575-character Personalization prompt with normal inline term/punctuation flow and independently sized tooltip cards. Removed unrelated gameplay preservation reminders from that personal prompt; authoritative rules retain their mechanics.

## Verification

- Local focused suites: 64 passed; final changed ownership/history and hosted-contract cases: 3 passed. The first run hit an existing Windows `.test-tmp` cleanup error; a new isolated base directory resolved setup without deleting the old directory.
- Final GitHub CI `40167808457`: **641 passed**, two existing dependency warnings, packaging succeeded. Initial CI `40167599631` found only a stale 13-check count after adding two recovery checks; the final test explicitly verifies both new checks and expects 15.
- In-app browser, disposable simulated hosts: **14 living/focus + 24 existing player-view + 8 journal/Gallery checks passed**. Focus cards and controls were checked in Original, Reclaimed Codex, The Orrery and Ember Ledger at 390/1100px; existing ability-list checks cover narrow/wide widths. Local proof image: `dndgpt-app/test-results/campaign-focus-1.0.45.png`.
- Production deployment `6add9c85c47c5f5443d7` and private probe deployment `6add9c84793716aa6cb1`: ready at the implementation commit. Health execution `6add9cf6862d927a13e4`: HTTP 200, version 1.0.45.
- Hosted disposable execution `6add9cf604bfb48ac389`: **16 hosting + 15 recovery checks passed** in 20.52 seconds. Includes preferences in the ordinary save and all views, plus preserved preferences after actual hosted restore. No model calls or player-campaign access.
- Native connected `read_rules` returned complete `campaign-focus` sections for both games, including the 70/30 default, matching the source hashes below.
- Hardener remains one page: Age 7,936 characters; Sovereign 7,987. Bundled sources match; the rule revision is reversible. Portable packaging contains 252 files at version 1.0.45. No ZIP was uploaded to the native connection.

| Source | SHA-256 |
| --- | --- |
| Age rulebook | `6d28b20a0f4bf31f27ac697d95af3f3eb05743ef14513a4d74d30a81084df25c` |
| Sovereign rulebook | `37f7bec68c47983c20147e0ae8733de796e76c28adf2d728352c8309bf446f8f` |
| Age hardener | `ac3a7a1e0ca906b0bb64c486eb666343dfe2dbf6eacb8eeea08aca1d05d45901` |
| Sovereign hardener | `6fe047dbded8c252bfa755dbd9cdc53ebf10356db0594e3ca078014a00f77442` |

These checks establish persistence, transport and local rendering. They do not measure whole-turn model latency, actual phone opening, generated Intelligent UI compliance or long-campaign style adherence. The Personalization prompt is an instruction fix, not a verified repair of a previously generated ChatGPT interface.
