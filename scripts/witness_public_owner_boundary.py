"""Public-fixture smoke across COMPOSITOR, DungeonMind, and WorldKeeper.

Run with a Python environment containing both owner repositories' dependencies.
No private corpus, network call, or persistent authority is used.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


MIND_REF = "4758fe812b539ad8209031ae22c05d36f7636957"
KEEPER_REF = "662a028fb1882719c4c3e192134a1a6b7a58026c"
MANIFEST_SHA = "289df4b50cb59b88ef3a72846f282b33bd2c52a960e931e953694aa2f310f712"
RULES_REF = "17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8"
ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
EXCERPT = "The watcher can move a token one space with Wind Step."
SPACE_ID = "space:compositor-public-windmill"


def _pinned_root(path: str, expected: str, label: str) -> Path:
    root = Path(path).expanduser().resolve()
    if not (root / "src").is_dir():
        raise RuntimeError(f"{label} source checkout missing: {root}")
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                            capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{label} revision check failed: {result.stderr.strip()}")
    actual = result.stdout.strip()
    if actual != expected:
        raise RuntimeError(f"{label} revision mismatch: expected {expected}, found {actual}")
    return root


def witness(mind_root: Path, keeper_root: Path) -> dict[str, object]:
    sys.path[:0] = [str(ROOT / "src"), str(mind_root / "src"), str(keeper_root / "src")]
    from compositor import JsonPackageStore, load_evidence_draft
    from compositor.owner_input_proposal import propose_owner_inputs
    from compositor.workspace_selection import WorkspaceSelection
    from dungeonmind.application.vnext.initialization import initialize_empty_knowledge_space
    from dungeonmind.application.vnext.native_source_access import (
        open_admitted_native_text, open_native_text_source_access_context,
    )
    from dungeonmind.application.vnext.native_source_admission import publish_native_text_source_evidence
    from dungeonmind.contracts.vnext.common import PublicVisibility
    from dungeonmind.contracts.vnext.domain import (
        DomainContractDescriptor, SemanticProfileDescriptorV2, SemanticProfilePredicate,
    )
    from dungeonmind.contracts.vnext.native_source import (
        NativeTextEvidenceSpanRequestV1, NativeTextSourceAdmissionV1,
    )
    from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository
    from worldkeeper.application.contracts import (
        AssertionMetadata, CreateFact, CreateObject, LiteralFactValue, ScopeBinding,
        TemporalScope, Visibility, WorldChangeIntent,
    )
    from worldkeeper.integrations.dungeonmind import DungeonMindWorldKeeperRuntime

    body = (ROOT / "fixtures/public/windmill-field-notes.md").read_bytes()
    contract = DomainContractDescriptor(
        domain_id="compositor.public", domain_revision="1",
        scope_axes=["compositor:scope"], claim_modes=["compositor:source_claim"],
        admission_policy_id="compositor.public.fixture",
    )
    profile = SemanticProfileDescriptorV2(
        profile_id="compositor.public.profile", profile_revision="1",
        term_namespaces=["compositor"],
        predicates=[SemanticProfilePredicate(term="compositor:title", allowed_value_kinds=["literal"])],
    )
    repository = InMemoryNativeSourceEvidenceRepository()
    genesis = initialize_empty_knowledge_space(
        repository=repository, space_id=SPACE_ID, initialization_id="init:public-windmill",
        created_at=NOW, domain_contract=contract, semantic_profile=profile,
    )
    genesis_head = genesis.published_revision_id

    with TemporaryDirectory() as temp:
        store = JsonPackageStore(Path(temp) / "packages")
        draft = load_evidence_draft(
            store, ROOT / "fixtures/public/evidence/supplied_markdown",
            project_root=ROOT, package_id="windmill-evidence", title="North Mill Field Notes",
            expected_rules_ingestion_ref=RULES_REF, expected_manifest_sha256=MANIFEST_SHA,
        )
        package_ref = {"package_id": draft.package["package_id"],
                       "revision": draft.package["revision"]}
        selection = WorkspaceSelection(store)
        selection.select(package_ref)
        assert repository.get_head(SPACE_ID).head_revision_id == genesis_head
        hits = selection.query("Mill Watcher", audience="GM")
        assert hits and all(hit["package_id"] == package_ref["package_id"] for hit in hits)
        resource_id = next(rid for rid, resource in draft.package["resources"].items()
                           if resource["name"].endswith("Mill Watcher"))
        proposal = propose_owner_inputs(store, package_ref=package_ref,
                                        resource_id=resource_id, source_body=body,
                                        evidence_excerpt=EXCERPT)
        candidate = proposal["dungeonmind_native_text_admission"]
        span = candidate["spans"][0]
        assert body[span["start_byte"]:span["end_byte"]] == EXCERPT.encode("utf-8")
        assert repository.get_head(SPACE_ID).head_revision_id == genesis_head

        admission = NativeTextSourceAdmissionV1(
            space_id=SPACE_ID, admission_id="admit:public-windmill",
            expected_parent_revision_id=genesis_head, created_at=NOW + timedelta(minutes=1),
            body_text=body.decode("utf-8"), expected_body_sha256=sha256(body).hexdigest(),
            source_classification="compositor:field_notes", authority="primary",
            visibility=PublicVisibility(kind="public"),
            spans=[NativeTextEvidenceSpanRequestV1(
                client_ref=span["client_ref_candidate"], evidence_role=span["evidence_role"],
                start_byte=span["start_byte"], end_byte=span["end_byte"],
                expected_slice_sha256=span["expected_slice_sha256"],
            )],
        )
        receipt = publish_native_text_source_evidence(
            repository=repository, request=admission,
            domain_contract=contract, semantic_profile=profile,
        )
        admitted_head = receipt.published_revision_id
        evidence_id = receipt.bindings[0].evidence_ref_id
        admitted = repository.get_revision(SPACE_ID, admitted_head)
        assert admitted is not None
        assert admitted.graph_payload["entities"] == []
        assert admitted.graph_payload["assertions"] == []
        context = open_native_text_source_access_context(
            repository=repository, space_id=SPACE_ID, revision_id=admitted_head,
            domain_contract=contract,
        )
        source = open_admitted_native_text(context, evidence_id)
        assert source.status == "available" and source.body_text.encode("utf-8") == body
        assert source.body_sha256 == proposal["source"]["content_sha256"]
        assert (source.span_start_byte, source.span_end_byte) == (span["start_byte"], span["end_byte"])
        assert source.span_sha256 == span["expected_slice_sha256"]

        runtime = DungeonMindWorldKeeperRuntime(
            repository=repository, domain_contract=contract, semantic_profile=profile,
            clock=lambda: NOW + timedelta(minutes=2),
            prepared_id_factory=lambda: "prepared:public-windmill",
        )
        metadata = AssertionMetadata(
            scope=(ScopeBinding("compositor:scope", "public-windmill"),),
            visibility=Visibility(), epistemic_basis="asserted",
            claim_mode="compositor:source_claim", standing="established",
            evidence_ref_ids=(evidence_id,), temporal_scope=TemporalScope(),
        )
        intent = WorldChangeIntent(
            SPACE_ID, "producer:compositor-public-fixture",
            (CreateObject("watcher", (CreateFact("watcher-title", "compositor:title",
                                                 LiteralFactValue.from_json("Mill Watcher"), metadata),)),),
        )
        prepared = runtime.prepare_change(intent)
        assert prepared.expected_parent_revision_id == admitted_head
        assert repository.get_head(SPACE_ID).head_revision_id == admitted_head
        committed = runtime.commit_prepared_change(prepared, confirmed_by="user:fixture-review")
        assert committed.verification.exact_child_read_back is True
        assert repository.get_head(SPACE_ID).head_revision_id == committed.child_revision_id
        child = repository.get_revision(SPACE_ID, committed.child_revision_id)
        assert child is not None and len(child.graph_payload["entities"]) == 1
        assert len(child.graph_payload["assertions"]) == 1
        assertion = child.graph_payload["assertions"][0]
        assert evidence_id in assertion["metadata"]["evidence_ref_ids"]

        selection.unload(package_ref)
        assert selection.active_refs() == []
        assert repository.get_head(SPACE_ID).head_revision_id == committed.child_revision_id
        return {
            "status": "pass", "fixture": "public-windmill", "package_ref": package_ref,
            "source_sha256": sha256(body).hexdigest(), "span": [span["start_byte"], span["end_byte"]],
            "mind_revision": MIND_REF, "worldkeeper_revision": KEEPER_REF,
            "genesis_revision_id": genesis_head, "admitted_revision_id": admitted_head,
            "evidence_ref_id": evidence_id, "committed_revision_id": committed.child_revision_id,
            "object_count": len(child.graph_payload["entities"]),
            "assertion_count": len(child.graph_payload["assertions"]),
            "unload_kept_world_head": True,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dungeonmind-root", required=True)
    parser.add_argument("--worldkeeper-root", required=True)
    args = parser.parse_args()
    try:
        mind_root = _pinned_root(args.dungeonmind_root, MIND_REF, "DungeonMind")
        keeper_root = _pinned_root(args.worldkeeper_root, KEEPER_REF, "WorldKeeper")
        result = witness(mind_root, keeper_root)
    except (ImportError, RuntimeError) as exc:
        parser.exit(2, f"owner-boundary smoke unavailable: {exc}\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
