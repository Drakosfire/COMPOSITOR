# Composition contract and assembly

Status: **accepted design baseline**, canonized by explicit operator direction after the five-question design discussion on 2026-09-29. This document governs Composition semantics and assembly in COMPOSITOR. It does not claim an implemented schema, pipeline, or consumer integration.

The operator accepted the golden Composition and media refinement on 2026-10-11: **a Composition preserves a source's content, meaningful structure, relationships, and media with traceable provenance, while supporting selection, grounded interaction, and explicit adaptation for Worldbuilding, Planning, and Playing.** Golden Compositions make this destination inspectable before comparing processing recipes or model stacks.

## Accepted decisions

1. A Composition can represent a faithful source package or an adapted package. Users can read its contents and rules, ask grounded questions, modify it, and save a different package with lineage to the original.
2. Rule dependencies are selectable: reference an exact external rules package revision, or bundle the needed content when saving/exporting where permitted. Modified rules retain their connection to the original.
3. Derived packages support both changes over a pinned original and complete snapshots. Provenance survives either representation.
4. Changes trigger impact review. Identify affected resources and propose dependent updates for the user to accept; do not silently propagate those updates.
5. Drafts are usable. Incomplete packages can be saved, loaded, read, and queried with missing content, unresolved references, and outstanding review visible. Readiness is assessed separately for Worldbuilding, Planning, and Playing.
6. Golden Compositions require two independent acceptance witnesses: faithful source reconstruction and functional use by the intended consumers. Equivalent encodings are acceptable when required content, relationships, provenance, and behavior agree.
7. Text is the first processing focus; an image media primitive belongs in the contract from the outset. Image descriptions and image bytes have distinct identities and provenance.

The suggested data-level “off” control was explicitly withdrawn as scope creep. It is not part of this contract.

## Logical contract

These are required concepts, not finalized JSON field names or database tables.

- **Identity and revision:** stable package identity, immutable saved revisions, title, and format version. Editing working material produces a new saved revision; saving as a different package establishes a distinct package identity with lineage.
- **Lineage:** exact source or Composition revisions from which the package derives. Preserve the distinction between derivation history and a dependency required to load content.
- **Resources:** narrative, entities, encounters, procedures, rules, tables, and assets with stable identity and source references. Preserve audience scope, authored adaptations, and explicit unresolved or unsupported material.
- **Relationships:** explicit connections among resources, including exact rule bindings. Loading packages together does not infer identity equivalence.
- **Dependencies:** exact external package/revision references and selected bundled content. Bundling preserves identity and provenance; referencing unavailable content leaves a visible unresolved dependency.
- **Changes:** additions, edits, and removals relative to a pinned original. An adaptation does not overwrite the original's saved content.
- **Review and readiness:** missing content, unresolved references, proposed dependent updates, review decisions, and known limitations. Report supported uses separately for Worldbuilding, Planning, and Playing.

The logical artifacts must be expressible through the public JSON fixture and private experimental persistence described in the [objectives](OBJECTIVES-compositor.md). Physical encoding and storage technology remain open.

## Source reconstruction and images

Faithful reconstruction preserves content, meaning, and organization: reading order, headings, dialogue and speakers, tables and selection semantics, images, references, conditions, and their meaningful connections. The original document remains the visual reference; exact typography and pagination are outside this reconstruction criterion. An adapted package retains an inspectable source view alongside its effective adapted content.

Trace each represented resource to its source and each relevant source part to its representation or explicit disposition. A coverage inventory records omissions, reference-only material, and ambiguity. A convincing rendering with missing material fails the affected reconstruction expectations. Source attribution and possible-versus-observed events must survive reconstruction and interaction.

An image resource requires stable identity; exact byte identity/digest; MIME type and dimensions; a storage reference and availability state; document revision and page/region provenance; audience; and relationships to the relevant resources. Crops, annotations, or other variants retain transformation lineage and their own byte identity. A description, caption, or interpretation is a distinct resource whose provenance identifies source-authored versus inferred or adapted content. Available bytes, visual meaning, and audience-safe presentation are separate review claims.

Reuse the existing [Conks asset inventory](../Implementation/RECORD-09-illustrated-asset-inventory.md) and [Sheep JPEG projection](../Implementation/RECORD-20-sheep-jpeg-asset-projection.md): they verify source occurrence, bytes, dimensions, and geometry. Their reference-only status does not establish the new reconstruction or consumer witness. An image from a different source revision keeps that revision's identity.

## Production ownership clarification

The two save forms and portable package semantics above remain accepted. The current JSON package kernel and SQLite ledger are lab/replay representations. In a production path, COMPOSITOR prepares reviewed, evidence-linked contribution candidates and selection/export manifests pinned to DungeonMind-managed Adventure or Rules space revisions. The proposed MIND vNext seam mints durable space/source/evidence/graph identities, admits exact source spans, materializes reviewed contributions against the admitted parent, and serves revision-pinned reads; it still needs an actual witness. A MIND space ID is not a product World ID. DungeonMind owns durable knowledge, storage, and publication; WorldKeeper coordinates the exact governed World change. Worldbuilding, Planning, and Playing use consumer-owned projections over this shared authority. This clarification does not imply that a cross-space join, contribution-decision ledger, or production package persistence API already exists; those contracts require owner review and a real consumer witness.

## Effective content and interaction

Reading and questions use effective content: the base content, accepted changes, and available dependencies, constrained by active selection and audience. Answers distinguish original material, adaptations, and unresolved information and retain evidence references. Unavailable material must not be silently substituted with another revision or invented.

Pending dependent-update proposals are review artifacts, not accepted content. A user's direct edit can be saved while its impact review remains incomplete; dependent resources remain unchanged until their proposed updates are accepted. Known inconsistencies remain visible.

Draft usability does not waive audience boundaries or justify presenting unresolved rules as verified. A missing dependency limits the affected content or operation; it does not require withholding all available draft content. Readiness is information about supported uses, not a universal save/load gate.

## Two save forms

### Changes over a pinned original

Store the changes and the exact original revision needed to reconstruct effective content. Preserve outstanding review and readiness information. If the original is unavailable, expose that missing dependency rather than claiming a complete reconstruction.

### Complete snapshot

Materialize the base content and accepted changes so reconstruction no longer requires the original package. Retain lineage and provenance. Deliberately external rules dependencies can remain external; a complete snapshot is not a promise that every dependency has been bundled. Pending proposals remain separate from accepted content.

With the same available dependency revisions, both save forms must reload to equivalent effective content and provenance. Their storage representation and requirement for the original differ.

## Assembly process

1. **Recover evidence.** Read the pinned document or supplied Markdown, retaining source locations and extraction provenance.
2. **Construct resources and relationships.** Interpret narrative, mechanics, procedures, and assets while retaining source attribution and uncertainty.
3. **Resolve dependencies.** Bind exact rules and other references; record the selected external/bundled treatment and unresolved dependencies.
4. **Assemble a usable draft.** Produce effective content with visible missing or inconsistent material and per-use readiness information.
5. **Review changes and effects.** Identify resources affected by edits and propose updates. Apply dependent updates only after acceptance; retain outstanding review separately.
6. **Save and reload.** Save a revision or derived package in either form, preserving lineage, accepted content, and outstanding review.

This is a repeatable editing cycle as well as an initial ingestion process. Saving, loading, or adapting a Composition does not publish World truth. DungeonMind/WorldKeeper retain their governed admission/publication boundaries, and product interaction remains with its owner.

## First acceptance witness

Demonstrate **assemble → read and query → edit → review affected content → save in both forms → reload**.

The witness must show:

- Grounded reading and questions over original and adapted content with attribution.
- A rule change with at least one affected resource, proposed dependent updates, and explicit acceptance rather than silent propagation.
- Saving/loading with a pending proposal and an unresolved dependency, preserving usable content and visible limitations.
- Both external and bundled dependency choices with exact identities preserved.
- Equivalent effective content and provenance after reloading either save form with the required dependencies available.
- Original content remains intact, and no World publication occurs merely from saving or loading.

These checks complement the [one-shot benchmarks](BENCHMARKS-one-shots.md); a synthetic witness alone does not establish adventure quality.

The next proposed golden unit is **one complete, source-reviewed section with text, relationships, and at least one image**. It must supply reconstruction and functional witnesses for planning, grounded query, adaptation, selection, and both save forms/reload. The [benchmark protocol](BENCHMARKS-one-shots.md) defines source-backed authoring, freeze, behavioral equivalence, and task records. Exact source/section, consumer contracts, thresholds, and execution scope await a separate activation; this accepted design does not dispatch an experiment.

## Remaining implementation decisions

Define the concrete schema, revision/identifier encoding, change representation, dependency resolution mechanics, impact-analysis method, readiness rubric, and persistence adapter in bounded implementation designs. This accepted semantic baseline does not select those mechanisms or authorize cross-owner migrations or provider runs.
