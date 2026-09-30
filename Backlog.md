# COMPOSITOR — Backlog

Project-specific learnings, ideas, and follow-ups. Accepted design authority lives in the linked design documents.

**Status legend:** `IDEA` → `READY` → `DOING`. Terminal states (`DONE` / `DROPPED`) are archived to `Backlog-DONE.md`.

## [READY] Composition assembly and round-trip witness — captured 2026-09-29

**Context:** Operator-canonized five-question Composition design.
**Insight:** Source and adapted packages share a contract; dependencies can be linked or bundled, adaptations can use changes or snapshots, dependent updates require review, and drafts remain usable.
**Action:** Define a bounded schema and assembly implementation for the accepted read/query/edit/review/save/reload witness. This is a design follow-up, not authorization for live provider runs or cross-owner migrations.
**Surfaces when:** Composition schema, assembly, dependency resolution, impact review, draft persistence, save/export/reload.
**Refs:** [Canonical Composition contract](Docs/Design/CONTRACT-composition.md), [objectives](Docs/Design/OBJECTIVES-compositor.md).
