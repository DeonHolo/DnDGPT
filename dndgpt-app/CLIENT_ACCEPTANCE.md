# Client acceptance boundaries

This source checkpoint contains the application and tests, not another user's working private connection.

The author's private installation was exercised in regular ChatGPT with authenticated dashboard rendering, saved updates and reopen/recovery. Display support is client-dependent. Neither an archive nor a local browser harness demonstrates that a different account can install the App, that every PiP mode works, or that the service has production availability.

For each new deployment verify:

- HTTPS health works; anonymous protected MCP requests fail.
- OAuth sign-in grants only the intended read/write scopes; account ownership isolates records.
- A disposable record can be created, read, saved, reopened and retried without duplicate consequences.
- The actual ChatGPT client renders the dashboard and preserves the intended surface across later messages.
- Navigation and refresh perform no gameplay changes; confirmation and adventure-start decisions remain explicit.
- Database recovery and restart behavior work in that hosting environment.

Cross-account sharing, public-directory publishing, permanent hosting guarantees and latency benchmarks remain separate acceptance work. Private evidence and live records are excluded from this public repository.
