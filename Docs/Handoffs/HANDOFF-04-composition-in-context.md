# Draft handoff 04 — composition in context

Status: **proposed, unassigned**. Roadmap: [Composition PR stack](../Roadmaps/ROADMAP-composition-pr-stack.md). Requires pinned packages and current owner contracts.

**Pin at dispatch:** COMPOSITOR package API and adventure revisions; current DungeonMind projection/source contract, WorldKeeper prepare/publish contract, and Buddy interaction owner contract; Eldyrwild test revision, permitted private-data handling and provider exposure, and isolated World/test state. Name owner-repository PRs or blocked dependencies, merge order, the end-to-end witness owner, and repository-specific write scopes before implementation.

**Deliver:** a consumer integration that selects and unloads packages, queries one source or the active set, and authors traceable adaptations into a blank or existing World through the governed owner path. Preserve source identity, active selection, audience, and review state. Owner implementation changes live in their own repositories and PRs if needed.

**Prove:** through the named real consumer path, load either adventure, both, Eldyrwild alone and alongside them, and a blank World; perform scoped and combined queries; adapt and review a change; unload/reload without content leakage, implicit identity merge, duplicate import, or World publication from package selection alone. Check caches and subsequent model context after unload. A COMPOSITOR-only mock is a contract check, not this acceptance witness.

**Boundary:** COMPOSITOR supplies packages and integration contracts. DungeonMind owns durable graph authority, WorldKeeper coordinates exact governed change, and Buddy owns product surfaces. This handoff does not authorize a product UI redesign or bypass publication review.

**Hand onward:** a verified consumer contract, supported operations, timing/scale observations, and explicit rule-binding gaps. Escalate owner contract collisions to PRIME rather than widening COMPOSITOR authority.
