# Owner A/B first result and selected-page coverage

Status: public synthetic implementation for PRIME review. Base: COMPOSITOR `main` after PR #18. This slice consumes RulesIngestion Mark III A/B output through `load_evidence_draft`; it does not run OCR or claim OCR quality.

## First-result order

1. RulesIngestion produces one or a few selected PDF pages at the accepted owner ref. The private COMPOSITOR wrapper pins the source PDF, ordered page indices, model, prompt, DPI, page fingerprints, all five unmodified per-page A/B artifacts, and provider usage status or receipt. `load_evidence_draft` verifies that wrapper and imports the source units.
2. `freeze_owner_first_result` checks the wrapper hash, source-manifest hash and PDF identity, package replay, selected physical-to-printed page map, and every resource locator. It writes a new private JSON file exclusively (`open("x")`) containing the exact package, adapter report, owner recipe, usage status, page map, and pins. It does not receive gold.
3. Only after the first-result hash is recorded, `score_owner_page_coverage` accepts the frozen gold and its freeze record. It verifies those hashes and source bindings, then reports `out_of_scope`, `partial_scope`, `recovered_page_evidence`, `missing_page_evidence`, or `unsupported_image_evidence` for each case. The fully scoped denominator includes only cases whose required pages were all selected, even when a selected page has no recovered units. Every `semantic_verdict` stays null; human source review and task-boundary witnesses are separate.

The selected page map is an explicit pilot input because the owner artifacts use physical indices and the gold cites printed pages. The operator must derive and review it against the exact source manifest before freezing. No default offset is inferred.

Provider usage can remain `unknown` for historical owner artifacts; unknown calls or spend are never reported as zero. A new live treatment still requires a pinned exposure, finite call/spend cap, and a receipt or explicit local-inference accounting before execution. OCR raw JSON/output hashes and run-level usage details belong in the private owner handoff; the existing import wrapper covers five page artifacts. Missing such a handoff must be recorded as an omission, not silently promoted to a complete treatment.

## Synthetic smoke check

`tests/test_owner_evidence_first.py` uses only the authored North Mill fixture. It checks replay and exclusive first-result creation, gold separation, selected/partial/out-of-scope denominators, unknown usage, and failures before output for source or page-map mismatches. It is an engineering witness, not a Conks or Sheep result.

## Next real witness

After RulesIngestion supplies a pinned Conks OCR 2 A/B bundle, wrap and import its selected pages privately; verify the handoff receipt and first-result hash; then score page coverage against the already frozen Conks gold and adjudicate semantic retention separately. Expand to the full PDF only after this limited route yields a trustworthy source-to-package witness. The Sheep source path and rights handling remain a separate input prerequisite.
