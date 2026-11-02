# D&D reference implementation

Upstream: https://github.com/heffrey78/dnd-mcp

Reviewed revision: 3a82eccaaa79ede41906104ccb85141a94568af6 (2026-11-02).

Upstream package.json declares `license: MIT`; that revision contains no standalone LICENSE file and its author field is empty. The upstream checkout is retained outside this repository for evaluation. No upstream TypeScript source is redistributed in this application.

app/dnd_reference.py adapts its approach to source-scoped lookup, explicit result provenance, exact-name matching, local filtering for unsupported endpoint filters and inherited species resolution to the existing Python backend and offline public SRD cache. Referenced files: src/sources.ts, src/open5e-endpoints.ts, src/species.ts. This avoids a Node process on each turn and another player-installed connection.

Upstream's build generator is not used as authoritative DnDGPT character state. Its documented limitations include unsupported multiclass builds; DnDGPT keeps its own versioned sheet and multiclass resource arithmetic.
