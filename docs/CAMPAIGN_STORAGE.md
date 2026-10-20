# Where campaign saves live

DnDGPT's hosted saves are in **Appwrite's database**. **Auth0 handles sign-in** and identifies which account may open them. Google is an optional way to sign in through Auth0; choosing Google does not put campaigns in Google Drive.

| Part | Job |
| --- | --- |
| ChatGPT | Runs the GM conversation and sends explicit save updates through the connection. Narration alone is not a database write. |
| Auth0 | Verifies the player's identity and issues the access token. It is not the campaign database. |
| Hosted MCP server | Checks the token, ownership and requested operation before reading or changing a campaign. |
| Appwrite TablesDB | Stores campaign records, versions, events and roll receipts. |
| Dashboard | Displays saved state and account display preferences. It does not turn the entire conversation into a save. |

The code derives ownership from the verified token's issuer and subject, not a player-entered email. Two sign-in methods can identify separate accounts even when their email addresses match. Keep using the method associated with your saves; do not assume signing in with Google links an existing password account.

For implementation details, see [authentication](../dndgpt-app/app/auth.py), [Appwrite persistence](../dndgpt-app/app/appwrite_store.py) and [hosting notes](MAINTAINER_HOSTING.md). The hosted service's [Privacy Policy](https://deonholo.github.io/DnDGPT/privacy.html) describes retention and deletion.

## Versions and portable snapshots

Each campaign has a current state and retained historical snapshots. A new save does not automatically delete the older ones. The dashboard can list versions and show readable changes without replacing the current state. Corrections still require a preview and explicit approval against the current version.

**Download campaign** exports the current snapshot, including recorded character mechanics, outcomes and continuity. It does not export every historical version, the server's roll-receipt ledger, access tokens or pending approvals. Keep the file private: it contains campaign records and may contain unrevealed setting data.

Restore validates the file, then creates a new paused campaign owned by the signed-in account. It preserves the recorded phase and advancement freeze, leaves the source campaign intact and starts a new version/event history. Its checksum detects corruption; it does not certify that a player-supplied file or its recorded rolls are authentic. This is portable snapshot recovery, not database point-in-time recovery. See [usage and verification](CONTINUITY_AND_RECOVERY.md).

## How Questforge approaches this

[Questforge](https://github.com/adrianmelic/codex-questforge) is a related project with a different save model. Its documented 1.3 portable-campaign workflow uses local campaign files, with optional synchronization to an exact folder the player authorizes through a writable storage connector. Google Drive is its first documented end-to-end tested beta target. It can export a portable ZIP when direct synchronization is unavailable.

Questforge checks campaign identity and save lineage before continuing and stops on newer or divergent copies. It verifies writes and commits the manifest last. Media synchronization is separate from the canonical campaign save. Without a writable filesystem or authorized connector, it keeps a conversation ledger and does not claim to have created durable files.

These are Questforge's documented behaviors, reviewed on October 19, 2026, not an independent live test. DnDGPT uses its account-backed Appwrite service and portable JSON snapshots rather than folder synchronization. It does not have Drive access or automatic synchronization between exported copies.
