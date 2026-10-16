# DnDGPT — Persistent Conversational RPG Companion

**Deon Holo** · [GitHub](https://github.com/DeonHolo/DnDGPT)

A ChatGPT-integrated RPG companion with an authenticated Python backend and a persistent, seven-chapter campaign dashboard. ChatGPT handles the story and adjudication; the service stores character, abilities, allies, inventory and world state.

**Current stack:** Python · FastAPI / ASGI · JavaScript / HTML / CSS · MCP / MCP Apps · Auth0 OAuth 2.0 / PKCE · Appwrite Functions / TablesDB · Git / GitHub

## Resume-ready wording

**One line**

Built a cloud-hosted RPG companion connecting ChatGPT to authenticated campaign storage, reusable game tools and an interactive dashboard.

**Project entry**

**DnDGPT | AI-Assisted Full-Stack Project**

- Built a seven-chapter dashboard inside ChatGPT, backed by OAuth-protected MCP tools for campaign updates, character records, inventory and world history.
- Migrated a Windows-hosted FastAPI/SQLite prototype exposed through ngrok to Appwrite Python Functions and TablesDB, using GitHub Student Developer Pack resources to remove the PC dependency for hosted games.
- Implemented account ownership checks, transactional state updates, optimistic concurrency, event history and idempotent dice receipts to handle retries and preserve campaign continuity.
- Integrated GitHub-triggered deployments from `main` and validated changes through automated tests, browser checks and live ChatGPT sign-in/save/reopen flows.

**Optional AI-focused bullet**

Directed AI-assisted implementation and debugging with Codex and ChatGPT, designing GM instructions and tool workflows, reviewing generated changes, and checking results against tests and live client behavior.

## How the architecture evolved

| Stage | Stack and delivery | What changed |
| --- | --- | --- |
| Local prototype | FastAPI + SQLite on Windows; temporary tunnels, then a fixed ngrok address; Auth0 sign-in | Proved the ChatGPT tools and reusable dashboard. The PC and tunnel had to stay online. |
| Hosted version | Appwrite Python Functions + transactional TablesDB storage; stable HTTPS endpoint; Auth0 retained | New hosted games work without the creator's PC or ngrok. Resources come from the GitHub Student Developer Pack's Appwrite education offer. |
| Current delivery | GitHub repository, reviewed branch merge, `main` as deployment source, `dndgpt-app/**` path filter | Backend and dashboard changes deploy from source. Packaged GM skills/rulebooks have a separate versioned release step. |

Auth0 and Appwrite have different jobs: **Auth0 handles player identity; Appwrite runs the service and stores campaign records.** ngrok was the bridge to the local prototype.

GitHub-triggered deployment is in place. Automated GitHub test CI is not configured; relevant tests currently run before pushing.

## Skills demonstrated

| Area | Resume-friendly skills | Project evidence |
| --- | --- | --- |
| Backend engineering | Python, FastAPI, ASGI, API design, request validation | Shared authenticated HTTP/MCP service and Appwrite runtime adapter |
| Data and reliability | SQLite, managed databases, transactions, optimistic concurrency, idempotency | Versioned records, account ownership, retry-safe updates and roll receipts |
| Security and integration | OAuth 2.0, PKCE, JWT validation, authorization boundaries | Auth0 sign-in and per-user access to campaign data |
| Cloud delivery | Serverless deployment, environment configuration, GitHub integration, Git branching and pull requests | Appwrite Functions/TablesDB migration and deployment from `main` |
| Frontend engineering | JavaScript, semantic HTML, CSS, responsive UI, accessible navigation | Dark fantasy dashboard, resource meters, subtabs and expandable details |
| Testing and debugging | Automated regression tests, browser testing, integration testing, live acceptance checks | Separate local, simulator, hosted backend and actual ChatGPT checks |
| AI application integration | MCP tool design, structured state updates, reusable tools, human approval flows | ChatGPT GM connected to persistent state and genuine Python rolls |
| AI-assisted development | Prompt engineering, task decomposition, iterative specification, generated-code review | Requirements and implementation refined with Codex/ChatGPT, screenshots, test results and user feedback |
| Product and systems design | Scope prioritization, rule specification, state modeling, technical documentation | Shift from a complete rules-engine goal to a playable chat-led system with a durable dashboard |

## What the AI work actually involved

- Turning natural-language requirements into concrete tool contracts, UI behavior and acceptance criteria.
- Writing and refining the GM skill, rulebook guidance and originality constraints for generated classes and abilities.
- Connecting model tool calls to saved state, with clear boundaries around approvals, retries and gameplay actions.
- Using AI coding assistants to implement, inspect and debug changes, then verifying the output rather than treating generated code as proof.
- Using official documentation and service tools to diagnose deployment, authentication and runtime integration issues.

Describe this as **AI-assisted software development and AI application integration**. It does not involve training a model or operating a custom inference service. Normal narration runs in the player's ChatGPT session.

## Interview explanation

“I started with an RPG dashboard running on my PC behind ngrok. I connected it to ChatGPT through MCP, used Auth0 for player sign-in, then moved the backend and saves to Appwrite with my GitHub Student Developer Pack. The main challenge was making chat-driven updates persist safely and display consistently across retries and reopened sessions. I used Codex and ChatGPT throughout development, with tests and live checks to validate the changes.”

## Evidence boundaries

Cloud-hosted private beta as of 2026-10-17. The creator's authenticated ChatGPT save/display/reopen flow and hosted fixture checks have passed. Independent-player acceptance and public-directory publication are still separate steps.

Do not claim measured player capacity, guaranteed uptime, latency improvements, complete executable rule coverage or model-training experience. Private credentials, account bindings, saves and playthrough evidence are excluded from the public repository.
