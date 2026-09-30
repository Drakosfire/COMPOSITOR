# Draft handoff 01 — package cycle

Status: **proposed, unassigned**. Roadmap: [Composition PR stack](../Roadmaps/ROADMAP-composition-pr-stack.md). This is a planning breadcrumb, not an activated implementation assignment.

**Pin at dispatch:** accepted [Composition contract](../Design/CONTRACT-composition.md), current COMPOSITOR base/head, public fixture license, and any dependency contract consumed. Record the exact write/runtime scope and owner.

**Deliver:** a concrete versioned package representation and an end-to-end deterministic cycle on project-authored JSON. Include identity, lineage, resources, relationships, audience, exact dependencies, accepted changes, pending impact proposals, and per-use readiness. A rule edit must identify affected resources for review. Support changes over a pinned original and a complete snapshot. Keep storage behind a logical boundary usable by the small JSON fixture and the later private database.

**Prove:** assemble → scoped read/query → direct edit → affected-resource proposal → acceptance → save each form → reload equivalent effective content and provenance. Save and reload an incomplete draft with a pending proposal and missing dependency; the original revision remains intact. Exercise audience denial and wrong dependency revision. Replay makes no provider call.

**Boundary:** COMPOSITOR package semantics and test fixture only. Do not move RulesIngestion code, connect a shared DB, implement Buddy UI, or publish a World. The concrete schema and algorithm are implementation choices if they satisfy the accepted witness.

**Hand onward:** versioned package API and fixture, exact invariants and gaps, commands/results, and any change needed in the next evidence adapter. Recut with PRIME if the witness cannot fit the accepted contract without a material semantic revision.
