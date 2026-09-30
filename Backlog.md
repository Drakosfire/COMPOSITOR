# COMPOSITOR — Backlog

Project-specific learnings, ideas, and follow-ups. Accepted design authority lives in the linked design documents.

**Status legend:** `IDEA` → `READY` → `DOING`. Terminal states (`DONE` / `DROPPED`) are archived to `Backlog-DONE.md`.

## [READY] Composition assembly and round-trip witness — captured 2026-09-29

**Context:** Operator-canonized five-question Composition design.
**Insight:** Source and adapted packages share a contract; dependencies can be linked or bundled, adaptations can use changes or snapshots, dependent updates require review, and drafts remain usable.
**Action:** Define a bounded schema and assembly implementation for the accepted read/query/edit/review/save/reload witness. This is a design follow-up, not authorization for live provider runs or cross-owner migrations.
**Surfaces when:** Composition schema, assembly, dependency resolution, impact review, draft persistence, save/export/reload.
**Refs:** [Canonical Composition contract](Docs/Design/CONTRACT-composition.md), [objectives](Docs/Design/OBJECTIVES-compositor.md).

## [READY] Keep PR handoffs as evidence-based breadcrumbs — captured 2026-09-29

**Context:** Operator-requested experiment with large coherent PR bites and concise handoffs.
**Insight:** A successor handoff is most useful when it carries the witness actually proven by the preceding PR, plus exact pins and unresolved findings. Proposed future handoffs must stay editable as evidence changes.
**Action:** At each dispatch, pin current refs, owner and data/provider scope; after each PR, update the next handoff with measured results and recut it with PRIME if a new capability or owner boundary appears.
**Surfaces when:** Composition PR stack, implementation dispatch, successor handoff, cross-repository contract, benchmark scoring.
**Refs:** [Draft PR stack](Docs/Roadmaps/ROADMAP-composition-pr-stack.md).
