# Conks offline evidence preparation — implementation record

Status: **PR candidate for PRIME review**. This source-safe recipe is based on COMPOSITOR `main` merge `da38847d6d4c7c583571cbb50930990dc4dfbdd0` and the committed RulesIngestion Stage A/B ref `17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8`. The private run uses the frozen *Of Conks & Cons* v2.1 gold proposal v3 and the accepted private source manifest. The exact source, gold, recipe, and output digests are recorded privately, not in Git.

## Scope and method

`scripts/prepare_conks_offline_evidence.py` requires explicit private source/gold files, owner checkout, private root, database path, and a unique run ID. It checks source and frozen-gold digests, requires printed Markdown page markers 2–20 and 19 printer-friendly PDF pages, renders each PDF page to obtain RulesIngestion fingerprints, and runs the pinned Stage A parser, Stage B binder, and gates on the supplied Markdown page text. It stores source-derived page images, surfaces, ASTs, units, manifests, a package revision, and a compact report only under ignored `.local/private/`. Each artifact file and the closed SQLite run have integrity hashes. The recipe makes no provider calls and performs no gold scoring or semantic interpretation.

The supplied Markdown is the direct textual source of the units; the PDF supplies an associated visual page fingerprint. This route is **not** automatic PDF text recovery. Embedded images are counted but have not been classified or extracted into the Composition; `asset_inventory_pending` limits readiness. The adapter carries that known omission and failed gates into the saved draft.

## Smoke and observed result

The source-safe page-split tests pass for all expected markers and reject a missing page. `PYTHONPATH=src python3 -m unittest discover -s tests -v` covers the complete package/adapter/ledger suite. The first private offline run `conks-md-substrate-001` completed with 143 evidence units, zero provider calls and zero spend. Its report records one Stage B orphan-heading gate failure on printed page 8 (page index 6), plus the pending image inventory; Worldbuilding, Planning, and Playing readiness are all `limited`. The three ledger artifact references verify after reopening. The reported gate failure is retained as an extraction/structural finding, not silently repaired or counted as semantic quality.

No `first_result` artifact or benchmark judgment was written. The first semantic treatment and later repairs must occupy distinct roles and be scored only against the frozen gold after their recipe, source handling, provider model, call/round limits, and spend cap are pinned. The selected *A Wild Sheep Chase* local PDF and processed Markdown paths remain outstanding, so no two-adventure comparison is claimed. PRIME owns PR review and merge.
