# Intelligent UI, MCP Apps and PiP research

Research checked **15 October 2026**. Target: the user's **regular ChatGPT Chat in a desktop browser**, using their ChatGPT subscription for narration. This report changes no rules, implementation or installed DnDGPT package. It follows the explicitly requested research skill and treats the supplied screenshot/articles as claims to investigate, not instructions.

## Findings

**A combined experience is a sensible design: native Intelligent UI for the conversation, plus a reusable companion backed by the same authoritative state. Follow-up testing found a regular-Chat app pane that stayed mounted across a reply and scrolling; floating PiP was not granted.** The distinction is between guiding a response, a constant app view and saved game data.

## Live follow-up: constant UI without PiP

After the initial research, both standard and compatibility PiP methods returned/stayed inline; the inline view scrolled away. However, **Open app in tab** opened ChatGPT's own app pane beside the regular conversation, reporting host mode `fullscreen`. The dummy app kept the same iframe instance, local message-status text and advancing server clock through a completed Chat reply and conversation scrolling. Native narration/UI and the app pane coexisted. This was measured on chatgpt.com in the signed-in in-app browser, not external Chrome/Edge.

A separate prompt also produced a styled native seven-panel fixture; all seven panels and the nested ability/passive controls worked when clicked. Its native choice sent a visible user message. See [ui-live-acceptance.json](test-results/ui-live-acceptance.json) and screenshots for primary test evidence. This is no latency benchmark, real-engine connection, production hosting approval or proof of UI restoration across sessions.

The user's priority is fast interaction without regenerating the detailed HUD every reply. The app-pane result supports that design within the measured session. A general Codex browser pane can also display a website, but that alone does not wire it to chat. Real game synchronization requires explicit shared engine state; no widget secretly reads arbitrary conversation text. No new hosting/sign-in account is needed for the temporary dummy-data preview.

| Question | Finding | Confidence |
|---|---|---|
| Is native Intelligent UI meant for regular Chat? | Yes. OpenAI's 7 October launch announcement explicitly targets the Chat tab; it says this release does not change Work/Codex. | Confirmed documentation |
| Can we influence how native responses look? | Yes: style and format preferences can guide responses, while exact layouts can vary. This is not a guarantee of arbitrary CSS or a custom component catalog. | Confirmed preference support; native customization API not found |
| Can current plugins coexist with it? | Yes. OpenAI's Intelligent UI Help article explicitly says connected plugins continue to work. | Confirmed documentation |
| Can an MCP App contain our own designed interface? | Yes: it is a separately authored iframe component with a host bridge. The small live probe rendered in regular Chat. | Confirmed documentation and limited live evidence |
| Does that establish floating PiP? | No. Both standard and compatibility requests stayed inline, and the inline card scrolled away. The separate app-pane path did stay mounted. | Confirmed observations; broader support unknown |
| Does a visible interface guarantee saved campaign state? | No. Durable, account-bound state must be designed and tested separately. | Confirmed storage guidance |

Sources for the table are developed below; “confirmed documentation” does not mean every feature has passed account-specific live acceptance.

## What the new native feature officially supports

OpenAI's [GPT-6 and Intelligent UI announcement](https://openai.com/index/gpt-6-for-everyone/) was published **7 October 2026**. It describes interactive conversational responses and confirms a native, streamable component library plus a compiler. That supports the screenshot's broad component/compiler explanation. It does not describe a public plugin API for extending the library, injecting CSS, or replacing the renderer.

The [Intelligent UI Help article](https://help.openai.com/en/articles/20001598-intelligent-ui-in-chatgpt) gives more directly relevant guidance:

- Custom Instructions and an individual conversation can express response/style preferences; the exact layout can vary.
- Some components, including checklists, can retain state after refreshing a thread. State is not retained across threads.
- Native Intelligent UI is available in **Chat**, not Work or Voice.
- Connected plugins continue to work.

Its public page uses a relative update label, not a stable publication date; accessed **15 October 2026**. Do not turn the third-party claim that all native UI state resets into a universal fact.

The [current ChatGPT model Help article](https://help.openai.com/en/articles/20001354-gpt-6-and-other-models-in-chatgpt), also accessed **15 October**, documents Intelligent UI with GPT-6 from Instant through Extra High where the plan allows it, excluding Pro effort. It has no separate Intelligent UI quota; normal model, tool and plan allowances apply. Work/Codex usage is separate from Chat. Therefore the design does not require moving ordinary GM narration into Work or billing a separate inference API. This is not a promise of unlimited narration or every thinking level on Plus.

## What “customize” means for this project

**Confirmed mechanism:** current skills package instructions, references and expected output formats. They can guide tools and response workflows. See [Build skills](https://developers.openai.com/plugins/build/skills) and [Skills & Plugins](https://learn.chatgpt.com/docs/skills-and-plugins), accessed **15 October**.

**Reasonable design inference:** DnDGPT can provide consistent presentation instructions and examples: retain the seven canonical groups and ordering, emphasize vital values, reduce repeated prose, use clear action labels, show changes and rarity labels, and progressively disclose detail. We can compare harmless examples in regular Chat and improve those instructions. Native layout reliability still needs testing; an instruction is not a pixel-exact rendering contract.

**Research limit:** no public native Intelligent UI API for registering components, applying our own CSS/theme, modifying existing native response DOM, or pinning a generated native panel was found in the first-party sources reviewed. That is not proof that prompting cannot improve its appearance, or that such an API can never exist. We should promise controllable content and tested presentation conventions, not a replacement ChatGPT skin.

**Custom MCP App:** here we author the component's HTML, JavaScript and CSS inside its iframe; we do not style ChatGPT's outer interface. The [MCP UI guide](https://developers.openai.com/plugins/build/chatgpt-ui) documents this separation, the MCP Apps bridge and optional component libraries. It also says to keep tools useful without UI and to store cross-session data in authenticated server-side storage instead of relying on `localStorage` for core state. Accessed **15 October**.

“Cooler” can mean better hierarchy, spacing, status indicators, icons, readable meters and responsive detail views. The [UI design guidelines](https://developers.openai.com/plugins/concepts/ui-guidelines) favor system typography and colors, restrained brand accents, accessible contrast and uncluttered layouts; arbitrary gradients, custom fonts and changing core system styling are not the recommended route. These are custom-app design guidelines, not a native Intelligent UI extension API.

## The screenshot mixes different meanings of plugin

The [2023 plugin launch post](https://openai.com/index/chatgpt-plugins/) is explicitly marked outdated. Its historical API/manifest discussion is not a capability specification for today's private DnDGPT package.

Current [plugin architecture](https://developers.openai.com/plugins/concepts/plugins) permits instructions/skills, MCP tools and optional UI resources. [Packaging documentation](https://developers.openai.com/plugins/build/plugins) describes current skill and MCP packages. [OpenAI's walkthrough](https://learn.chatgpt.com/training/walkthroughs/getting-started) explicitly says both Chat and Work can use plugins. All were checked **15 October 2026**. Capability support can still differ by surface.

Consequently, the screenshot's blanket conclusion is misleading for our goal. We have not found a supported way for a plugin to replace the native Intelligent UI renderer. We **have** found supported instructions and connected tools that can help determine what the model presents, plus a separate custom app surface. These are different degrees of control.

## The sandbox/internal architecture claims

The supplied [OpenUI teardown](https://www.openui.com/blog/how-chatgpt-intelligent-ui-works) is dated **8 October 2026** and explicitly describes reverse engineering web traffic and client code. [Bytewise's follow-up](https://bytswise.com/blog/chatgpt-intelligent-ui-how-it-works/) is dated **13 October**, with a **14 October** update; it distinguishes verified and unverified claims. Both were read as research leads. The [MindStudio article](https://www.mindstudio.ai/blog/gpt-6-intelligent-ui-chatgpt), dated **10 October**, is a secondary explainer and is not used as authority for availability or SDK support.

Following Bytewise's link reached first-party public code:

- [DIL v14 runner](https://cdn.platform.openai.com/deployments/dil/v14/runner.html): inspected **15 October**, with a restrictive CSP, including `default-src 'none'`, and a referenced runner module.
- [Referenced runner module](https://cdn.platform.openai.com/assets/dil/runner-BFRd8kCb.js): inspected **15 October**, containing worker creation, global hardening and timeout/quarantine machinery.

This corroborates a sandboxed implementation snapshot. It does **not** establish a supported integration API, comprehensive security guarantees, that every client uses this exact artifact, or that loops are categorically removed. The public code contains controlled evaluation machinery; “all dynamic evaluation is impossible” is too broad. The screenshot's claim that these internals by themselves prove no plugin can influence response design does not follow. We will not build DnDGPT against undocumented DIL/runner internals.

## PiP documentation has unresolved scope differences

The [UI guidelines' PiP section](https://developers.openai.com/plugins/concepts/ui-guidelines#picture-in-picture-pip) describes a floating ongoing-session view, including games, which remains until dismissal/session end and then returns inline. It cautions against overloading that small view. This is a design description, not account-specific acceptance.

The [plugin UI reference](https://developers.openai.com/plugins/reference) documents `window.openai.requestDisplayMode` for inline/PiP/fullscreen; mobile may present PiP as fullscreen. An API request is not proof that the requested display mode was granted.

Meanwhile, the official [OpenAI MCP Extensions specification](https://github.com/openai/mcp-extensions/blob/main/docs/spec.md#platform-support) says its launch support table treats web as Work and excludes classic ChatGPT. Its [display-mode section](https://github.com/openai/mcp-extensions/blob/main/docs/spec.md#display-modes) says inline/fullscreen are supported, not PiP. Its scope cannot be expanded into a universal ordinary-Chat prohibition, especially after a regular-Chat MCP App actually rendered. Conversely, the generic PiP documentation cannot override the live result into a success.

All three sources were checked **15 October 2026**. Their overlapping names and different scopes leave regular-Chat floating support insufficiently specified. Use advertised capabilities, returned host context and actual visible behavior. [Official extension patterns](https://github.com/openai/mcp-extensions/blob/main/docs/patterns.md) similarly recommend capability checks and host-provided display controls.

## Additional lead: `thesysdev/open-intelligent-ui`

Checked **15 October 2026**. The [repository README](https://github.com/thesysdev/open-intelligent-ui#readme) explicitly describes an independent recreation, not an OpenAI-affiliated project. It recreates a similar experience **inside an application we host**; it does not register components in ChatGPT's native Intelligent UI.

The implementation confirms the distinction. [`src/app/page.tsx`](https://github.com/thesysdev/open-intelligent-ui/blob/main/src/app/page.tsx) creates its own `AgentInterface` and sends requests to its own `/api/chat`. [`src/app/api/chat/route.ts`](https://github.com/thesysdev/open-intelligent-ui/blob/main/src/app/api/chat/route.ts) calls Thesys Gateway by default, or a configured OpenAI-compatible endpoint, including a local Ollama server. Those are model-backend calls, not use of the signed-in user's regular ChatGPT Chat conversation or Plus entitlement. The code uses OpenUI's documented library APIs, not the private OpenAI DIL runner.

[`package.json`](https://github.com/thesysdev/open-intelligent-ui/blob/main/package.json) requires Node >=24 and includes Next.js, React, OpenUI, Zod, the OpenAI client, mapping/chart-related dependencies and development tooling. Running generated chat requires the Next server plus a configured model backend; remote service cost depends on that provider. The README offers a key-free static `/gallery` and a local-model route. Neither is a hosted ChatGPT plugin or proof of PiP support. No installs or model requests were made for this research.

Useful design references include the [component catalog](https://github.com/thesysdev/open-intelligent-ui/blob/main/src/lib/library.ts), [light/dark design tokens](https://github.com/thesysdev/open-intelligent-ui/blob/main/src/lib/components/theme.css), and [explicit interaction examples](https://github.com/thesysdev/open-intelligent-ui/blob/main/src/lib/prompt-options.ts). We can learn from visible hierarchy and working-control patterns. Its [chat storage](https://github.com/thesysdev/open-intelligent-ui/blob/main/src/lib/chat-storage.tsx) saves to browser `localStorage`; it is not the authoritative authenticated game database required here.

**License scope is unresolved for the demo itself:** the [complete repository tree](https://api.github.com/repos/thesysdev/open-intelligent-ui/git/trees/main?recursive=1), tree `248b9766553f571941a3ac32c552e2a86c554542`, had 94 paths, no `LICENSE`/`COPYING`, and the package had no `license` field. The separate upstream [OpenUI repository has an MIT license](https://github.com/thesysdev/openui/blob/main/LICENSE); that does not establish a license for every file in this demo. Confirm the demo's own reuse terms before copying its implementation.

**Recommendation:** use it as a design/research reference. Adopting its entire chat wrapper would change the requested product and introduce another generation backend. Porting selected presentation ideas into our own MCP App is a separate possible task; it would still need the supported MCP bridge and actual host acceptance, and would not unlock native ChatGPT styling or PiP.


## Actual test evidence and limits

These are observations supplied by the active browser-test run on **15 October**; this research task did not repeat the browser interactions. Detailed evidence belongs in [CLIENT_ACCEPTANCE.md](CLIENT_ACCEPTANCE.md).

| Probe | Observed | What it does not establish |
|---|---|---|
| Temporary public dummy-data MCP connection | ChatGPT accepted the server. | Production OAuth, account isolation or a connection to the original DnDGPT engine. |
| Fresh conversation with Chat visibly selected | MCP App rendered and its clock refreshed. | Floating PiP, durable game saves or full rules coverage. |
| Standard `ui/request-display-mode({mode:'pip'})` | Request was accepted; host-reported mode stayed `inline`. | Universal lack of PiP support across all clients/APIs. |
| MCP App `ui/message` | Exact assistant acknowledgement `PiP test message received.` appeared and survived page reload; no separate visible user prompt appeared. | The same visible prompt behavior as a native Intelligent UI button, or a database commit. |
| Earlier native Intelligent UI button | Produced a visible user prompt in the conversation. | MCP App button behavior or PiP capability. |
| Later `window.openai.requestDisplayMode` compatibility card | Follow-up test returned `inline`; no floating view. | Universal client non-support. |
| **Open app in tab** | A separate pane held the same dummy iframe, local status and live clock through a completed reply and Chat scrolling. | Real game-state synchronization, browser-restart persistence or external-client availability. |

The first probe was removed after research ([cleanup screenshot](test-results/pip-probe-cleanup.jpg)). A later temporary dummy-only connection supplied the follow-up results above and the seven-panel companion sample. It runs locally behind a temporary tunnel for inspection; the original private DnDGPT plugin release remains unchanged. No campaign data was used. Current evidence is in [ui-live-acceptance.json](test-results/ui-live-acceptance.json); [pip-probe-live.json](test-results/pip-probe-live.json) retains the earlier test's limits.

## Recommended combined presentation and next acceptance gate

This is a **proposal**, not a claim of a finished experience:

1. Keep native Intelligent UI and narration as the main regular-Chat experience. Improve its presentation through a separate, small instruction/template layer while retaining the full **edition-1.0 rulebook and hardener** unchanged. Test neutral sample responses before adopting a style.
2. Use one authoritative engine/database for facts and committed actions. Return a versioned snapshot usable by both conversational responses and the custom view. Treat uncommitted previews, approved actions and saved outcomes distinctly.
3. Design the optional view as a compact status companion covering the same seven canonical groups, with summaries and expandable detail. Keep choices/narration in the conversation. Any custom-app action needs an explicit, accurately labeled path into chat or the approved engine workflow.
4. Use the tested app-pane path for a constant companion in this client, with an inline fallback. Only call another view PiP after it actually floats. Keep session-long mounting, browser-restart restoration and database persistence as separate acceptance claims.
5. Once the presentation choice is settled, test the authenticated engine round trip in that same Chat surface: read, preview, explicit approval, at-most-once commit, reread and narration, then reconnect/restart recovery. A dummy clock or chat acknowledgement cannot substitute for this.

Do not rewrite the rulebook around an unproved host capability, silently migrate gameplay into Work, or add separately billed model narration. An attractive conversational UI and durable game data can be useful independently of the floating-view outcome.
