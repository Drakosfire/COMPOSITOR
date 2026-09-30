# Conks first semantic treatment: review record

Status: **source-safe implementation candidate; live treatment pending explicit source-to-provider approval**.

## Contract and bounds

The driver reads the exact 19 supplied-Markdown page surfaces from the private `conks-md-substrate-001` evidence manifest. Preflight checks that every page's SHA-256 matches, the source manifest and frozen gold match the substrate's pins, the run identity is a safe private path component, and the GenerationEngine checkout is the requested exact commit. Gold is pinned but never included in prompts. The supplied Markdown is the treatment input; this does not claim automatic recovery from the PDF.

COMPOSITOR owns the page prompt, schema, assembly, and private artifacts. GenerationEngine owns OpenAI execution and observations. The pinned owner ref for the first treatment is `128710668369b73beff78ea0e4377ec252cd04e4`. The proposed model is `gpt-5.6-luna` using structured output with `temperature=None`, low reasoning, 8,192 maximum output tokens, zero transport retries, and at most one GenerationEngine conformance retry. Nineteen logical page operations permit at most 38 provider attempts. The ledger reserves $0.05 per page, at most $0.95 total. The [model's listed text rates](https://developers.openai.com/api/docs/models/gpt-5.6-luna) are $0.20 per million input tokens, $0.02 cached input, and $1.20 output, checked 2026-09-30. A token-based list-price estimate is reported separately from billed cost; the ledger retains the conservative reservation when billed cost is unknown.

The first result is a private, immutable bundle of the raw parsed and text responses, failures, and GenerationEngine observations. Each page's prompt and response is separately saved and hashed in a ledger-pinned call manifest. Assembly accepts only candidates with a source quote found on their pinned page; rejected and unresolved candidates remain diagnostics. A source package is a derived artifact, separate from the raw first result. It preserves structural gate and asset-inventory issues inherited from the evidence substrate. External rule mentions remain unresolved; the first pass does not advertise verified PHB bindings. This quote check is a coarse grounding guard, not a semantic accuracy score.

## Smoke evidence and current limit

`PYTHONPATH=src python3 -m unittest discover -s tests -v` covers package, adapter, ledger, path safety, and first-result grounding. The private preflight passed for all 19 pages and the pinned GenerationEngine ref without creating a run or making a provider call. A local GenerationEngine contract check resolved the model and accepted the structured schema and output ceiling.

Automatic approval review rejected the proposed live call because it would send nonpublic, source-derived Conks page contents to OpenAI. The user's general API-key authorization did not specifically authorize that payload and destination under the reviewer's rule. No `conks-semantic-first-001` run directory or ledger row was created. The live run remains pending an explicit approval to transmit this source text. No gold score, quality claim, or repaired result is recorded yet. PRIME reviews and owns merge authority.
