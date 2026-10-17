# Hosting and deployment

Maintainer notes for the hosted DnDGPT service. Players should use [Start playing](../README.md#start-playing).

The Python Function serves the backend and the MCP App dashboard resource. A separate website is optional. See the [Appwrite deployment guide](../dndgpt-app/APPWRITE_HOSTING.md) and [authentication setup](../dndgpt-app/AUTH0_SETUP.md).

**Deployment flow:** develop locally → run relevant tests → push to `main` → Appwrite builds changes under `dndgpt-app/**` → the stable domain serves the new deployment.

Automatic GitHub test CI is **not configured**. Appwrite provides automatic deployment; tests currently run before pushing. GM instructions and packaged rulebooks need a new plugin version and distribution step. Backend/dashboard changes keep the same server address. ChatGPT can retain older dashboard HTML: refresh the app's tools in Settings, then reload the ChatGPT page to fetch the new layout.

**Current status:** cloud-hosted private beta. Real Appwrite fixture checks and the creator's ChatGPT sign-in, save, display and reopen flow have passed. Independent-player installation and public-directory publication remain separate acceptance steps.

For local development and packaging your own integration, see [Developer setup](../README.md#developer-setup).
