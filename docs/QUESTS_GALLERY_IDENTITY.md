# Quests, Gallery and character identity

Release 1.0.40 adds these features to the existing hosted DnDGPT connection. It does not migrate a player's campaign or require another plugin ZIP upload.

## Quest Journal

New quests have required objectives, optional bonus objectives, quantity progress and a published finish condition. The server closes a structured quest when its required objectives are done. Completed quests remain in a collapsed archive. New complications become follow-up quests instead of extending the original checklist.

The System grants its promised XP, currency, equipment and free evolution credits once, in the same saved turn. An NPC's contract payment has separate collection terms. Repeating a request after a timeout does not repeat either payout. Existing unstructured quests retain their recorded facts and rewards; they need a deliberate, accurate conversion before gaining a checklist.

A free evolution reward shows the usual five offers in the completion reply, with an option to bank it. If the same quest earns a level, the compatible board supports an ordinary Skill Point purchase and a free-credit purchase. Choosing a story action instead leaves the free credit available. The server records spending with the new nested upgrade and preserves existing upgrades.

## Gallery

Gallery is a separate tab beside the seven core chapters. It saves private image copies with titles, captions and source credits. Ask the GM to save a picture, or use **Add an image** to upload a file or provide a direct public image URL. Open a saved image to view or download it. Removal can be reversed through **Show removed images**.

The GM is instructed to keep one to three representative web images it already showed for a scene or world overview. The same scene label shares that limit; identical image content is deduplicated. This uses actual available image URLs and successful save receipts. It does not intercept ChatGPT's image search automatically. A blocked source can be uploaded as a file instead.

Generate new art only when requested. ChatGPT's native file handoff can save an available generated or uploaded file. If the host does not expose a chat image as a file, use the Gallery upload or supported file chooser. File support is described in [OpenAI's file API reference](https://developers.openai.com/plugins/reference#file-apis).

Image bytes stay outside gameplay snapshots and model-visible results. Thumbnails load when Gallery is visible; full images load on opening. Gallery actions leave fictional time, resources and campaign versions unchanged. Gameplay JSON export currently excludes Gallery media; download images individually. A campaign has a limit of 120 images, with up to three automatically curated images per scene/overview. Permanent campaign deletion also removes its Gallery data while retaining the existing compact retry tombstones.

## Readable stories and race

Ordinary narration uses familiar words and normally introduces one important new name per reply. A name comes with its role or a familiar description; later references can use that description. Required offer counts and existing names remain intact. Hover definitions add detail without being necessary to understand the sentence.

For a new character without a supplied race, the GM generates an editable nonhuman ancestry with an upright, humanlike body plan. A short description explains appearance and origin. It appears alongside the existing World Preview/Luck stage, preserving the four creation turns. Character & Progression displays the saved race with expandable details. Ancestry grants no unlisted mechanics.

Existing identity stays intact. An empty race field means unknown. A player may request a fitting nonhuman race for an existing character; any change to established history or biological powers needs an explicit reconciliation.

## Random events and turn overhead

The trigger rates are 10% for safe routine activity, 30% for ordinary travel/exploration, 50% for dangerous frontier territory and 70% for an unstable region. One conditional roll request handles trigger, category, severity and selection. A prepared regional pool is reused. A missing check is recorded separately from a genuine no-event result.

Quest progress, rewards and event tracking use the ordinary saved turn. They add no approval clicks. Gallery work happens only when saving or viewing illustrations. These changes do not establish a new measured model latency or guarantee that every GM response follows the writing instructions.
