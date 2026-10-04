# Record 34 — Scene contribution to card projection lab

Status: author-local development witness, pending PRIME review. This is a bounded COMPOSITOR representation and deterministic read path. DungeonMind owns durable source admission, graph revisions and evidence reads; Buddy owns the DOGFOOD card surface. Neither owner contract changes here.

## Input and authority

The experiment uses the frozen OCR2 evidence and reviewed package revisions from the Conks and Sheep baselines. It makes no provider calls and writes no product store. The private receipt at `.local/private/runs/scene-card-lab-v1/first-result.json` pins the Conks PDF SHA-256 `9c6458d5c742945e7b0c0abfcaef217384a8a14a6c503458f2ad49e7ee143e8c` and reviewed package revision `cfcdc3f50f5901539f48f29f99afdbac2298ead59bf482f7f59b352bad5fb74c`; Sheep PDF SHA-256 `a92a7d6f67432dfacd935161a7c90a6ec9ba7f4fc636a8e8f09537070bbdeeb6` and provisional reviewed map-link revision `ef7d1f6d96b0cec9fea673059de283c66d41cfcb629a8371874f9a66a094e8e7`. The prior #38/#39 first results remain unchanged. The Sheep opening is development material already exposed in #39, not a held-out transfer result.

The user selected the 2024/5.5 revision as the desired PHB/MM binding target. The adventures' historical page references do not establish exact 2024/5.5 rules. Both cards carry an explicit unresolved external-rule item. No source content is marked player safe.

## Contract

`load_pinned_context` checks the source, OCR manifest, Stage B page files, and package bytes and identities. Each cited Stage B page hash must also be present in the manifest. A scene contribution contains an id, pinned source identity, reviewed claims, and optional choices. Each claim declares `source_supported`, `proposed_connective`, or `unresolved`; a lens, kind, audience, and attributed review decision are required. Source support cites an exact unit, physical page index, and verbatim substring. A read-aloud claim needs an explicit player-safe disclosure decision. Choices are optional and carry an explicit noncombat flag; references to conditions and consequences must resolve locally.

`project_card` is stateless. The caller supplies active surface and audience; the projection returns Situation, Read aloud, Do now, GM only, Relevant, and Missing reference lenses. GM and player projections share the same contribution identity but obey audience filtering. `card_to_source` checks the card's pinned source identity and reopens a claim's exact evidence; it does not fall back to a different revision. These are lab-local candidates, not governed graph ids or executable rules.

## Development result

Two private opening contributions produced GM cards and source readbacks. Conks has six claims: three source supported, one proposed connective, two unresolved. Sheep has seven: four source supported, one proposed connective, two unresolved. Both player projections are empty by design because no player-safe review occurred. The initial card and readback bytes are frozen in `.local/private/runs/scene-card-lab-v1/`; review decisions are in `.local/private/gold/scene-card-v1/`. This is same-agent development review, not independently adjudicated gold. No whole-adventure package or connected scene graph is claimed. The Conks cross-page identity and Sheep #39 missing connected path remain open findings.

## Checks and next owner decision

Public synthetic fixture tests exercise exact source readback, tamper failures, state separation, audience filtering, card identity mismatch, optional choice projection, and player-safe read-aloud gating. The private build reopened cited OCR units from pinned artifacts. Production promotion needs an accepted DungeonMind read contract and Buddy consumption contract; PRIME should coordinate those separately. A next bounded slice can review semantic edges and selected player disclosure against actual source pages, with independent reviewer attribution and no reuse of the held-out Sheep page.
