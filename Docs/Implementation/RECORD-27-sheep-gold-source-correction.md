# Record 27 — Sheep case 026 gold source correction

PRIME leased a versioned, no-model correction from COMPOSITOR `main` `c183010b788a8b09c0cf497494cf2e076caa29e1`. The selected publisher v2 PDF remains SHA-256 `a92a7d6f67432dfacd935161a7c90a6ec9ba7f4fc636a8e8f09537070bbdeeb6`. Direct page-5 rendering and its PDF text layer both read `DC13 Deterity Save`. The OCR2 first result reads `Detrity`; frozen v3 gold case `SHEEP-V1-026` instead asserted `Dexterity` as source-derived. PRIME independently verified the printed and text-layer literal before this correction. The earlier baseline adjudication already identified the printed typo in its rationale, but the gold expectation and owner repro did not preserve that distinction.

## Versioned private evidence

- Frozen v3 gold `a5a74042ab1ba1afddabb4dce87a2ccacb3925b21d2a3d87a4aa36e5e596e8de` and its freeze record remain unchanged.
- New private v4 gold `.local/private/gold/sheep-v4/proposal.json` is SHA-256 `cb799ea3835adbd00e64839c9420e804d636219845ad57149bcb03a7de163d31`; its freeze record is `a4900050a3b5d1375add346bb2bb514477f9c850d303e9e49fb0c2562d660eb8`. The source manifest digest is unchanged. Case `SHEEP-V1-026` is the only modified case object; all 55 IDs, 48 source-fidelity and seven integration denominators, other 54 case objects, and source revision remain unchanged. The private revision note SHA-256 is `28a7011e29e073f4e564add66e81146be5b8fa387d5ce893dec0216f95b6d645`.
- New private owner repro `.local/private/runs/sheep-v2-ocr2-full-20260930/owner-repros-v3.json` is SHA-256 `2b3e94702e750dfcb375a8c7f40267172ef314acbd06576403c9acb16c774c4a`, with lineage to unchanged repro v2 `def8f041259fc193e80ebb0e38a24fa2c6690323683e3f1f044404bbd0017c0b`. It records printed `Deterity`, OCR `Detrity`, and a separate, unverified intended `Dexterity` interpretation. No OCR repair was applied.

V4 requires source evidence to retain the printed spelling. A GM may use `Dexterity` only as an attributed mechanics interpretation; it cannot be presented as the publisher's exact text. This correction does not establish an external rules binding or a general spelling-normalization rule. It was driven by independent source verification, not by a favored pipeline's answer.

## Comparable v4 rescore

The existing pinned packet builders reopened all 48 source-fidelity cases blank for the 139-resource OCR2/JPEG base and four existing additive treatments. Each derived package revision was loaded unchanged; case 026 was directly checked against the PDF and package. Every other case expectation and cited package evidence was unchanged, so its prior verdict was carried into an explicit same-agent v4 review. All seven owner integration cases remain unexecuted.

- OCR2/JPEG base `2fc627a04df68372d2443f8991bf3df7b117f1b6750b4961d785b492d1a73ebc`: **37 pass / 10 material / 1 minor**, same as v3.
- Reviewed source decisions `de11692d328695a0cf46af4904d7a858e12e21a7642c68fbe720aba29c67bde1`: **39 / 8 / 1**, same as v3.
- Statblock conflict diagnostic `17657fd1d82803e1185f6b0961d3edcc5b679f8c5ee51f648b9f2649f0c37d4b`: **38 / 9 / 1**, same as v3.
- Combined disjoint treatments `5874e97dcd625726f8eadd9f56f06119088e549f007049d651bcc914874ee2b2`: **40 / 7 / 1**, same as v3.
- Reviewed map links `ef7d1f6d96b0cec9fea673059de283c66d41cfcb629a8371874f9a66a094e8e7`: **38 / 9 / 1**, same as v3.

Case 026 remains a material gap in all five packages: OCR2's `Detrity` differs from the printed literal, and none records an attributed intended-save interpretation or a complete corrected Wyrmling statblock. The private v4 rescore root is `.local/private/runs/sheep-v4-gold-rescore-20260930/`; receipt SHA-256 `72e2d66d2577461d1e3d5d33104d0734ea5496f56497e7d3379cd2b8c085470b` pins all five blank and adjudicated packet hashes and verdict comparisons. Existing v3 packets and first results remain historical and unchanged.

The rescore used zero provider or GPU calls and `$0` external spend. Agent page inspection, case review, and recipe work were not separately time-metered; total compute and review cost is not zero. The v4 rescore is comparable, provisional, and same-agent. It does not supply independent full semantic or human acceptance, run owner consumer witnesses, repair RulesIngestion Stage A/B, or promote a package. The three OCR defects remain for the RulesIngestion owner, with the corrected source spelling now pinned for its treatment.
