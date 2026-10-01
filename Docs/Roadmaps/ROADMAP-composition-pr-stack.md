# Composition capability PR stack

Status: **draft roadmap, PRIME reviewed as a proposed sequence**. The operator requested large coherent PR bites and concise handoffs after accepting the [Composition contract](../Design/CONTRACT-composition.md). This plan is sequencing guidance, not execution authority or a promise that these PRs will retain exact boundaries.

## Working rule

Each PR must leave one independently inspectable capability and a short handoff based on what its witness actually proved. Preserve the user-facing objective while allowing implementation choices and later PR boundaries to change when evidence requires it. A future draft handoff becomes executable only after a dispatch pins its base, source and dependency versions, write/runtime ownership, allowed data handling, and provider budget where applicable.

The existing [design PR](https://github.com/Drakosfire/COMPOSITOR/pull/1) is bite 0. It records objectives, separate one-shot benchmarks, and accepted package semantics. It is not a working pipeline.

## Proposed bites

| Bite | Coherent PR outcome | Acceptance witness | Draft handoff |
| --- | --- | --- | --- |
| 1. Package cycle | Concrete Composition model, deterministic assembly, scoped read, adaptation/impact review, both save forms, and JSON replay on a project-authored fixture. | Assemble → read/query → edit → review → save both forms → reload equivalent effective content and provenance; incomplete draft stays usable. | [Package cycle](../Handoffs/HANDOFF-01-package-cycle.md) |
| 2. Document to draft | Reuse RulesIngestion evidence recovery through an adapter to the Composition draft model, including assets, omissions, and diagnostics. | Pinned PDF and supplied-Markdown routes retain recoverable evidence and distinguish recovery failures from interpretation failures. | [Document to draft](../Handoffs/HANDOFF-02-document-to-draft.md) |
| 3. Adventure competence | One recorded recipe exercised against both selected one-shots with separate reviewed gold, first-result preservation, and task-focused reports. | Separate source fidelity and Worldbuilding/Planning/Playing findings for each adventure; repair effort and known gaps visible. | [Adventure competence](../Handoffs/HANDOFF-03-adventure-competence.md) |
| 4. Composition in context | Admit reviewed Adventure contributions to a MIND-minted space, then integrate pinned package selection, scope, adaptation, and unload through owner contracts with Eldyrwild and a blank World. | Reopen exact MIND space/revision and verify source/evidence path; load each/both adventures, query selected/active content, adapt through World governance, unload without leakage or unintended publication. Cross-space join behavior needs its own owner contract. | [Composition in context](../Handoffs/HANDOFF-04-composition-in-context.md) |
| 5. Rules interaction | Admit reviewed Rules contributions to a separate MIND-minted space and resolve exact bindings for adventure resources, statblocks, and Rules Lawyer. Bridge *Of Conks & Cons* original citations to the operator-selected 2024/5.5 target edition. | Bound rule opens with original citation and reviewed target source/version/amendment; missing, stale, and edition-mismatched bindings do not present as verified. | [Rules interaction](../Handoffs/HANDOFF-05-rules-interaction.md) |
| 6. Bounded Rules execution | RulesEngine or an agreed adapter runs a limited Drools witness using pinned rule/fact inputs; COMPOSITOR supplies source-linked candidate artifacts and evaluation cases. | Reproduce expected and counterexample outcomes with firing/result provenance, resource caps, and explicit unsupported behavior. This does not choose a production engine. | [Rules interaction](../Handoffs/HANDOFF-05-rules-interaction.md) |

Bites are ordered by dependency, not calendar. Before activating bites 4–6, name the owner-repository PRs or blocked dependencies, their merge order, and which PR proves each end-to-end consumer witness. The first Adventure path requires MIND review of `DomainContractDescriptor` and `SemanticProfileDescriptorV2`, MIND-minted space/source/evidence identities, governed materialization, and revision-pinned reads. A COMPOSITOR-only mock does not satisfy that witness. COMPOSITOR does not copy owner implementations to avoid that boundary.

## Parallel preparation and gates

Source inspection and two distinct gold-authoring tracks may proceed while bite 1 or 2 is built. Each gold suite is independently source-reviewed and frozen before its results are used for scoring or tuning. Real-source results and derived gold remain in authorized private storage; the public repository carries only permissible fixtures, protocol, code, and source-safe findings.

The private experiment database choice and isolated namespace must be settled before writing real runs. Provider calls need a pinned model, data-handling decision, call/round and spend caps, and receipts. No paid or bulk ingestion follows automatically from this roadmap.

## Recut rule

Keep the stated acceptance witness when routine implementation details change. If a witness exposes a missing package primitive, repair that primitive in the active bite and record the resulting contract revision. If it requires a new product workflow, changed owner contract, corpus migration, or materially different capability, return a bounded proposal to PRIME and revise the affected future handoff. Do not let draft handoffs silently become authority to edit another repository.

Before each dispatch, replace the draft's open pins with exact refs and current owner contracts. After each PR, write its actual result, failing cases, cost, and next dependency into the successor handoff. Merge and production publication remain separate decisions.
