# Pinned Docling evidence route

Status: **generic COMPOSITOR implementation candidate for PRIME review**. Base `af61748c5993b01e6742144077ec1e61a575fae7`. This route supports a selected page scope or the full Docling intermediate, and leaves interpretation for later review.

`load_docling_evidence_draft` requires exact SHA-256 pins for a local PDF and Docling JSON. It validates the Docling page index, then saves an immutable source package. Text retains its exact intermediate text. Tables retain the structured cell data and a reversible JSON pointer. Pictures remain reference-only. Every resource carries the PDF source ID, intermediate digest, element locator, page provenance, and available structural references. A partial page selection stays visible in diagnostics.

The adapter does **not** prove that the Docling intermediate accurately recovered the PDF. It marks source correspondence and semantic interpretation pending, and marks every table for cell review and every picture for asset review. These issues limit per-use readiness while allowing inspection of the draft. It does not produce verified rules, edition bindings, graph assertions, or a scored benchmark.

The public witness uses a project-authored one-page PDF and a synthetic Docling structure created inside the test. It checks text, table, and picture locators; immutable package replay; source and intermediate pins; missing provenance; invalid page selection; zero provider calls; and limited readiness. No commercial corpus or derived source text is in the PR. Private exploratory runs, if any, remain under the ignored `.local/private` tree and require separate source review before quality claims.
