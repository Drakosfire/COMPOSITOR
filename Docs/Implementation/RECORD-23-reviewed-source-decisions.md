# Reviewed source decisions: provisional Sheep pilot

Status: **private, provisional, non-model development treatment**. The COMPOSITOR parent agent reviewed the candidate source pages and the resulting 48 source-fidelity cases. No human user or independent reviewer has accepted these judgments. The derived package records `review_authority: agent` and `promotion_state: provisional_pending_independent_review`; it has no consumer publication authority.

## Scope and pins

The treatment used the publisher Sheep v2 PDF SHA-256 `a92a7d6f67432dfacd935161a7c90a6ec9ba7f4fc636a8e8f09537070bbdeeb6`, frozen gold `a5a74042ab1ba1afddabb4dce87a2ccacb3925b21d2a3d87a4aa36e5e596e8de`, unchanged OCR2 first result `821a0a36da1c80a6a0fcf266e856ebd8827b28bafbe4111f7d780fc829e96f24`, and 139-resource OCR2/JPEG package revision `2fc627a04df68372d2443f8991bf3df7b117f1b6750b4961d785b492d1a73ebc`. The original 48-case adjudication had 37 pass, 10 material gaps, and one minor gap. Seven owner integration cases were unexecuted.

The generic scanner visited all 139 package resources, including 135 text resources, without consulting gold. It emitted three source-page-anchored candidates: one identity/form cue, one possible conflict between failure consequences, and one charge-use versus remaining-charge timing ambiguity. Their frozen first-result file has SHA-256 `44f79f78658b08c53b788126c16094b3cde338fa51dc1c39324b8b8c77c97bbd`. Each candidate carries exact physical PDF page, source quote, package resource IDs, and a typed proposed choice. Candidate discovery alone grants no assertion authority.

The parent agent inspected the rendered source pages and recorded three attributed choices with rationales. The corrected decision record is `8201320208339acdb5c6c71bdc274d58040b0c14860e01596c242f3cfa86b72d`. The additive derived package revision is `de11692d328695a0cf46af4904d7a858e12e21a7642c68fbe720aba29c67bde1`: all 139 baseline resource values remain identical, one identity resource and three typed relations were added, and both source ambiguities remain unresolved. Source quotes, decision attribution, lineage, and the provisional promotion state remain in the private package. No gold case or original package was edited.

## Development comparison

The parent agent re-adjudicated all 48 cases against a fresh blank treatment packet. The corrected expected packet SHA-256 is `24f14cbf5696f685849165b59abadb0daf1841cb5d2280b0f7a8e0d6e908b6da`; the complete, validator-accepted adjudication SHA-256 is `96fa16efa02d76a0a1c713a090f39aa7d237d9e9da5ede03fb27fd01211d512a`. The corrected receipt SHA-256 is `6b1a3ccb627d83c19754638f5d21cfdcc5404ff438903a70864083bdbd29ffee`. These files remain under ignored `.local/private/runs/sheep-v2-reviewed-source-decisions-001/`.

| Source-fidelity cases | Baseline | Provisional treatment |
| --- | ---: | ---: |
| Pass | 37 | 39 |
| Material gap | 10 | 8 |
| Minor gap | 1 | 1 |

Cases `SHEEP-V1-005` (identity/form) and `SHEEP-V1-039` (charge ambiguity) changed from material gap to pass in this same-agent review. No regression was observed. Case `SHEEP-V1-043` remains a material gap: the source relation does not repair an OCR monster-name error. Seven integration cases remain unexecuted. The counts are a gold-informed development comparison, not an independent estimate of first-ingestion quality, end-user usefulness, or generalization.

This treatment made zero separate model/API/GPU inference calls and spent $0 on external providers. The COMPOSITOR agent performed source review and engineering; its compute cost is not measured here. Measured wall time from branch start to review end was 549 seconds, including 86 seconds for candidate source review, 61 seconds for the 48-case regression review, and 402 seconds of engineering/tool/other time. These intervals are effort proxies, not billed labor. The prior private artifacts with `human` in filenames or fields remain immutable historical records; the corrected v2 decision record and receipt identify the actual agent reviewer and supersede those labels.

Promotion requires independent source review and explicit human acceptance if this output is to be treated as accepted, followed by owner integration witnesses through pinned boundaries. This PR adds the generic mechanism and synthetic test; the private Sheep package is evidence for review, not a published composition.
