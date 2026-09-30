# COMPOSITOR

COMPOSITOR is a proposed open-source research program for making **portable, source-linked Compositions** from documents people bring themselves. Its first goal is a reproducible lab baseline: given an exact document and its source identity, produce a bounded set of inspectable resources and relationships while showing what was resolved, kept for reference, unsupported, or left unresolved.

The repository currently contains its foundation documents only. There is no ingestion pipeline, Composition format, fixture, replay command, or production integration yet. The broader research program remains subject to operator alignment and a bounded PRIME dispatch.

## Why this exists

Role-playing source material can mix facts, procedures, exceptions, references, and prose. A useful Composition must preserve where each claim came from, where it applies, and what the system could not establish. Research here asks which approaches can do that reliably, with enough evidence for another researcher to reproduce and challenge the result.

The first milestone is deliberately small. It should accept an exact local document and a shareable fixture, produce source-linked results within a stated audience and domain, and fail clearly on missing or changed inputs. Ruleset compilation, Drools, executable mechanics, and full-book coverage are separate research questions.

## Intended first lab baseline

Once the program is activated and the first assignment is pinned, the baseline should provide:

1. A small, openly licensed or project-authored fixture with stable source anchors and documented expected outcomes.
2. A command-line path from an exact local input to a bounded, inspectable Composition with explicit resolved, reference-only, unsupported, and unresolved results.
3. Deterministic replay with pinned dependencies and no hidden model call, plus visible failures for missing input, source mismatch, broken references, and audience mistakes.
4. Independent review of the fixture outcomes and a report of limits, failures, and costs. Optional live-model experiments need separate data and budget approval.

These are acceptance targets, not implemented features. The exact format, commands, dependencies, and files will be chosen in the authorized implementation slice.

## Boundaries

COMPOSITOR is a lab for research and evidence. It does not publish to production, mutate source authority or campaign canon, execute mechanics, or become a permanent fork of another repository's runtime. Production promotion needs a named destination owner and contract.

User documents stay outside Git by default. A public codebase does not make an input document public or grant permission to send it to a model provider. Initial fixtures must be openly licensed or project-authored; any other material requires an explicit rights and handling decision.

This work sits alongside [DungeonOverMind](https://github.com/Drakosfire/DungeonOverMind) for ecosystem architecture, RulesIngestion for ingestion substrate, GenerationEngine for reusable inference execution, DungeonMind and WorldKeeper for governed knowledge and publication, DungeonMindBuddy for product workflows, and RulesEngine for mechanics execution. Each keeps its own authority.

## Working in this repository

Read [AGENTS.md](AGENTS.md) before agent-assisted work. An active assignment also needs a pinned mandate/handoff and an activation record with its write, data, runtime, provider, and budget scope. Repository initialization and these documents do not activate experiments or authorize paid runs.

There is no installation or test command to run yet. The first implementation PR should add only the dependencies, fixture, workflow, and verification needed for its bounded baseline, then document their actual commands here.

## Open-source status

The project is intended to be public open-source software. A license has not yet been selected for this repository; until one is added, do not assume the code is licensed for reuse. Contributions and redistribution guidance will follow that decision.
