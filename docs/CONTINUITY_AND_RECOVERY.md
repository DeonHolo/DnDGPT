# Campaign continuity and recovery

After a selected action, the GM should connect the next passage to what the player just did: finish the immediate outcome, carry forward an unfinished problem, and explain travel or elapsed time when the scene changes. One or two sentences usually suffice. This is a writing rule, not a requirement to add another tool call. It does not authorize invented thoughts, unchosen actions or skipping an unresolved decision.

The existing limit of two player decisions on the same underlying obstacle remains. A failed repair should produce a consequence, a materially different approach or a closed attempt; it should not generate another menu to retry the same check indefinitely.

## Resume, history and corrections

Open **View options → Campaign brief, history & portable saves** in any dashboard layout.

- **Resume brief** shows the saved scene, recent intent, action, outcome, pending decision, unresolved threads and NPC commitments. Older saves without continuity notes say so. Reading it leaves pause, time and the saved version unchanged.
- **Save history** loads a page of versions only when requested. Select a version to see the public fields that changed when it was saved. Long historical values are labeled excerpts. Viewing them never rolls back the current save.
- **Correct a saved detail** supports common character/resource/location fields. Enter the new value and a reason, then preview. The approval panel shows complete before/after values for the public fields. **Approve correction** uses the existing current-version approval gate; preview alone does not commit anything. More complex corrections can still be proposed through the GM.

The brief is derived from committed state, without a model call or another storage read. The GM adds or changes bounded `continuity` notes in the same save used for the rest of that turn. Unrecorded promises and old-chat details cannot be recovered merely by adding this field.

## Download and restore

**Download campaign** prepares a private JSON snapshot. If the host does not start the download, use the displayed file link. Hosts can restrict downloads: **Copy JSON if downloads are unavailable** exposes the same data and a copy button. Save that exact text in a local `.json` file using the displayed filename. The selectable text remains available if clipboard access is restricted too. Choose the file under **Restore a campaign export**, review the source identity, then select **Restore paused copy**. The restored campaign has its own ID and starts at version 1; it never overwrites the original. A retry of the same restore returns the same result.

Restore keeps the character, saved mechanics, fictional time, phase and advancement freeze. It creates the copy paused and does not import old approval tokens. Character confirmation, adventure start and resuming an adventure remain separate operations. Exports contain the current snapshot rather than all server history or original roll receipts. A checksum detects corruption, not authenticity. See [storage boundaries](CAMPAIGN_STORAGE.md).

## Turn efficiency

The normal turn path has no mandatory history, export, evaluation or resume calls. Reuse current state/rules, batch independent authorized rolls when appropriate, then save the authorized result once. Do not batch rolls whose later choices depend on earlier results, or bypass approval gates to save time. Compact turn responses retain current mechanics while excluding older log bulk. The dashboard reads state and pending approval in one transaction and polls at most every 45 seconds while visible; successful tool results update it directly.

Use a full save for story/history decisions unless the relevant established facts are already in context. Compact reads are optional for turns whose current mechanics and available story context suffice. Fetch full before relying on omitted past events, promises or world details. Missing information is not proof that an event never happened. Ordinary world updates now merge object fields recursively, retaining omitted keys. Lists/scalars still replace their explicit values; never reconstruct them from an excerpt. Approved corrections can intentionally replace the world object.

Storage timings and model-visible campaign JSON sizes can be measured. Compact responses still send the full dashboard snapshot in metadata hidden from the model; the size comparison is not a reduction in total network traffic. Timings do not include ChatGPT reasoning, UI generation, host scheduling or the player's network. These changes reduce avoidable work; they are not a guaranteed maximum time per turn. See [the continuity tests and their limits](CONTINUITY_TESTS.md).

## Repeatable checks

From `dndgpt-app`, run `python -m pytest -q`. For the browser matrix, start `python -m uvicorn tests.host_harness:app --host 127.0.0.1 --port 8779`, open `http://127.0.0.1:8779/test-continuity` and click **Run layout and recovery checks**. The page exercises all four layouts at 390 and 1180 pixels, approval visibility, collapsed/padded story content, all three ability tabs, read-only history, approved correction and file restoration. It writes `test-results/continuity-browser.json`.

This test page is a simulated MCP Apps host using real local authenticated transport and disposable SQLite campaigns. It is not evidence of ChatGPT's own rendering or model performance. The private `appwrite_probe.py` separately exercises the hosted Appwrite store with probe-owned data and records save/read timings, API-call counts and compact-response sizes. Never expose the test host or private probe publicly. Neither test restores a provider database backup.

Actual generated class/ability quality is reviewed separately; see [sample findings and rubric](GENERATION_REVIEW.md). Those development reviews add no calls to gameplay turns.
