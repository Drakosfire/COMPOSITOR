# One-shot benchmarks and gold review

Status: benchmark design for review; no accepted COMPOSITOR gold or measured quality is claimed.

## Separate suites and shared composition checks

Maintain one suite for *Of Conks & Cons* and one for *A Wild Sheep Chase*. Each suite has its own source manifest, gold version, coverage accounting, results, and limitations. Report results separately so a strong result on one source cannot hide a weak result on the other.

Add integration cases over the two packages, Eldyrwild, and a blank World. These complement source-specific scores; they do not replace them. Keep all private source bytes and derived source-specific gold in authorized private storage. Public Git may hold the protocol, schemas, synthetic/open fixtures, and source-safe summaries.

## Gold-authoring roles and independence

Assign a distinct authoring subagent to each one-shot. Each reads the exact source and shared evaluation rubric, supplies source-cited expectations, and records ambiguity and acceptable alternatives. Authors must not generate expected answers by copying the pipeline result being scored.

The parent agent reviews both suites directly against their sources. A separate challenger may inspect missing coverage, contradictions, or workflow assumptions. Separate agents reduce correlated author mistakes but are not human review or proof of independence by themselves. Record who authored, challenged, and adjudicated each case; call human review human only when it actually occurred.

Existing manufactured gold and product-derived answers are prior proposals. Check them against original evidence before adoption. Pin raw and normalized source separately: a human-cleaned Markdown experiment does not demonstrate automatic PDF recovery. Layout-dependent expectations and copied numerical fields require checks against the original source where normalization could have changed their meaning.

## Iterative review and freeze

1. Pin source version/digest and processing provenance before authoring. Enumerate source sections, output categories, and supported tasks.
2. Author expected resources, relationships, audience restrictions, procedures, unresolved outcomes, and task cases. Account for omitted/reference-only material explicitly.
3. Parent review verifies each critical expectation against its cited source, checks coverage and contradictions, and records findings with severity and evidence. Workflow expectations beyond source meaning are labeled evaluator-authored requirements.
4. The author resolves findings; the parent reviews the changed gold and affected cases again. Preserve review decisions and outstanding limitations.
5. Freeze a suite only when no known defect invalidates its declared scope. Mark ambiguous cases and acceptable alternatives rather than inventing a single answer. Declare partial coverage as partial.
6. Score ingestion against the frozen version. Gold changes after observing outputs require independent source verification, a new version, and comparable rescoring; do not repair gold merely to agree with a favored method.

"Basically flawless" means trustworthy expectations for declared coverage, with no known critical gold error. It is not a claim of exhaustive correctness. If review stalls on a genuine ambiguity, record or exclude that scored claim explicitly while preserving the material as unresolved. Do not loop until reviewers happen to agree.

## Minimum case record

Each case needs a stable identity; suite and source revision; a reversible evidence locator; category and task; source-derived versus evaluator-authored expectation; acceptable alternatives; forbidden outcomes; audience and query scope; severity; review status; and rationale. A digest protects identity but cannot replace a usable source locator.

Cases involving rules also name the applicable edition/revision and binding context. Publication date or a familiar rule name is not enough to establish edition compatibility. Preserve custom modifications to referenced rules instead of replacing them with the ordinary definition. Cases involving adaptations name the source claim, authored change, and expected attribution. Cases involving assets distinguish a reference from available bytes and record required audience-safe variants.

## Coverage obligations

For both sources, inventory the applicable categories and explicitly mark those absent:

- Narrative, setting, locations, people, groups, items, and meaningful source prose.
- Identities, aliases, relationships, repeated appearances, and participant quantities without accidental entity merging.
- Alternate hooks, conditional developments, procedures, sequences, encounter outcomes, and possible versus observed events.
- Mechanics references, typed values, qualifiers, conditions, exclusions, and exact rule bindings where in scope.
- Tables and selection semantics; assets and references; player-visible versus GM-only information.
- Worldbuilding adaptation, planning preparation, and play-time lookup/presentation tasks.
- Missing evidence, uncertainty, unsupported representations, and content intentionally kept for reference.

Review high-confidence exclusions and non-extracted sections as well as emitted output. A clean artifact with important content missing is not a high-quality ingestion.

## Workflow and composition witnesses

Apply the accepted [Composition contract and assembly witness](CONTRACT-composition.md). Cover source/adapted packages, linked/bundled dependencies, both save forms and reload equivalence, and rule edits whose dependent updates require acceptance. Saving and loading drafts with unresolved dependencies or pending proposals must preserve available content, visible limitations, and the separation of proposed and accepted changes. Per-use readiness is evaluated independently of draft loadability.

Worldbuilding cases should show original and adapted claims, explicit cross-source connections, and additions to a blank World through its owning boundary. Planning cases should produce usable preparation from the selected package's participants, situations, references, and dependencies. Playing cases should exercise retrieval and presentation of relevant content with audience restrictions intact.

Composition cases must cover each one-shot alone, both together, Eldyrwild alone and with packages, and a blank World receiving explicit authored additions. Check scoped queries and queries across the active set. A namespaced union must not infer identity equivalence merely from matching names.

Load/unload tests check subsequent retrieval, cached projections, model context assembly, and dangling dependencies. Loading is not automatic World publication; unloading is not source deletion. Reloading must not create duplicate persistent imports or erase prior authorized adaptations.

Rule interaction cases check that a statblock and Rules Lawyer open the same bound source/version and applicable local amendment. Missing, stale, unsupported, or conflicting bindings cannot present as verified information. Rules adjudication beyond simple lookup needs its own declared facts and dependency coverage.

## Quality and reporting

Report source fidelity, completeness, relationship/identity correctness, audience correctness, binding validity, practical task success, and repair burden separately. Include denominators, unsupported/unresolved outcomes, confidence in review, and per-source failure examples in the private report. Record model calls, costs, automated rounds, human/agent interventions, and recipe engineering effort.

Proposed severity rubric to freeze with the case inventory:

- **Critical:** audience or inactive-source leakage; fabricated source authority; silent source/edition substitution; unintended World mutation; destructive identity merging; a materially wrong binding advertised as verified.
- **Material:** a missing or distorted resource, relationship, procedure, or dependency that prevents or substantially misleads a declared user task.
- **Minor:** a disclosed presentation or organization defect that leaves meaning and the declared task usable.

Acceptance requires no known critical failure within evaluated scope. Useful packages may retain explicitly bounded material gaps or minor defects if those gaps do not invalidate the tasks claimed ready. Human assessment of actual preparation/play usefulness must complement automated cases before claiming that experience has been proven. Numeric thresholds and acceptable repair effort remain to be agreed before scoring; do not invent passing thresholds after a run.

Preserve the unedited first-ingestion result for a frozen recipe. Report later repair separately. A fixed multi-pass recipe is permitted, but its internal validation/repair rounds and provider calls are part of its measured cost. Retuning on visible gold produces a new development treatment. Hold out cases during tuning and use a new source later to assess transfer beyond these two documents.

## Readiness records

Record source readiness in the private benchmark store: dated inspections, source manifests and digests, extraction/normalization provenance, prior-target discrepancies, review decisions, and unresolved source dependencies. Verify those records before freezing each suite. Keep private corpus metadata and inspection reports outside public Git unless their publication is explicitly authorized.

Neither suite currently has accepted COMPOSITOR gold. Both selected titles are established; pin each exact source revision and extraction provenance before gold authoring. A smaller focused regression fixture complements these suites but cannot substitute for either adventure's benchmark.

## A Wild Sheep Chase: source and recovery plan

The selected second adventure is *A Wild Sheep Chase*. [Winghorn Press](https://winghornpress.com/adventures/a-wild-sheep-chase/) offers a free download and links to its [v2 PDF](https://winghornpress.com/wp-content/uploads/2018/02/the_wild_sheep_chase_v2.pdf). The PDF credits identify original material as copyright 2016 Richard Jansen-Parkes and publication under the Dungeon Masters Guild Community Content Agreement, alongside third-party copyrighted material. This inspection establishes free availability, but has not established a general redistribution license for the text or artwork. Keep source bytes and derived gold private under the repository's source-handling policy; use project-authored or explicitly open material for the public fixture.

Compare the selected PDF with existing processed Markdown and recovered assets before choosing another extraction pass. Record their relationship and any manual cleanup privately. The publisher's current PDF is a reference for identification, not an automatic replacement for the selected local revision. Render pages or extract embedded images directly where those operations suffice. Use the existing DeepSeek OCR tooling for deficient text/layout recovery when needed, verifying local runtime readiness or an explicitly scoped API run first. Score PDF recovery separately from semantic processing of supplied Markdown.
