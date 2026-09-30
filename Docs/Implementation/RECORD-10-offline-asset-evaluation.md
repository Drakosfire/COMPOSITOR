# Offline mixed-source asset recovery review

Status: **COMPOSITOR-only asset recovery witness for PRIME review**. Base `e369965da0e1251e01ab17fff9745ece1ae85f62`. This is a three-case recovery adjudication, not the semantic first treatment, a score for the full 62-case suite, or a Worldbuilding, Planning, or Playing acceptance result.

The existing semantic review packet requires a single supplied-Markdown source identity and printed-page text locators. The illustrated asset package intentionally contains both Markdown-derived evidence units and image references from a different, exact illustrated-PDF revision. `compositor.asset_benchmark` builds a separate packet for frozen asset cases. It validates the two source identities and exact image page/xref locators, matches each case to its illustrated page, and leaves every verdict `null`. The packet reports whether a candidate resource exists and marks semantic and task competence `not_assessed`. It cannot infer a pass from a present image. The previous semantic review code and frozen v3 matching remain unchanged.

`scripts/review_private_asset_recovery.py` pins source manifest `eebebb2f802ce31ba5a0be763db37a1dcac6e4d94e02c79b746caac5ee933b2a`, separately frozen v4 gold `0f0b570000e68d11534a4f38eec0e19b92112e1c6fa22ff3709f5ab09f5ce01b`, the source-verified `conks-illustrated-assets-002` manifest `8c76c676572da58421a502c7215cca10cfda7a5231e96515dc3286153c30ad2e`, and immutable package revision `a2052f59793b1da38c0663fb62b140b0fefcf0a423199c8acddf2599c926d7b9`. Before packet creation or finalization, it independently reruns PDF-to-image verification and requires the resulting package to equal the pinned one. The persistent ledger pins those inputs, an immutable unjudged context, and a composite recipe digest covering the driver plus the local code that decides the result. A separate draft accepts only explicit reviewer, rationale, verdict, and valid resource citations. Finalization checks all cases, writes a distinct immutable adjudication, and records judgments under `asset_recovery_package`; a matching retry is idempotent.

The final-head private review run is `conks-asset-recovery-v4-004`. Its adjudication SHA-256 is `acea69a149aad69f2288db7c41b768b2965a9ee82914c9dfa7147651f467ef45`; composite recipe SHA-256 is `efac50f95872b11ac88f802aa925e1b5632a78341fd46931a8aa5bfb51f6c559`. The earlier `-003` run remains an immutable prior-code result (adjudication `75aa887651ff66b907357ee4041cbf9747d55e2b5cc2d406e55203ac357af511`, recipe `1bf279a2b697bedf19eba553cecb93475498ec5c1c7b6726eed748b1fc83f2ca`); `-001` and `-002` remain private development runs. The same explicit reviews were transferred only after the three unreviewed case contexts matched between `-003` and `-004`. The reviewer checked the rendered illustrated pages and the source-verified package:

| Frozen v4 case | Recovery-only verdict | Evidence and limit |
| --- | --- | --- |
| C055, Shacks figure | Material gap | Illustrated printed page 9 has the figure, but the current asset package has no page-9 image resource. |
| C061, Greenfields map | Pass | Private PNG from illustrated printed page 4/xref 31 is recoverable with exact source provenance. Map interpretation is unassessed. |
| C062, Hempholm map | Pass | Distinct private PNG from printed page 8/xref 65 is recoverable; markers 1–5 are visible. Marker-to-location mapping and player presentation are unassessed. |

The verdicts measure asset recovery only. The package still labels these maps `reference_only` pending content review, and retains its other extraction issues. No claim is made about complete illustrations, layout interpretation, scene utility, semantic correctness, or the remaining 59 v4 cases. The ledger closes the run with zero provider calls, zero call cap, zero spend cap, and zero charged or reserved dollars. No external owner, World, or Buddy write occurs.

Private replay, using the same exact ignored corpus and package artifacts:

```sh
python scripts/review_private_asset_recovery.py prepare --private-root "$PRIVATE_ROOT"
# Inspect source, package, and the private review-draft.json; enter explicit reviews.
python scripts/review_private_asset_recovery.py finalize --private-root "$PRIVATE_ROOT"
```

The synthetic test builds a mixed-source package with two image pages and a missing third asset. It proves candidate scope, an unjudged packet, explicit review, and failure on wrong source identity, wrong locator/page metadata, changed packet context, and a tampered immutable package. A second test injects a ledger failure during preparation, verifies rollback of both the run row and newly created packet files, then retries the same run ID to one closed run with five pinned artifacts. The full local suite, PDF-environment suite, wheel build, and diff check are the PR smoke.
