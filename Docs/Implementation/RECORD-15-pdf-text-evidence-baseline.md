# PDF text-layer evidence baseline

Status: **COMPOSITOR-only review candidate**. Base main `b7a7d81674cb68b43b7fd3c948fbfb7559fb58e1`. This extends the immutable deterministic baseline to an existing RulesIngestion Stage A/B `pdf_text` bundle. It adds no PDF extraction engine, provider call, semantic interpretation, or owner-repository write.

## Route contract

The first-result freezer accepts `supplied_markdown` or `pdf_text` only when the evidence manifest says zero provider calls. It requires the source manifest to bind the exact PDF digest; supplied Markdown also requires its own exact digest. It pins the recovery method, manifest and artifact hashes, RulesIngestion ref, ordered page identities, adapter replay, and every Stage B unit origin. A blank text surface is preserved with a `missing_text` diagnostic. An embedded image count yields `image_content_unsupported`; PDF text does not imply recovery of image pixels. The first result is written exclusively before any gold is opened.

The separate scorer reads the frozen-gold record and uses route-specific page locators: normalized Markdown markers for the supplied route and printer-friendly PDF printed pages for `pdf_text`. It reports case-level page-evidence availability, candidate unit IDs, and unset semantic verdicts. Its structural section also records units by page, pages without units, and failed Stage A/B gates. These measurements can reveal a structural loss even when both routes have text on every page. They do not certify that units retain the correct entities, tables, quantities, relationships, or task meaning.

## Public smoke

The project-authored three-page PDF has text on pages 1 and 3, no text on page 2, and one embedded image. The static Stage A/B fixture is pinned to that PDF and the accepted RulesIngestion ref. Its test proves byte-identical replay, printed-page order, PDF source identity, missing-text and unsupported-image diagnostics, separate gold input, route-specific coverage, a rejected reordered manifest, and rejected pin substitution. The earlier supplied-Markdown tests remain in the same suite.

## Private comparison and limits

The selected local PDF was processed offline with pinned Poppler text extraction and the accepted RulesIngestion Stage A/B owner ref. Its recipe, evidence bundle, package, immutable first result, frozen-gold record, and later recovery evaluation are saved under ignored private storage and digest-verified in the experiment ledger. A separate evaluation of the prior supplied-Markdown first result used the same frozen gold and scorer revision. Both closed with zero provider calls and zero cost. Exact source revisions, case details, counts, and failure examples remain private. The page-presence score alone is deliberately insufficient; compare the structural section and retained gates before drawing a recovery conclusion.

The PDF route is a deterministic lower bound for source recovery. Headings, layout, tables, and images can be lost by the text layer or by treating extracted text as Markdown. No semantic or Worldbuilding, Planning, or Playing acceptance is claimed. The source-to-provider semantic treatment remains separately held for exact exposure approval, and the selected local *A Wild Sheep Chase* source paths remain outstanding. PRIME owns PR review and merge.
