# Conks C045 reviewed source-text correction

Status: **PR candidate for PRIME review**. Base: COMPOSITOR `origin/main` at `f22f55343d4e51d53bbe7d09a37d40e67e21b4e6`. This is a bounded, no-model source-fidelity treatment for frozen Conks case C045. RulesIngestion retains OCR repair ownership; the OCR first result and frozen gold remain immutable.

## Pinned private inputs

- *Of Conks & Cons* v2.1 printer-friendly PDF SHA-256 `9c6458d5c742945e7b0c0abfcaef217384a8a14a6c503458f2ad49e7ee143e8c`, printed page 17 (physical index 15). The rendered page was visually checked and is private at SHA-256 `3f5a9c1db7a0d36ed9de7538cf9cb8a0e31203235dee9992bf853ad8c8b8a353`.
- Full-document OCR2 first-result SHA-256 `66c03819fb2e9249beee8a6693d3a2e43dc25b3da8321a7a8827983a36d90ad5`, with first source package `conks-ocr2-mark3-full-001@98f8dddde4f68daea9331e534895a8c77d79e5a3f14256ed7c4bac3bc12c5257`.
- Frozen Conks v5 gold SHA-256 `e73883dae382881bf44043fb1ab11490217cb308cb78b26e1979889a05cbe1cc`; freeze record `203d71a6ca3563e79c798752f1b8f6a2756204cc32b44a2d01503a2cf62e0928`.
- Private zero-call run plan `.local/private/runs/conks-c045-reviewed-source-001/run-plan.json` SHA-256 `3531b2a279f7bbf32b3e554be87ab9756aa4953c1cb43fcc5d2251cca1e1ca89`. It pins source, first result, gold, recipe SHA, no provider exposure, call/GPU/spend caps of zero, and the ignored output root.

## Result and checks

The printed page and PDF text layer both read **Huge plant** and **blindsight 600 ft.** for the Grotesque Tree. OCR2 Stage B reads `Huqe plant` and `blindness 600 ft.` in two separately located resources. The private reviewed-correction manifest SHA-256 is `f5e500c12b43537cd6b92975b964d6fe3b046d8ee70d2fe0bd13fbbdd1d9f00e`; it records the exact old/new resource text, source locators, and visual-review evidence. No general spelling heuristic runs.

`apply_reviewed_text_corrections` verifies the pinned PDF bytes, source package revision, per-resource source identity and locator, old text, and review evidence before saving a separate snapshot. The derived private package is `conks-c045-reviewed-source-001@cfcdc3f50f5901539f48f29f99afdbac2298ead59bf482f7f59b352bad5fb74c`. It retains 114 resources and lineage to the original; only the two affected resources' text and authored correction provenance differ. The original OCR package still reloads unchanged. A fresh temporary-store replay reproduced the exact derived revision and file bytes.

The treatment reopens all 62 cases with blank judgments in a private packet, SHA-256 `6862f3cdfae7aeabb3816767a2f078c3ab3e61bf07b52a71d3b2e413ad08db26`, context SHA-256 `a952be97f1701d9a8e15f906b97ae1392f110c2d08ae750bc21301f74d8d379a`. C045–C050 all use page-17 candidate context, so each sees the two changed resources. No other resource, relationship, or dependency changed; no semantic or Playing verdict is inferred for any of these six cases. All 62 remain unreviewed in this treatment packet. The private receipt SHA-256 is `e85dde92a60ae5be8e475e801ea7a6f80e5b550d2bb80779f6be5d7718c7e689`.

Focused synthetic tests passed (two tests). The full suite ran 59 tests, six skipped, zero failures; `git diff --cached --check` passed. The treatment made zero provider/model/GPU calls and spent $0 externally. Review effort was one visual page inspection, two exact source/locator checks, and an independent deterministic replay; agent labor was not priced. The operator's private PDF remains at its local path outside Git; the render, gold, package, and packets are under ignored `.local/private/`.

This improves the literal source evidence for C045. It does not assemble a typed statblock, resolve 2024 rules, prove task-level use, or establish a real consumer witness. The owner OCR repro remains separate for RulesIngestion.
