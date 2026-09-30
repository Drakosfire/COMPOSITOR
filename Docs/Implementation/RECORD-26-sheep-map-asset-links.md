# Record 26 — provisional Sheep map-to-prose links

PRIME leased one no-model COMPOSITOR treatment for source-fidelity case `SHEEP-V1-022`, based on merged `main` `abf370a9517e1cc0d2a3671b0945c4b110838094`. This record describes a private development result, not an accepted consumer package.

## Frozen input and recipe

- Publisher v2 PDF SHA-256: `a92a7d6f67432dfacd935161a7c90a6ec9ba7f4fc636a8e8f09537070bbdeeb6`.
- Embedded page-4 JPEG SHA-256: `5b5285145dacb9ec4733654b96afba3123e70aa083001d49ac4371763837e497`. It remains a private, GM-only, reference-only image.
- Frozen Sheep gold SHA-256: `a5a74042ab1ba1afddabb4dce87a2ccacb3925b21d2a3d87a4aa36e5e596e8de`.
- Unchanged 139-resource OCR2/JPEG base: `sheep-v2-ocr2-jpeg-assets-001@2fc627a04df68372d2443f8991bf3df7b117f1b6750b4961d785b492d1a73ebc`.
- Recipe: `review-map-asset-links-v1` in `src/compositor/review_map_asset_links.py`. It verifies package revision, exact PDF and image bytes, GM asset scope, same-page prose, exact resource and PDF quotes with overlapping terms, and attributed review. The visual correspondence remains a reviewer judgment. A rejected or uncertain judgment can remain unresolved. The recipe makes no model or network call.

Direct inspection of rendered PDF page 4 and its embedded map found five source-supported correspondences: the large enclosed three-room central structure, planted open garden platform, smaller connected platform, two bedded huts, and isolated outhouse. The page text supplies names and heights; the top-down image does not independently establish elevation. No coordinates, player-safe variant, or World truth were added.

## Immutable private treatment and comparison

The ignored private root is `.local/private/runs/sheep-v2-reviewed-map-asset-links-001/`. The first result was saved before the frozen review packet was opened for scoring. Its package is `sheep-v2-reviewed-map-asset-links-001@ef7d1f6d96b0cec9fea673059de283c66d41cfcb629a8371874f9a66a094e8e7`: all 139 source resources are byte-equivalent to the base, with five added, GM-scoped, reviewer-attributed map-to-prose relations and no added diagnostics. The context, decisions, first-result, and first-receipt file SHA-256 values are respectively `7d039f165e332802a9ff5dd8949fd09583530f69fb432dd335da7f7b328a25c1`, `8e6ebf614ece1f5bf0e343766ba8763c70b615fc4db57b69b3073771e9121f6f`, `e4d4519a28446ae18075f9ef176e077d025515924943be7d9b53919b7dfef2c5`, and `1389a56e86c4f449129b48d333af892860fb3757d1a766f9553f3cbb6a6b3160`.

The blank full-48 packet SHA-256 is `346e8ef12658e75c8723291129501f62d4fd525b574ccefca088f64bd6efdb2c`. The same-agent provisional adjudicated packet SHA-256 is `1d1b02ff1c8e74db5893b2066da782fbe2da6028956116e810c3fc8ac0ed50de`, with receipt `97da51a2c815add94cca24e697fbc2b1bc607892dd6b587f39b0987e24790095`. The baseline 37 pass / 10 material / 1 minor becomes **38 pass / 9 material / 1 minor**. Only case 022 changes from material gap to pass; there is no observed regression in this exact-delta review. All seven owner integration cases remain unexecuted. Cases outside 022 retained their prior verdicts after checking that their source resources, prior relations, and diagnostics are unchanged; this is not a new independent semantic audit.

The first treatment used zero provider or GPU calls and spent `$0` externally. The recorded execution step took 0.961 seconds. Visual inspection, relationship judgment, coding, and 48-case review were performed by the agent but were not independently time-metered; zero external spend is not zero total compute or review cost. The work is gold-informed development because case 022 was a known gap before this treatment.

## Verification and boundary

The full 54-test synthetic suite passes. An exact private replay against the pinned PDF, JPEG, base, context, and decisions reproduced revision `ef7d1f6d…` with 139 resources and five relations. `git diff --check` passes. The package remains `provisional_pending_independent_review`; neither human acceptance, independent full semantic review, owner consumer use, nor publication is claimed. OCR defects, exact external rules, and the other source-fidelity gaps retain their named owners. PRIME reviews and owns merge authority.
