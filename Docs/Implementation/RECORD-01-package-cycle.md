# Package cycle — implementation record

Status: **PR candidate for PRIME review**. This activates [draft handoff 01](../Handoffs/HANDOFF-01-package-cycle.md) on merged COMPOSITOR `main` at `33826ab7872a59b0c84d0f24def85760c1adc621`. The owning branch is `codex/composition-package-cycle`.

## Scope and inputs

- Write paths: `src/compositor/`, `fixtures/public/`, `tests/`, `pyproject.toml`, `README.md`, and this record.
- Runtime: local Python only; no model/provider calls, shared database, cross-repository writes, or World publication.
- Fixture: `fixtures/public/package-cycle.json` is newly authored for this repository. Its Windmill scenario, rules, names, and text are fictional project material; no commercial adventure or rule text is bundled.
- Storage: each package revision is canonical-JSON hashed, written under an explicit store root, and checked on load. The public fixture is test input; real experiment stores belong under ignored `.local/private/`.

## Witness

`PYTHONPATH=src python3 -m unittest discover -s tests -v` checks seven independent paths:

1. Assemble and reload the source; follow a resource locator into the fixture; read by audience; edit a rule; leave its dependent update pending; accept it; save a delta and snapshot; compare their effective content and lineage.
2. Select a pinned rule package as linked or bundled; require a recorded bundling permission basis; resolve an exact rule; expose edition and revision mismatches and missing linked content.
3. Save a draft while its base later becomes unavailable; expose the missing base while retaining its locally changed content. A saved snapshot remains independent.
4. Reject a modified revision and a package ID that could escape the store root.
5. Preserve a superseded impact proposal when a later direct edit changes the same rule again; only the new proposal remains pending and eligible for acceptance.
6. Keep a resource with an undeclared local rule reference visible but mark its rule unresolved and each use limited.
7. Detect a rule dependent expressed only through a `uses_rule` relationship and leave its update pending for review.

The package does lexical local-resource retrieval and exact rule resolution. `readiness` is a conservative first-pass signal based on known missing content and pending impact; later ingestion and task-specific evaluation must provide richer assessments. Source locators are required in the package and verified in the fixture witness, but arbitrary imported locators are not yet checked against external documents. The `permission_basis` field records a decision; it does not determine the legal right to bundle material.

## Smoke checks

The first source save/load smoke failed because `__init__.py` exported names before implementation; exports were completed and the smoke passed. Edit/review/save and linked/bundled/missing-rule smokes passed. PRIME's first exact-head review found two gaps: an unresolved local rule could leave readiness usable, and a relationship-only rule dependent received no impact proposal. Both were reproduced, fixed, and covered by focused witnesses. All seven permanent tests passed. A wheel build passed with system `setuptools` using `python3 -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/compositor-build .`. The earlier `uv build --offline` attempts failed because the default cache was read-only, then because `hatchling` was unavailable offline; the build backend was changed to locally available `setuptools` and the wheel smoke passed.

## Handoff to document ingestion

The next adapter can emit source resources with IDs, `source_id` and reversible locators, audience, kind/name/text, rule references, and relationships. It should preserve extraction omissions and evidence diagnostics alongside packages rather than inventing missing facts. A document-derived draft can be saved through this store, but this PR proves only the public project-authored fixture. PRIME owns review and merge.
