# Open the dashboard once

Runtime 1.1.5 corrects a regression introduced in 1.1.4. Binding the dashboard resource to `read_rules`, `get_campaign`, `list_campaigns` and `create_chat_game` caused ordinary calls to produce more dashboard components. First-use instructions alone could not prevent the host from mounting those tool-bound views.

Only `render_dashboard` now advertises the modern dashboard resource, the legacy output template and thread/global entrypoints. The first DnDGPT call in a chat opens it. Normal reads and saves continue returning current state and widget snapshots, which update the mounted view through the existing notification/polling paths. Ongoing play reuses its campaign and view; reopening is reserved for an explicit request or a closed, missing or outdated component. The three-mode chooser remains unchanged.

Regression checks inspect actual MCP tool definitions and run one open followed by creation, repeated rules/state reads and two saves. They verify one opening resource and updated full widget snapshots after the saves. This tests transport behavior, not a claim that every ChatGPT model obeys the open-once instruction.
