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

The current blank full-48 packet (`blank-review-packet-v2.json`) SHA-256 is `67d8fc459c8aa61358a94d259fd421954197f6f3a7f3fe97b9e5c2494639a954`. Its canonical context hash is `859a57552fc7928d1628c4ce98f5a587fe870c0fb04e2909c7b4bfef324e6697`. The same-agent provisional adjudicated packet (`adjudicated-packet-v2.json`) SHA-256 is `a007f560d9e923d57b15096c00e2bd507aa2ac893064c6282c0fc92da1e4e82a`, with receipt `70701be9ba4858d400dfeeedaf679023525eea7e9eabcb4b1216368640521496`. The original blank/adjudicated packets and receipt remain in the private root: PRIME found that their stored context hash did not cover the subsequently added map relationship evidence. Version 2 repairs the hash without changing the first package or verdicts.

The baseline 37 pass / 10 material / 1 minor becomes **38 pass / 9 material / 1 minor**. Only case 022 changes from material gap to pass; there is no observed regression in this exact-delta review. All seven owner integration cases remain unexecuted. Cases outside 022 retained their prior verdicts after checking that their source resources, prior relations, and diagnostics are unchanged; this is not a new independent semantic audit.

The first treatment used zero provider or GPU calls and spent `$0` externally. The recorded execution step took 0.961 seconds. Visual inspection, relationship judgment, coding, and 48-case review were performed by the agent but were not independently time-metered; zero external spend is not zero total compute or review cost. The work is gold-informed development because case 022 was a known gap before this treatment.

## Verification and boundary

The full 54-test synthetic suite passes. An exact private replay against the pinned PDF, JPEG, base, context, and decisions reproduced revision `ef7d1f6d…` with 139 resources and five relations. `git diff --check` passes. The package remains `provisional_pending_independent_review`; neither human acceptance, independent full semantic review, owner consumer use, nor publication is claimed. OCR defects, exact external rules, and the other source-fidelity gaps retain their named owners. PRIME reviews and owns merge authority.
