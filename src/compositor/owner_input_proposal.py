"""Read-only proposal of source/evidence inputs for owning repositories.

This is not a DungeonMind registration or WorldKeeper intent. Owner IDs,
classification, visibility, and authority must be resolved by those owners.
"""

from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

from .package import CompositionError, JsonPackageStore, effective_content


_SOURCE_SHA = re.compile(r"^sha256:([0-9a-f]{64})$")


def propose_owner_inputs(store: JsonPackageStore, *, package_ref: dict[str, str],
                         resource_id: str, source_body: bytes,
                         evidence_excerpt: str) -> dict[str, Any]:
    """Preserve exact source identity while exposing unresolved owner decisions."""
    content = effective_content(store, package_ref)
    resource = content["resources"].get(resource_id)
    if resource is None:
        raise CompositionError("resource not present in exact package revision")
    origin = resource.get("origin") or {}
    match = _SOURCE_SHA.fullmatch(str(origin.get("source_id", "")))
    if origin.get("type") != "source" or match is None or not origin.get("locator"):
        raise CompositionError("owner source proposal needs exact SHA-256 and reversible locator")
    if not isinstance(source_body, bytes) or not source_body or len(source_body) > 1_048_576:
        raise CompositionError("native source proposal needs one UTF-8 body within 1 MiB")
    try:
        source_body.decode("utf-8", errors="strict")
        excerpt_bytes = evidence_excerpt.encode("utf-8", errors="strict")
    except (UnicodeError, AttributeError) as exc:
        raise CompositionError("native source and excerpt must be UTF-8") from exc
    if sha256(source_body).hexdigest() != match.group(1):
        raise CompositionError("native source body differs from package source revision")
    if not excerpt_bytes or source_body.count(excerpt_bytes) != 1:
        raise CompositionError("evidence excerpt must identify one exact source byte span")
    if evidence_excerpt not in resource["text"]:
        raise CompositionError("evidence excerpt must also occur in the selected resource")
    start = source_body.index(excerpt_bytes)
    end = start + len(excerpt_bytes)
    snapshot = json.dumps(resource, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    exact_ref = {"package_id": content["package_id"], "revision": content["revision"]}
    return {
        "format_version": 1, "status": "proposal_only_no_owner_write",
        "package_ref": exact_ref,
        "package_issues": content["issues"],
        "resource_ref": {"resource_id": resource_id, "resource_snapshot_sha256": sha256(snapshot).hexdigest(),
                         "kind": resource["kind"], "name": resource["name"],
                         "audience_label": resource["audience"]},
        "source": {"content_sha256": match.group(1), "source_id": origin["source_id"],
                   "locator": origin["locator"],
                   "associated_pdf_sha256": origin.get("associated_pdf_sha256")},
        "dungeonmind_native_text_admission": {
            "contract_candidate": "NativeTextSourceAdmissionV1",
            "owner_ref": "4758fe812b539ad8209031ae22c05d36f7636957",
            "space_id": None, "expected_parent_revision_id": None,
            "admission_id": None, "created_at": None,
            "body_text": None, "body_text_handling": "attach_exact_verified_UTF8_body_at_owner_run",
            "expected_body_sha256": match.group(1), "body_byte_length": len(source_body),
            "source_classification": None, "authority_policy": None,
            "visibility_policy": None,
            "spans": [{"client_ref_candidate": resource_id, "evidence_role": "support",
                       "start_byte": start, "end_byte": end,
                       "expected_slice_sha256": sha256(source_body[start:end]).hexdigest(),
                       "compositor_locator": origin["locator"]}],
            "returned_source_artifact_id": None,
            "returned_source_revision_id": None,
            "returned_evidence_ref_id": None,
            "returned_published_revision_id": None,
        },
        "worldkeeper_prepare_prerequisites": {
            "contract_candidate": "WorldChangeIntent",
            "owner_ref": "662a028fb1882719c4c3e192134a1a6b7a58026c",
            "space_id": None, "world_id_to_space_id_binding": None,
            "registered_evidence_ref_id": None,
            "prepare_reads_current_head": True,
            "prepared_expected_parent_must_be_reviewed": True,
            "identity_choice": "explicit_create_new_or_use_existing_required",
            "review_and_confirmation": "required_before_publication",
        },
    }
