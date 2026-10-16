"""Development-only authenticated creation tools; registration is explicitly gated."""
from mcp.types import CallToolResult, ToolAnnotations
from pydantic import StrictInt

from .auth import WRITE_SCOPE


def register_creation_tools(server, repository, invoke, metadata, read, write, resource_uri):
    render_meta = metadata()
    render_meta["ui"]["resourceUri"] = resource_uri
    render_meta["openai/outputTemplate"] = resource_uri

    @server.tool(title="Character creation", annotations=read, meta=render_meta)
    def render_creation(draft_id: str | None = None) -> CallToolResult:
        """Open the DEVELOPMENT creation screen using this account's saved drafts.
        Choices require app approval. Does not create a campaign, roll, or authorize play.
        Keep the view mounted; get_creation_draft refreshes it as the GM completes offers.
        """
        return invoke(lambda owner: repository.get_draft(owner, draft_id) if draft_id
                      else repository.list_drafts(owner))

    @server.tool(annotations=read, meta=metadata())
    def list_creation_drafts() -> CallToolResult:
        """List this account's DEVELOPMENT creation drafts. Does not create or start gameplay."""
        return invoke(repository.list_drafts)

    @server.tool(annotations=read, meta=metadata())
    def get_creation_draft(draft_id: str, include_preparation: bool = False) -> CallToolResult:
        """Read a saved development draft. Preparation exposes private Class review/history
        and fixed final tiers, not raw rolls. Never show private seeds/reasons to the player.
        Partial kits are not player offers. Completed offers require supported programs;
        semantic novelty/tier certification remains pending.
        """
        return invoke(lambda owner: repository.get_draft(owner, draft_id, include_preparation))

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def propose_creation_start(world_preview: str, action_id: str) -> CallToolResult:
        """On an explicit DEVELOPMENT TEST request only, preview a new creation draft.
        No record, rolls, character, campaign or time advancement occurs before app approval.
        """
        return invoke(lambda owner: repository.propose_start(owner, world_preview, action_id), True)

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def propose_creation_transition(draft_id: str, action_id: str, expected_version: StrictInt,
                                    kind: str, payload: dict) -> CallToolResult:
        """Preview one typed DEVELOPMENT creation transition without drawing random numbers.
        Follow current phase; retain original boards/rarities. Retry the same action ID/arguments.
        Class roll_board requires review: 12–15 seeds, five shortlist IDs, select/reject decisions,
        ten pair differences and comparisons with actual known_classes from preparation.
        Difference fields: left/right IDs, permission, economy, tactical_decision, independent_utility.
        Each decision has seed_id, selected and reason. Never invent history or certify novelty.
        """
        return invoke(lambda owner: repository.propose_transition(
            owner, draft_id, action_id, expected_version, kind, payload), True)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True,
                 idempotentHint=True, openWorldHint=False), meta=metadata(WRITE_SCOPE, app_only=True))
    def confirm_creation_transition(proposal_id: str, approval_token: str) -> CallToolResult:
        """APP ONLY. Commit the exact development transition approved by the player.
        Retry this proposal/token after failure. This never creates a playable campaign.
        """
        return invoke(lambda owner: repository.confirm(owner, proposal_id, approval_token), True)

    @server.tool(annotations=read, meta=metadata())
    def audit_creation_draft(draft_id: str, show_rolls: bool = False) -> CallToolResult:
        """Inspect creation event integrity; show raw receipts only for explicit SHOW ROLLS requests."""
        return invoke(lambda owner: repository.audit(owner, draft_id, show_rolls))
