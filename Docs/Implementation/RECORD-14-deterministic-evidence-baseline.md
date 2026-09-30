# Deterministic evidence baseline

Status: **COMPOSITOR-only review candidate**. This slice starts from main `6bd52de06590647ca6783c93ab9749ac9b1b0924`. It adds a zero-provider recovery baseline for an existing RulesIngestion Stage A/B supplied-Markdown draft. It does not interpret adventure meaning or demonstrate Worldbuilding, Planning, or Playing competence.

## Contract and order

`freeze_first_evidence_result` takes an exact, immutable source package revision, a source manifest, an evidence manifest, and the RulesIngestion adapter ref. Before writing, it checks both manifest hashes, that the source manifest binds the evidence Markdown and PDF digests, every adapter artifact through `load_evidence_draft`, package replay identity, and each resource's Stage B unit provenance. It rejects a missing pinned source. The only output is a new private JSON file containing the adapter result, package, page mapping, source and recipe pins, diagnostics, and zero provider usage. Exclusive file creation prevents replacement of a first result.

`build_recovery_coverage` runs only after that file exists. It separately checks the first-result digest, frozen gold digest, and gold freeze-record digest. The freeze record must bind the same suite, source manifest, proposal, and case count. It maps gold's printed Markdown page markers to Stage B `origin.page_index` values. A case is `recovered_page_evidence` only when each named page has at least one evidence resource; missing pages are explicit. Image-dependent `asset_*` cases are `unsupported_image_evidence` on this text route. Each case keeps candidate resource IDs and `semantic_verdict: null`.

This is a page-evidence recovery count, not a source-fidelity pass. A page can have units while a key detail is omitted, misread, or assigned the wrong meaning. Asset recovery needs the separate illustrated-PDF route. Source-specific first outputs, gold, coverage packets, and ledger receipts stay under ignored private storage. Do not publish their bytes or derived case metadata.

## Smoke and private replay

The project-authored synthetic test verifies byte-identical replay in two output directories, exclusive first-result creation, absence of gold-only text from that result, the three recovery states, zero semantic judgments, and failure on mismatched source and freeze pins. The full public suite ran 41 tests with one optional skip. A wheel and source distribution built from a temporary copy of the tree with local cached build dependencies; the default isolated build could not reach PyPI in this environment.

A private replay used the accepted source and frozen gold manifests with the existing closed evidence substrate. It froze the first output before computing coverage, recorded both artifacts and the freeze record in the SQLite experiment ledger, reopened and verified those artifact digests, and closed with zero provider calls and zero reserved or charged spend. Earlier private development replays remain immutable. The exact private pins and recovery counts are in that ledger and ignored run directory, not this public record. No semantic run or source-to-provider transmission occurred.

## Next gate

Use the recovery packet to identify what page evidence is available for later adjudication, while preserving the separate semantic first treatment and its exposure hold. The selected local *A Wild Sheep Chase* PDF and processed Markdown still need exact paths and revision pins before a second-adventure run. PRIME retains PR review and merge authority.
