# COMPOSITOR objectives and roadmap

Status: operator-established direction; acceptance design for review. Capabilities below are objectives, not implemented behavior.

## Purpose and ownership

COMPOSITOR owns ingestion and processing: taking supplied documents through faithful evidence recovery, interpretation, resource construction, validation, and package preparation. Rules extraction is one capability within that responsibility. The program must handle narrative, Worldbuilding, characters, locations, encounters, procedures, tables, assets, and meaningful reference prose as well as mechanics.

The operator's current direction extends the initial repository-foundation scope and earlier proposed lab mandate. Existing research and implementations are the starting assets. Moving maintained RulesIngestion components or replacing existing ingestions requires an explicit transition with their current owners; it does not require abandoning the broader COMPOSITOR objective.

GenerationEngine retains shared provider execution. DungeonMind/WorldKeeper retain governed knowledge and publication. Buddy retains product surfaces. COMPOSITOR supplies inspectable resources, packages, and bindings through the appropriate contracts. Rules Lawyer is a consumer/component and possibly a future Surface; its eventual UI location is open.

## Success from the user's perspective

Given either selected one-shot, a frozen ingestion recipe produces a package good enough to begin Worldbuilding, Planning, and Playing with limited, visible repair. The intended quality is competent to better than good on first ingestion. A tiny fixture or schema-valid output is insufficient evidence for that claim.

The user can:

1. Load either one-shot, both one-shots, Eldyrwild, or a selected combination; create and select a blank World through its owning boundary.
2. Query and interact with one explicitly selected source or the authorized active set, seeing where information came from.
3. Adapt a source into a World while inspecting the original and the authored changes independently.
4. Prepare locations, participants, encounters, procedures, references, and assets into usable planning material.
5. Open relevant material during play, present player-safe content, and retrieve an available rule from a statblock or Rules Lawyer.
6. Unload a package and see its content disappear from subsequent active-set results; receive explicit missing-dependency information if remaining material refers to it.

Assess package readiness for each workflow separately. Useful reference prose may satisfy a workflow without executable mechanics. Each package declares supported tasks, dependencies, unresolved issues, and known limitations.

## Sources, adaptations, rules, and projection

Preserve separate identities for source revisions, extracted resources, authored World changes, mechanics definitions, participants, presentation instances, and runtime observations. A source statement, an adventure possibility, and an event that occurred in play have different meanings.

A workspace projection combines selected sources and World context while retaining provenance. Loading two packages does not merge similarly named entities. Equivalence, cross-source links, adaptations, and overrides are explicit, reviewable assertions. Contradictions remain attributable until resolved; arbitrary precedence must not silently discard them.

Define operations distinctly:

- **Ingest:** produce artifacts from a pinned source through a recorded processing recipe.
- **Load/unload:** activate/deactivate an existing package in a workspace; preserve its stored artifacts and original source.
- **Adapt:** author a traceable addition, modification, or binding in a selected World context.
- **Save:** persist a draft or authored working material in its owning product/workspace store; saving a draft does not itself publish World truth.
- **Import/admit:** request incorporation into a selected World through its owner's validation and governance contract, keeping source and adaptation provenance.
- **Publish:** perform the World owner's explicit publication transition, with the confirmation and revision semantics that contract requires. Workspace selection and draft saves do not imply this transition.

Query scope and audience both constrain the projection. Combined queries cannot expose GM material to players or draw silently from inactive packages. An explicit request to reopen inactive material is a separate action. Context already displayed remains historical, but caches and subsequent model/query context must honor the new selection.

Rules bindings connect the relevant field, ability, condition, or procedure to an exact definition/source revision and applicable local amendments. The UI's information-ready indicator must reflect a valid binding. Missing, unsupported, edition-mismatched, or stale bindings remain visible states. Statblocks and Rules Lawyer should resolve the same binding consistently. A citation is not proof that every rule needed for broader adjudication has been recovered.

## Storage direction

Use versioned `.json` files for the small public fixture, its expected outcomes, and reproducible engineering checks. Persist private real-source experiments in a database: source identities/snapshots, run configurations, artifacts, relationships, validation results, review decisions, and model receipts.

Both forms express the same logical artifacts. Keep inputs and results of distinct runs instead of overwriting a single latest result. Separate research persistence from governed World authority. A pinned run can be exported privately as a JSON replay bundle with its dependency identities; replay performs no hidden provider calls. Media may use file/object storage with stable digests and references.

Database selection, deployment, retention, and the exact schema remain design decisions. The storage direction does not authorize connection to a shared live store or publication of private source material.

## Evaluation direction

Use separate benchmarks for *Of Conks & Cons* and the second selected one-shot. Each receives its own gold author and iterative source-grounded parent review. The [benchmark protocol](BENCHMARKS-one-shots.md) defines independence, freeze, acceptance, and regression handling.

The public fixture is a reproducibility aid. The two actual adventures are the primary capability witnesses. A composition scenario exercises both packages with Eldyrwild and a blank World, including scoped queries, adaptation, audience boundaries, and unload behavior.

High quality may include disclosed imperfections. Gold should be trustworthy within its declared scope, with explicit ambiguity and acceptable alternatives. Product results must distinguish critical defects, material repair, and minor limitations. Do not demand invented certainty from either gold or ingestion.

First ingestion uses one frozen recipe and preserves its unedited result. The recipe may contain documented bounded model passes and automated validation; retries, spend, and internal repairs are measured. Human edits or configuration changes informed by an evaluated run are reported as subsequent development/repair, not concealed inside its first result.

Repeated tuning on two adventures demonstrates competence on those benchmarks. Reserve untouched evaluation cases and subsequently test a new document before claiming general first-ingestion quality.

## Roadmap by acceptance witness

1. **Freeze the evaluation contract.** Identify both exact sources, enumerate Worldbuilding/Planning/Playing tasks, define expected output categories and defect severity, and settle the private storage choice. Resolve source handling and experiment budgets before affected runs.
2. **Establish reviewed gold.** Assign one author per one-shot. Parent review checks source claims, omissions, alternatives, and audience assumptions. Iterate until no known defect invalidates declared benchmark scope, then freeze each suite independently.
3. **Deliver a reproducible ingestion path.** Reuse prior research and tooling; establish exact input, resource, persistence, and replay contracts. Preserve and score first-run results for each adventure. Diagnose evidence recovery, semantic interpretation, assembly, and interaction failures separately.
4. **Reach useful package quality.** Improve the pipeline against the separate suites, retaining earlier results and reporting repair effort. Demonstrate the named Worldbuilding, Planning, and Playing tasks with explicit remaining gaps.
5. **Demonstrate composition and interaction.** Load either/both packages, Eldyrwild, and a blank World; perform scoped and combined queries; add adaptations; unload and reload. Validate at the real graph/product boundary rather than substituting helper-only tests.
6. **Prove shared rule interaction.** Ingest the needed rules, bind exact definitions, and show consistent statblock and Rules Lawyer retrieval, including amendments and stale/missing behavior. Integrate this with the workflow witnesses; broader mechanics execution is a separate capability.
7. **Transfer the learning to existing corpora.** Compare retrofit of compatible artifacts against re-ingestion from exact originals. Choose from quality, compatibility, review effort, and cost evidence. Preserve authored adaptations and provenance; do not overwrite an existing World merely to replace an ingestion.

These are capability gates, not a fixed number of PRs or a calendar commitment. Define bounded implementation slices as their prerequisites become concrete. Full-book processing may be economical earlier: measure a representative pass, then scale when justified. Existing retrieval benchmarks remain useful but need semantic, binding, and workflow checks for these objectives.

## Open choices

- Exact identity/revision of the second one-shot; do not silently substitute a synthetic fixture or an unrelated campaign recap.
- Database/service and isolated experimental namespace.
- Source-specific expected outcomes and named human review of workflow usefulness.
- Numerical quality thresholds, practical repair tolerance, model treatments, and run budgets, frozen before scored runs.
- Owner contracts for workspace activation, graph projection, and production ingestion migration.

Keep exact source inventories, readiness inspections, and private experiment evidence in the private benchmark store. Prior corpus work informs the design; completed COMPOSITOR benchmarks still need to be established.
