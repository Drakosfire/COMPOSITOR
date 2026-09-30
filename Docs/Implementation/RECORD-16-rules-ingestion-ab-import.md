# RulesIngestion Mark III A+B import bridge

Status: **public synthetic PR candidate for PRIME review**. Base COMPOSITOR main `3f7a6cb642523cb360b534465f43bf681877b669`; accepted RulesIngestion ref `17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8`. This change imports owner evidence. It does not perform OCR, column reconstruction, Stage A, Stage B, or semantic interpretation.

## Owner artifacts and wrapper

RulesIngestion `scripts/run_mark3_full_pdf.py --stage ab --dpi 200` writes per-page `stageA.page.json`, `stageA.surface.md`, `stageA.surface.ast.json`, `stageA.gate_diagnostics.json`, and `stageB.evidence_units.json`. `stageA.page.json` is the `StageARecord`: `page_fingerprint`, `source_pdf`, `page_index`, `model_id`, `prompt`, `raw_markdown`, `inference_elapsed_sec`, `content_hash`, and `content_version`. The AST carries `page_fingerprint`; each Stage B unit carries its own fingerprint, content version, line span, ID, type, structural path, and verbatim text. Gate arrays have `gate_name`, `passed`, and `detail`. Those five files are owner output; COMPOSITOR does not rewrite them for a real run.

The new `rules_ingestion_ab` manifest is a COMPOSITOR wrapper, not a RulesIngestion artifact. It binds the source PDF SHA-256, exact RulesIngestion Git ref, ordered page indices and owner paths, every artifact SHA-256, page fingerprints, and `owner_recipe` (`stage`, `recovery_method`, `model_id`, `prompt`, `dpi`). `provider_usage.status` is `unknown` with null calls and spend unless a separate receipt establishes them. Known nonzero provider use requires a receipt path and SHA-256 in the bundle. Known zero provider calls require an explicit `local_inference` basis. Unknown is never reported as zero.

The adapter checks the owner record against the wrapper and verbatim Stage A surface, checks Stage B fingerprints and content versions, imports exact Stage B unit text, and preserves reversible unit locators. Missing artifacts and failed gates remain typed diagnostics; mismatched hashes, source, model, prompt, order, or fingerprints fail closed. Existing supplied-Markdown and PDF-text routes retain their behavior.

The committed fixture is synthetic and project-authored. It reuses the existing *North Mill Field Notes* public Stage A/B shape, adds a synthetic `StageARecord`, and labels its model and recovery method as a fixture. It makes no DeepSeek quality claim and has no provider receipt. The actual RulesIngestion output shape was checked read-only at the accepted ref. The owner OCR JSON and run-level report are outside this per-page wrapper; later source treatment must separately pin their hashes and usage receipts before first-result scoring.

## Next owner handoff

RulesIngestion should produce a one/few-page A+B bundle at the accepted ref, using a verified DeepSeek OCR 2 execution target. Its handoff should identify the exact source revision, selected page indices, model/prompt/DPI, five unmodified per-page artifacts, run summary and gate results, OCR raw-output hashes, execution environment or provider, usage receipts, and any known omissions. Store nonpublic source and derived output privately. COMPOSITOR then builds the wrapper, imports the bundle, freezes its first result, and scores against already frozen gold in a separate slice. An ingestion defect goes back to RulesIngestion with a page and artifact witness.

The current host has no CUDA GPU. The public OpenRouter catalog did not list the exact DeepSeek OCR 2 model when checked; no API slug, provider exposure, call cap, or cost can be pinned from it yet. No live source transfer or provider call occurs in this PR. The selected *A Wild Sheep Chase* local source paths remain outstanding.
