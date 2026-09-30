# COMPOSITOR

COMPOSITOR is an ingestion and processing program for making **portable, source-linked Compositions** from documents people bring themselves. Its goal is competent to better-than-good first ingestion into packages usable for **Worldbuilding, Planning, and Playing**. A package preserves resources, relationships, source identity, audience boundaries, adaptations, and explicit unresolved or unsupported material.

The repository contains operating guidance, objectives, benchmark design, and a first deterministic Composition package kernel. Document ingestion, the private experiment database, and production integrations remain future work.

Start with the [accepted Composition contract and assembly process](Docs/Design/CONTRACT-composition.md), [objectives and roadmap](Docs/Design/OBJECTIVES-compositor.md), and [one-shot benchmark and gold protocol](Docs/Design/BENCHMARKS-one-shots.md).

The [draft capability PR stack](Docs/Roadmaps/ROADMAP-composition-pr-stack.md) groups implementation into reviewable bites with concise handoffs. It is proposed sequencing for PRIME review; future dispatches must pin their actual inputs and boundaries.

The first format implements source and adapted packages, selectable linked or bundled exact rule dependencies, and saving adaptations as changes over a pinned original or as complete snapshots. Direct rule edits produce dependent update proposals for review. Drafts remain readable with explicit issues and preliminary readiness for Worldbuilding, Planning, and Playing. This kernel is a deterministic package boundary, not a document ingestion or runtime integration.

## Why this exists

Role-playing source material can mix facts, procedures, exceptions, references, and prose. A useful Composition must preserve where each claim came from, where it applies, and what the system could not establish. Research here asks which approaches can do that reliably, with enough evidence for another researcher to reproduce and challenge the result.

The research includes rules extraction and exact bindings for statblocks and Rules Lawyer, alongside narrative, characters, places, procedures, encounters, tables, and assets. Ruleset compilation and execution remain separate capabilities to investigate.

## Intended evaluation

Two independently reported one-shot benchmarks will establish whether ingestion and package preparation are useful: *Of Conks & Cons* and *A Wild Sheep Chase*. Each receives its own gold author and source-grounded review loop. Together they also exercise loading either or both packages with Eldyrwild or a blank World, source-scoped and combined queries, and explicit Worldbuilding adaptations.

The [project-authored JSON fixture](fixtures/public/package-cycle.json) supports package engineering checks. Private database records will persist real-source experiments, versions, outputs, judgments, and receipts. Both storage forms should express the same logical artifacts, with private JSON exports for replay. Database technology is still open.

First-ingestion quality, repairs, coverage, known imperfections, and human review effort will be reported separately. These are acceptance targets, not implemented features.

## Boundaries

COMPOSITOR owns ingestion and processing through package preparation. The original source, authored World additions, applicable rules, and runtime outcomes keep separate identities and provenance. Loading packages changes the workspace's active content; importing or publishing durable World changes uses the owning governed contracts.

User documents stay outside Git by default. A public codebase does not make an input document public or grant permission to send it to a model provider. Initial fixtures must be openly licensed or project-authored; any other material requires an explicit rights and handling decision.

This work builds on existing RulesIngestion research and tooling. [DungeonOverMind](https://github.com/Drakosfire/DungeonOverMind) coordinates cross-repository transitions; GenerationEngine supplies reusable inference execution; DungeonMind and WorldKeeper supply governed knowledge and publication; DungeonMindBuddy owns product workflows. Transfer of existing ingestion components and retrofit versus corpus re-ingestion will be decided from benchmark evidence.

## Working in this repository

Read [AGENTS.md](AGENTS.md) before agent-assisted work. Follow the current operator direction and record the write, data, runtime, provider, and budget scope needed by the assigned work. Design decisions do not automatically authorize paid runs or production changes.

Copy [.env.example](.env.example) to `.env` and fill the source paths and settings needed for your local experiments. It includes optional OpenAI, OpenRouter, and Buddy internal API key names. The package kernel does not consume these settings. `.env` stays local.

Keep private PDFs, processed Markdown, reviewed gold, source-derived packages, media, and replay exports under `.local/private/` (or at external paths named in `.env`). Write generated runs and diagnostics under `.local/out/`; preserve first results and later repairs in separate run directories. Both roots are ignored by Git. Other common private corpus and artifact directories are ignored as a safeguard. Put intentionally public, project-authored fixtures under `fixtures/public/` and source-safe benchmark definitions under `evals/public/` once those directories are created. Review any file before explicitly adding it to the public repo.

The kernel needs Python 3.11 or newer and has no runtime dependencies. Run its contract witnesses with `PYTHONPATH=src python3 -m unittest discover -s tests -v`. To build a wheel in a prepared Python environment, run `python3 -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/compositor-build .`.

`JsonPackageStore` writes immutable, content-addressed revisions beneath an explicit directory. Keep real-source stores under `.local/private/`, not `fixtures/public/`. The [package-cycle run record](Docs/Implementation/RECORD-01-package-cycle.md) gives the exact first implementation scope, smoke checks, and current limits.

## Open-source status

The project is intended to be public open-source software. A license has not yet been selected for this repository; until one is added, do not assume the code is licensed for reuse. Contributions and redistribution guidance will follow that decision.
