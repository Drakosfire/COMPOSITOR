# Contextual visibility for Composition resources

Status: **provisional design checkpoint; no schema or API authority**. Base COMPOSITOR `b3e7b0e2f647ec60925ce11aa8a4484c05ee0e9e`. This document uses only a project-authored example. It does not change the accepted package contract, implement policy evaluation, or authorize an owner repository edit.

Authority readbacks: the current [COMPOSITOR package API](../../src/compositor/package.py) and [public fixture](../../fixtures/public/package-cycle.json); [WorldKeeper's current boundary](https://github.com/Drakosfire/WorldKeeper/blob/c1aeb157e14f2c07036e6346e93b2e47a228f387/Docs/Architecture/BOUNDARY-dungeonbuddy-worldkeeper-dungeonmind.md) at `c1aeb157e14f2c07036e6346e93b2e47a228f387`; and MIND exact-read behavior reviewed at `619329c2c8586572ffd04558a79b3555c2ca3764`. These are read-only observations, not leases for an owner change.

Review checkpoint: ARCHITECTURE confirmed the pure WorldKeeper evaluator is a proposal requiring a boundary amendment and requested the fail-closed witnesses below. MIND confirmed the absence of an accepted product fact snapshot and reviewed the proposed missing envelope. Buddy delivery-boundary review is pending. PRIME authorized only this documentation draft and holds any schema or runtime implementation.

## Problem and public counterexample

COMPOSITOR currently stores `audience: GM | PLAYER` per resource. `query(content, term, audience=...)` has no viewer, character, scene, or World revision input. In the public synthetic example, the source author wants a bell description to be player-facing **if that character can hear it**. A local smoke over project-authored data observed one player hit for the `PLAYER` label and zero for the `GM` label. Because hearing cannot be supplied to this API, each static result applies in both contexts:

| Resource label | Hearing available: contract-allowed / observed | Hearing unavailable: contract-allowed / observed |
| --- | --- | --- |
| `PLAYER` | 1 / 1 | 0 / 1 — premature disclosure |
| `GM` | 0 / 0 — hard ceiling applies | 0 / 0 |

The `GM` row does not authorize a reveal when hearing is true. To realize the source author's conditional player presentation, a reviewer must separately change the audience ceiling to `PLAYER` and retain the hearing condition. The current API proves only static audience filtering and cannot decide that condition.

This is a contract problem for eventual Playing retrieval, not a request to infer live game state during ingestion. It does not weaken the existing rule that GM-only content is never returned to a player.

The existing per-use `usable | limited | unknown | unavailable` readiness assessment describes package evidence for a workflow. It is separate from a viewer-specific release decision: `usable` alone never authorizes disclosure, and a withheld player response does not make the underlying GM-readable package unusable.

## Invariants for review

1. **Hard ceiling.** The existing `GM | PLAYER` field remains mandatory. A conditional rule may narrow a `PLAYER` resource; it cannot widen a `GM` resource. Missing or unrecognized presentation metadata cannot make GM material player-visible.
2. **Source meaning and authored policy remain distinct.** COMPOSITOR can preserve a source-stated presentation type and prerequisite with an exact source locator. A later authored release choice is a separate, attributed change with its own revision and review; it cannot be reported as the source's instruction.
3. **Portable source, exact use.** Source packages should not invent a World Fact ID. Any binding from a portable prerequisite to a World fact must identify the exact package/resource/condition revision and the owner-minted fact identity. An evaluator reads an exact authoritative World snapshot; it does not silently use a different head.
4. **Default deny.** Missing, stale, ambiguous, unsupported, partial, contradictory, or client-asserted context never yields player release. An empty fact read is not `false` unless the authoritative predicate contract explicitly provides closed-world semantics. Buddy must verify that the authenticated actor may act for the selected character in the selected World. The server filters before response text, excerpts, model context, cache entries, or UI props can disclose the resource.
5. **Internal decision and non-revealing denial.** A proposed internal outcome is `released`, `withheld`, or `unknown`; `unknown` is not released. Its trace includes reason and issue IDs, condition/evidence paths, exact package and resource snapshots, condition/binding revision, World-to-space binding revision, MIND fact snapshot and evidence IDs, Buddy context revision, audience, workflow, and evaluator semantics version. A player-facing denial must not reveal that a hidden resource or condition exists, and must not expose the internal trace. A GM may inspect the unresolved prerequisite without turning it into player-facing content.
6. **No automatic authority promotion.** Saving or loading a Composition does not make its source claims World facts or approve a player reveal. No general policy language, arbitrary expression interpreter, or gameplay fact schema is introduced here.

## Candidate package vocabulary, pending owner agreement

The initial presentation types could be a short controlled set: `gm_reference`, `player_handout`, `read_aloud`, and `sensory_cue`. A source-specific box or layout label would remain a separate provenance-bearing string, so an extracted layout type is not mistaken for a release decision. Unknown types stay GM-inspectable and player-withheld. The exact names and whether `read_aloud` needs a distinct type are **unsettled**.
`read_aloud` would describe a possible presentation mode, not unconditional player permission. A presentation type that conflicts with the hard audience label must fail closed and be reviewed.

The initial declarative condition shape could support only a conjunction of explicitly identified prerequisites. The hearing example needs one prerequisite that an authoritative fact read can resolve to true, false, or unknown for the selected character and scene. A portable source condition would have a stable package-local condition ID and evidence locator; a separate World binding would map it to an owner-minted fact ID at a reviewed revision. Operators such as `fact_is_true` and any additional sensory or knowledge predicates are **candidates, not approved syntax**. Disjunction, negation, inferred facts, and free-form policy expressions remain out of scope. Unsupported source conditions remain inspectable and evaluate to unknown.

This proposal does not mint Fact IDs or name a current MIND fact path. MIND's read-only review confirmed generic exact `(space_id, revision_id)` reads with pinned DomainContract/SemanticProfile identity or digest and request selectors, not an accepted product World/scene/character fact snapshot or actor attestation. A `head_revision_id` or `is_head` observation indicates freshness; it is not a lease or release authorization. A proposed product envelope would need an authenticated Buddy viewer/principal, selected World/scene/character identities and authoritative revisions, a reviewed World-to-space binding revision, exact MIND revision and selectors, and a reviewed mapping from package/resource/condition revision to admitted fact/assertion IDs. Buddy's trusted server would attest its inputs. These are missing contract requirements, not current MIND guarantees; a new MIND API is needed only if the accepted fact read cannot be assembled from existing exact reads.

## Provisional owner split and collision

COMPOSITOR owns versioned, evidence-linked package metadata describing source presentation and declarative prerequisites. Buddy owns authenticated viewer and selected World/scene/character presentation context, obtains authority-stamped facts, and filters content before disclosure. DungeonMind/MIND owns durable fact identity, provenance, and exact reads at a graph head or snapshot. A **proposed**, narrowly scoped WorldKeeper service could deterministically evaluate the release prerequisites over a complete stamped snapshot supplied to it. It would perform no I/O, MIND read, lookup, or general World-read façade. Buddy would apply the decision before any resource content reaches the player path.

This split is **not yet an accepted owner contract**. WorldKeeper's current boundary document assigns Buddy presentation context, WorldKeeper coherence validation, and ordinary reads to the product adapter; its implemented consumer service prepares and commits governed writes. A pure release evaluator would be a new owner contract requiring an explicit WorldKeeper boundary-authority amendment and separate lease. If owning review instead assigns the decision to Buddy, that change also needs a named decision contract. PRIME is holding implementation until exact Buddy context, MIND fact snapshot, input attestation, and evaluator owner are settled.

## Falsification cases for the next contract review

| Case | Required outcome |
| --- | --- |
| Project-authored bell cue, `PLAYER`, hearing fact true in exact scene snapshot | Release only to the selected eligible player, with condition and context revisions. |
| Same cue, hearing fact false | Withhold before any text or excerpt reaches the player path. |
| Same cue, fact absent, stale, ambiguous, or from a different World revision | `unknown`; withhold. Never substitute a nearby fact or latest head. |
| Same cue, exact graph head but partial, timed-out, contradictory, or coverage-unknown fact read | `unknown`; withhold. An empty result is not false without a closed-world predicate contract. |
| Source author intends conditional player cue, but saved resource is `GM` and hearing fact true | Withhold; conditions cannot widen the hard ceiling. A separate reviewed reclassification to `PLAYER` plus the condition is required before any player release. |
| Presentation type implies player delivery but hard audience is `GM` | Withhold and surface an internal mismatch for review. |
| Player supplies another character's ID with a favorable hearing fact | `unknown`; withhold unless Buddy's authoritative actor-to-character binding covers that character in the selected World. |
| Source prerequisite unmapped to a World fact | `unknown`; preserve the source statement for GM review. |
| Authored release policy differs from source wording | Show two attributed records and require review; never rewrite source provenance. |
| Package unloaded or exact resource revision unavailable | No player disclosure from a cached projection or model context. |
| Client asserts a favorable sensory fact that authoritative read does not support | Withhold; client assertion is not authority. |
| Player is denied a hidden cue | Return a non-revealing result; do not disclose resource existence, condition IDs, issue reasons, excerpts, or internal decision paths. |

## Decisions required before implementation

- Agree the bounded presentation vocabulary and which source layout labels remain separate.
- Name the exact Buddy viewer/character and scene context contract, World-to-space binding, the MIND fact-read API and graph head/snapshot token, and the attestation owner. Reject cross-World or mixed-revision inputs.
- Decide the smallest portable prerequisite operators and owner-minted Fact ID binding form. Confirm that unsupported conditions return unknown.
- Decide whether the proposed pure WorldKeeper evaluator is the owner. Amend WorldKeeper's current boundary authority before leasing it; the evaluator may consume only complete stamped inputs and must make no reads.
- Obtain new path-specific leases for any COMPOSITOR schema/code, Buddy delivery gate, or MIND/WorldKeeper contract implementation. Prove the public counterexamples at the actual delivery boundary before claiming Playing readiness.
