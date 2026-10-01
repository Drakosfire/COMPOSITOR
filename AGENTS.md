# Agent operating policy

COMPOSITOR owns the ingestion and processing program that turns user-supplied documents into faithful, source-linked, portable **Compositions**, usable for Worldbuilding, Planning, and Playing. Rules extraction and binding are part of this broader responsibility. This file is durable repository guidance; the current operator direction and bounded assignment provide work-specific authority.

## Ecosystem execution core — overmind-agent-core-v1

These rules follow the shared DungeonMind ecosystem core. Repository-specific rules below add constraints without weakening it.

1. **Re-anchor before action.** Check the current remote default branch, relevant open PRs, active work, and the exact authority ref before editing, reviewing, or merging. Local state and old chat context are not current authority.
2. **Respect ownership boundaries.** DungeonOverMind owns cross-repository architecture and sequencing. Runtime and product changes belong to their owning repositories. Name the contract and owner when a proposal crosses repositories.
3. **Use bounded, portable handoffs.** A handoff may live on a branch, PR, or other durable pinned ref. Its location alone does not activate it. Execution needs explicit authorization, a pinned authority, scope, and write/runtime ownership.
4. **Finish authorized work to a reviewable result.** For an active implementation assignment, inspect the cumulative diff, verify the owning boundary, commit, push, and open or update its assigned PR. A local draft is not completion.
5. **Treat merge as separate authority.** Do not merge merely because a PR is open, reviewed, or green.
6. **Use isolated Git lanes.** Do not develop on local `main`. Use a branch or worktree, and account for shared files, data, services, caches, and provider budgets as well as Git conflicts.
7. **Keep one slice bounded.** Deliver one independently useful capability per assignment. Return a second capability, public contract, or unexpected scope expansion for a new decision.
8. **Verify at the owning boundary.** Tests and review must exercise the claimed behavior. Schema-valid output alone does not prove source fidelity or a usable Composition.
9. **Settle after merge.** Re-anchor and update any mutable authority that the merge made stale. Preserve unique evidence; let Git history carry superseded process drafts.

## Activation and authority

- Follow the current operator's explicit direction for the assigned scope. Record material revisions to earlier proposals in the repository; do not let an outdated proposed handoff override later operator instructions. The objectives in `Docs/Design/OBJECTIVES-compositor.md` capture the current direction.
- Before running an implementation or live experiment, establish its exact source/ref, expected outcome, write/runtime/data scope, and provider/spend limits where applicable. A PR, merge, or design document alone does not supply missing execution scope. PRIME coordinates cross-owner dispatch and production transitions.
- Authorized design and benchmark work can proceed within its stated scope. It does not by itself authorize paid provider runs, production publication, or bulk re-ingestion of existing corpora.
- On dispatch, read current DungeonOverMind architecture/ownership and the current owner contracts. Re-check active work in RulesIngestion, GenerationEngine, DungeonMind/WorldKeeper, DungeonMindBuddy, and relevant RulesEngine lanes. Treat design documents as proposals until their acceptance and implementation are verified.
- Keep slice-specific paths, base/head refs, acceptance checks, exclusions, collisions, and budget in the active handoff or launch record. Do not put transient status or guessed task IDs into this policy.

## Research invariants

- The delivery objective is competent to better-than-good first ingestion into packages usable for Worldbuilding, Planning, and Playing. Two real one-shot benchmarks drive evaluation. A small public JSON fixture supports reproducible engineering checks; passing it alone does not establish product success.
- Preserve exact source identity, stable anchors, resource relationships, audience scope, and authored adaptations. Loading packages together must not silently merge identities, publish source claims as World truth, or expose inactive/unauthorized content.
- Make `resolved`, `reference-only`, `unsupported`, and `unresolved` outcomes explicit. Missing input, source revision mismatch, broken references, and audience errors must fail visibly. Never turn uncertainty into an invented rule or source claim.
- Keep deterministic replay free of hidden provider calls. Live model experiments require separate opt-in data handling, model/provider pins, call and round caps, spend limits, and receipts. Budget exhaustion terminates the run.
- Use a distinct gold-authoring subagent for each one-shot and iterative parent review against the actual source, following `Docs/Design/BENCHMARKS-one-shots.md`. Agent agreement alone is not source verification. Freeze gold before scoring, record ambiguity, and distinguish first-ingestion results from repairs informed by benchmark outcomes.
- Do not commit user document bytes, personal campaign material, credentials, or unlicensed rulebook content by default. Verify rights and permitted storage/provider handling before any such use. An open-source repository is not permission to publish user inputs.
- Preserve the distinction between research evidence and production authority. A Composition is not automatically executable mechanics, a governed World write, campaign canon, or a published product resource.

## Ownership and scope

- COMPOSITOR owns ingestion and processing design, experiments, pipeline implementations, source adapters, semantic resource production, package preparation, and evaluation. Reuse the existing ingestion research and tooling. Moving maintained components or replacing existing ingestions requires a named migration; the ownership direction does not silently transfer occupied implementation paths.
- GenerationEngine retains reusable provider execution; DungeonMind owns durable Adventure/Rules space IDs, source admission, governed graph revisions, and revision-pinned evidence reads; WorldKeeper retains governed World publication; Buddy retains product surfaces and workflows. COMPOSITOR produces reviewed contribution candidates and package selection/export representations through explicit contracts. Its local JSON and SQLite stores are research/replay stores, not durable graph authority.
- Consume pinned owner contracts. Return a proposed production contract or promotion to the owner and PRIME instead of importing lab internals into a product or copying an owner runtime into this repository.
- When the Rules track begins, include a bounded Drools execution witness owned by RulesEngine or an agreed adapter, outside DungeonMind. That witness does not select a production rules engine. A general plugin framework, web dashboard, autonomous full-book formalization, and production publication remain later possible assignments.
- A fresh authorized researcher should be able to replay the named baseline from exact source/evidence and dependency pins, see the supported scope, and observe explicit failures. If this cannot be shown, report a failed or incomplete witness rather than calling the baseline complete.

## Git and handback

- Keep local `main` free. Start from the current remote default branch when it exists; an empty repository may use an isolated bootstrap branch. Do not remove or move the checkout currently open in an editor.
- Before a PR, review the full base-to-head diff and run checks relevant to changed files. For documentation-only work, at least check whitespace, links/paths, and claims against their named authorities.
- Return the exact repository, branch, base/head, changed paths, commands and results, source/fixture identities, supported scope, negative findings, current holds, and proposed next bounded slice. Distinguish author-local, CI, and independent review evidence.
- Stop the affected action when its specific authority, source identity/handling, or spending scope is missing; report the missing prerequisite to the operator. Current explicit operator authorization applies to its stated scope. Return cross-owner collisions, production transitions, and separately scoped capabilities to PRIME for coordination instead of expanding the assignment silently.
