# Conks source-fidelity adjudication

Status: **PR candidate for PRIME review**. Base: COMPOSITOR `origin/main` at `0effff173b39f59b1f29f16ac876812cdb80ff60`. This record scores the frozen *Of Conks & Cons* v5 gold against the immutable full-document OCR2 first package, then independently scores the C045 reviewed-text treatment. It reports source fidelity only. PRIME owns merge authority.

## Pinned scope and method

- Printer-friendly PDF SHA-256 `9c6458d5c742945e7b0c0abfcaef217384a8a14a6c503458f2ad49e7ee143e8c`; illustrated PDF SHA-256 `b85eb98ee60110e90de90fa04574ae8a5a2b19f4e24d42acd998ec34fdffba41`. Both stay private. Illustrated pages are necessary to check the three image cases.
- OCR2 first result SHA-256 `66c03819fb2e9249beee8a6693d3a2e43dc25b3da8321a7a8827983a36d90ad5`; first package `conks-ocr2-mark3-full-001@98f8dddde4f68daea9331e534895a8c77d79e5a3f14256ed7c4bac3bc12c5257` (114 resources).
- Frozen gold SHA-256 `e73883dae382881bf44043fb1ab11490217cb308cb78b26e1979889a05cbe1cc`; freeze record SHA-256 `203d71a6ca3563e79c798752f1b8f6a2756204cc32b44a2d01503a2cf62e0928`; denominator **62 cases, C001–C062**.
- The private run plan `.local/private/runs/conks-source-fidelity-adjudication-v1/run-plan.json` SHA-256 `5bf79e095bb273e54c858f53c6e17728df812328fe688d6fab7394871ac3bd0a` pins inputs and zero provider/model/GPU/spend caps. Rubric SHA-256 `7efae4f99b65af4e6319b6a2dbbfbc74b7e3a2ea7263e2f30423e792dd382a10`.
- A **pass** means critical source facts, qualifiers, attribution, and required structure are recoverable in candidate resources. A **minor gap** damages a secondary label, locator, or structure. A **material gap** loses or corrupts a critical identity, quantity, relationship, audience qualifier, table cell, or asset. A **critical failure** reverses or fabricates a critical expectation. These are source-only verdicts; page presence alone is insufficient. Source ambiguity is recorded as ambiguity, not automatically a package error.

The initial private packet SHA-256 `6c5ad0668e748d9e6099db53f3d9d6b2626499f9f2a08bc5dc3a2d9d9a454f61` had 62 blank judgments. Every scored case records its verdict, rationale, exact candidate resource IDs (or empty evidence for an absent asset), printed pages, source PDF pin, uncertainty where relevant, and an unexecuted task verdict. This is a **same-agent provisional** review, not independent owner acceptance. The second pass visually rechecked the questionable and critical source pages, including printed pp2, 5, 7–8, 11–13, 16–17, 19–20 and illustrated map/figure pages. No new OCR or model call was made.

## Frozen first-package result

Private scored packet `.local/private/runs/conks-source-fidelity-adjudication-v1/scored-baseline-source-fidelity-packet.json` SHA-256 `676a33c76a77ca12a143f931a4371d8198339f4f0365b0097caf04c9c9d91abc`:

- **48 pass, 5 minor gaps, 8 material gaps, 1 critical failure**; 62/62 source-fidelity judgments filled. Task, Worldbuilding, Planning, Playing, rules-binding, and consumer judgments remain unexecuted.
- **Critical C045:** printed p17 says “Huge plant” and “blindsight 600 ft.” The first package says `Huqe plant` and `blindness 600 ft.` in distinct statblock resources, changing identity and a combat-relevant sense.
- **Material C005, C010, C029, C053:** Torbin's cross-page farm-boy identity is not bound in the local origin unit; Hempholm loses its final letter; even-roll `d20` becomes `d2o`; and p19's three exact tables have Ebbo/cell structure corruption.
- **Material C055, C061, C062:** the Shacks caption survives, but its illustration and the two distinct illustrated maps have no separately identified asset bytes and provenance in this printer-friendly OCR package. Textual setting references do not repair these asset cases.
- **Material C056:** printed p2 explains Hints and Senses boxes and conditional player knowledge, but the package does not encode box type or contextual disclosure. Every candidate resource is conservatively GM-audience; no unsafe player exposure is asserted.
- **Minor C014, C024, C028, C054, C058:** Hints relation/type loss, shared tactics/treasure locator, mixed contest/GM-advice unit, unclassified paratext, and shared at-tree locator respectively. The core facts remain recoverable.
- **Source caveats C023 and C040:** printed p11 itself says “seizes hostilities”; the intended “ceases” reading is editorial. Printed p16 leaves the all-success helix escape branch unclear; the package preserves that ambiguity. Both receive source-fidelity passes, without claiming executable rules.

## C045 treatment on the same denominator

The separate derived package is `conks-c045-reviewed-source-001@cfcdc3f50f5901539f48f29f99afdbac2298ead59bf482f7f59b352bad5fb74c`, with reviewed correction and immutable first-package lineage documented in [RECORD-29](RECORD-29-conks-c045-source-fidelity.md). Its treatment packet began with blank judgments. All 62 cases were checked again against treated candidate context. C045–C050 include the two changed p17 resources; the other 56 cases have byte-identical candidate resources. The six shared-context cases were examined for changed facts; no verdict was copied silently.

Private scored treatment packet `.local/private/runs/conks-source-fidelity-adjudication-v1/scored-c045-treatment-source-fidelity-packet.json` SHA-256 `be3c5c39cde877d884bac92745f48a06f83aa86249e93fd2347eb1c60ff7a933` yields **49 pass, 5 minor gaps, 8 material gaps, 0 critical failures**. The sole changed judgment is **C045: critical failure → pass** on literal source fidelity. Printed p17 and the two corrected resources now agree on Huge plant and blindsight 600 ft.; C046–C050 retain their separate mechanics. The initial and treated packages remain separate; no treatment is promoted by this record.

## Review boundary and next owner work

The result is reviewable evidence for source preservation, with 13 remaining non-pass cases after treatment. It does not prove a typed statblock, actual query success, session audience policy, 2024/5.5 PHB/MM binding, or a Buddy consumer witness. The source's historical PHB p150/MM citations are retained as historical citations; the operator-selected rules target is the **2024/5.5 revision**, requiring separate exact-version ingestion and linkage. PRIME may accept this provisional adjudication as a benchmark record while retaining those gaps as explicit follow-up work.

The review used zero provider/model/GPU calls and $0 external spend. Reviewer effort was a manual pass across 62 frozen expectations, candidate resources, and cited source pages, plus a visual second pass on ambiguity, statblock, table, audience, and asset cases. Human independent review and task-level execution are still outstanding.
