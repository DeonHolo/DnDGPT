# Dashboard host startup and updates

Runtime 1.4.1 fixes dashboard initialization when ChatGPT exposes both the MCP Apps bridge and window.openai. The previous bootstrap treated window.openai.callTool as a reason to skip ui/initialize and ui/notifications/initialized. ChatGPT's live timeout detail explicitly reported that the app did not finish initialization within five seconds. A successful render_dashboard tool response meant the server returned its data; it did not establish that the iframe mounted.

The regression browser fixture reproduced that missing readiness message. It also reproduced a separate startup crash when persisted view_preferences contained a layout without panels/details arrays. Existing host tests exercised the two interfaces separately and missed the hybrid case.

The dashboard now begins MCP Apps negotiation for every embedded host, including hosts that also provide compatibility globals. It sends the initialized notification before processing host styling or fetching saved data. Compatibility-only hosts can begin after a 300ms grace period instead of waiting for the 15-second standard request timeout. A delayed modern handshake can recover one rejected compatibility read. Late bridge injection remains supported. Restored preferences receive safe array defaults.

This follows [OpenAI's standards-first UI guidance](https://developers.openai.com/plugins/build/chatgpt-ui): shared initialization and tool operations use the MCP Apps bridge; compatibility APIs remain a fallback. The existing separation between render and data tools remains. No new model tool call, authorization scope or gameplay rule is required.

Regression coverage executes the actual startup JavaScript in Node with standard, hybrid, compatibility-only, delayed and standalone hosts, plus partial/malformed preferences. The browser fixture additionally uses real authenticated local MCP transport and a disposable campaign to test notification updates and refreshes while retaining the mounted document. It records before/after results in ignored test-results files. Production verification and release evidence follow after deployment.
