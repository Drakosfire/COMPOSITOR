# External rule edition gate

Status: **COMPOSITOR-only contract fix for PRIME review**. Base `40b2cb366e3c3948c13fd65132199f17114e992d`.

An exact external package revision identifies the saved package bytes, but does not by itself state the ruleset expected by the citing resource. `resolve_rule` now leaves a linked or bundled external rule unresolved when the binding omits a nonblank `ruleset`. A declared ruleset must still match the bound rule resource. A local same-package rule reference can continue to resolve by its immutable package revision and resource ID without adding redundant edition metadata.

The public package-cycle witness checks both linked and bundled missing-edition behavior. It also saves and reloads a draft whose external binding lacks an edition: the unrelated content stays readable, while the unresolved rule limits readiness. Adding the matching ruleset to a new saved revision clears the issue. No private rules corpus, provider, or owner repository is involved.
