# Draft handoff 05 — rules interaction

Status: **proposed, unassigned**. Roadmap: [Composition PR stack](../Roadmaps/ROADMAP-composition-pr-stack.md). Scope depends on the prior package and consumer witnesses.

**Pin at dispatch:** exact rules source/edition revisions and handling permission; current RulesIngestion evidence contract; MIND-reviewed Rules `DomainContractDescriptor` and `SemanticProfileDescriptorV2`, Rules space/admission/read contract; package binding contract; statblock and Rules Lawyer consumer owners and their PRs or blocked dependencies; RulesEngine or agreed Drools adapter owner and execution contract; merge order, end-to-end witness owner, target cases, provider budget if any, and repository write scopes.

## Of Conks & Cons edition bridge

The operator selected **2024/5.5 PHB and Monster Manual rules as the target edition** for this adventure. Its 2019 PHB/MM citations remain locators in the adventure's original source. A cited page number must not be presented as a page in the target edition, and a candidate 5.5 evidence package is not yet a verified rule binding.

For each proposed binding, record the adventure source locator and original citation separately from the exact target-edition source revision and rule locator. Review whether the target rule is equivalent, changed, absent, or still unresolved; preserve any adventure-specific amendment. A missing target source, unreviewed edition mapping, or conflicting rule stays visibly unresolved or reference-only. It must not acquire a verified indicator in either consumer.

The first targeted review should exercise a cited equipment table, a cited monster statblock, and a spell reference with an adventure-specific modification. Use privately held source material and reviewed target-edition evidence. The existing exploratory 5.5 PHB extraction has no frozen rules gold or independent semantic adjudication; target Monster Manual evidence is not yet pinned. This decision selects the edition for the later witness, not permission to publish the rulebooks or claim the bindings complete.

**Deliver:** reviewed, evidence-linked Rules contribution candidates for admission to a MIND-minted Rules space, plus exact rule bindings from adventure resources and statblock fields to a rule definition, source revision, and applicable local amendment. Expose retrieval states so a consumer can indicate when verified information is available. Use the same binding for statblock and Rules Lawyer retrieval. Record whether needed rules stay linked or are lawfully bundled. Keep runtime rule evaluation in RulesEngine or an agreed adapter.

**Prove:** reopen the exact MIND Rules space/revision and recover the admitted source/evidence path for a reviewed binding. Through the named real consumer paths, both consumers resolve an exact binding and amendment consistently; missing, stale, conflicting, unsupported, and edition-mismatched bindings remain visible and never display as verified. Test at least one modified rule whose affected resources require review. A COMPOSITOR-only mock does not establish consumer acceptance. Separately, run a bounded Drools witness under RulesEngine or an agreed adapter using pinned rule/fact revisions, expected and counterexample cases, firing/result provenance, explicit unknowns, timing, and resource caps. This witness does not choose a production engine.

**Boundary:** COMPOSITOR owns ingestion and binding preparation. DungeonMind owns durable Rules knowledge and pinned graph/evidence reads. Rules Lawyer and statblock UI remain with their product owners; RulesIngestion extraction and RulesEngine/adapted Drools execution retain their own boundaries. Targeted rule ingestion does not authorize full-book publication or wholesale retrofit.

**Hand onward:** verified binding contract, source/version coverage, failed cases, and evidence for deciding whether existing ingestions can be retrofitted or need a corpus redo. Return any larger rules or runtime program to PRIME for separate sequencing.
