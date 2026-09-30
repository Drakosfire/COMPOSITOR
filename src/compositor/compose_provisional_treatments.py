"""Compose two disjoint, provisional additive source treatments by exact revision.

No gold, source inference, rule resolution, or consumer publication occurs here.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from typing import Any

from .package import CompositionError, JsonPackageStore


RECIPE = "compose-provisional-additive-v1"
ALLOWED_TREATMENT_FIELDS = {
    "package_id", "revision", "title", "lineage", "resources", "relationships",
    "diagnostics", "promotion_state", "review_authority", "candidate_context_sha256",
    "scan_context_sha256", "reviewed_source_decisions", "reviewed_statblock_conflicts",
}


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode()).hexdigest()


def _ref(package: dict[str, Any]) -> dict[str, str]:
    return {key: package[key] for key in ("package_id", "revision")}


def _verify_revision(package: dict[str, Any]) -> None:
    revision = package.get("revision")
    if (not isinstance(revision, str) or len(revision) != 64
            or any(char not in "0123456789abcdef" for char in revision)
            or _hash({key: value for key, value in package.items()
                      if key != "revision"}) != revision):
        raise CompositionError("package revision integrity mismatch")


def _scope_ids(issue: dict[str, Any]) -> set[str]:
    ids = set()
    if isinstance(issue.get("resource_id"), str):
        ids.add(issue["resource_id"])
    listed = issue.get("resource_ids", [])
    if isinstance(listed, list) and all(isinstance(item, str) for item in listed):
        ids.update(listed)
    if not ids:
        raise CompositionError("added diagnostic lacks exact resource scope")
    return ids


def _delta(base: dict[str, Any], treatment: dict[str, Any]) -> dict[str, Any]:
    base_ref = _ref(base)
    if treatment.get("lineage") != [base_ref]:
        raise CompositionError("treatment has different or ambiguous base lineage")
    if (treatment.get("promotion_state") != "provisional_pending_independent_review"
            or treatment.get("review_authority") not in {"agent", "human"}):
        raise CompositionError("treatment lacks explicit provisional review provenance")
    if treatment.get("form") != "source" or base.get("form") != "source":
        raise CompositionError("only materialized source packages can be composed")
    for key in set(base) | set(treatment):
        if key not in ALLOWED_TREATMENT_FIELDS and treatment.get(key) != base.get(key):
            raise CompositionError(f"treatment changed nonadditive package field {key}")
    base_resources = base["resources"]
    resources = treatment["resources"]
    if any(resources.get(rid) != value for rid, value in base_resources.items()):
        raise CompositionError("treatment changed or removed a base resource")
    added_resources = {rid: deepcopy(value) for rid, value in resources.items()
                       if rid not in base_resources}
    source_ids = {value.get("origin", {}).get("source_id")
                  for value in base_resources.values()}
    source_pages = {value.get("origin", {}).get("page_index")
                    for value in base_resources.values()}
    if len(source_ids) != 1 or None in source_ids:
        raise CompositionError("base source identity is not singular")
    for resource in added_resources.values():
        origin = resource.get("origin") or {}
        page_index = origin.get("page_index")
        if (origin.get("type") != "source" or origin.get("source_id") not in source_ids
                or not isinstance(page_index, int) or isinstance(page_index, bool)
                or page_index not in source_pages):
            raise CompositionError("added resource is outside pinned source pages")
    base_relations = base["relationships"]
    relations = treatment["relationships"]
    if relations[:len(base_relations)] != base_relations:
        raise CompositionError("treatment changed or removed a base relationship")
    added_relations = deepcopy(relations[len(base_relations):])
    existing_relations = {item["id"] for item in base_relations}
    if (len({item["id"] for item in added_relations}) != len(added_relations)
            or any(item["id"] in existing_relations for item in added_relations)):
        raise CompositionError("relationship ID collision within treatment")
    base_diagnostics = base.get("diagnostics", [])
    diagnostics = treatment.get("diagnostics", [])
    if diagnostics[:len(base_diagnostics)] != base_diagnostics:
        raise CompositionError("treatment changed or removed a base diagnostic")
    added_diagnostics = deepcopy(diagnostics[len(base_diagnostics):])
    base_issue_hashes = {_hash(item) for item in base_diagnostics}
    issue_hashes = [_hash(item) for item in added_diagnostics]
    if len(set(issue_hashes)) != len(issue_hashes) or base_issue_hashes.intersection(issue_hashes):
        raise CompositionError("diagnostic collision within treatment")
    footprint = set(added_resources)
    relation_by_id = {item["id"]: item for item in relations}
    for relation in added_relations:
        for key in ("source_id", "target_id"):
            rid = relation[key]
            if rid not in resources:
                raise CompositionError("added relation references unavailable resource")
            footprint.add(rid)
    for issue in added_diagnostics:
        scopes = _scope_ids(issue)
        if not scopes.issubset(resources):
            raise CompositionError("added diagnostic references unavailable resource")
        footprint.update(scopes)
        if "relationship_id" in issue:
            relation = relation_by_id.get(issue["relationship_id"])
            if relation is None:
                raise CompositionError("added diagnostic references unavailable relationship")
            footprint.update((relation["source_id"], relation["target_id"]))
    if not (added_resources or added_relations or added_diagnostics):
        raise CompositionError("empty treatment delta")
    review_records = {key: deepcopy(treatment[key]) for key in
                      ("reviewed_source_decisions", "reviewed_statblock_conflicts")
                      if key in treatment}
    if (not review_records or any(not isinstance(records, list) or not records
                                  for records in review_records.values())):
        raise CompositionError("treatment lacks attributed decision records")
    return {"ref": _ref(treatment), "review_authority": treatment["review_authority"],
            "review_records": review_records, "resources": added_resources,
            "relationships": added_relations, "diagnostics": added_diagnostics,
            "footprint": footprint, "diagnostic_hashes": issue_hashes}


def compose_provisional_treatments(*, base: dict[str, Any],
                                   treatments: list[dict[str, Any]],
                                   output_store: JsonPackageStore,
                                   package_id: str) -> dict[str, Any]:
    """Save a new immutable source package only for strictly disjoint deltas."""
    if len(treatments) != 2:
        raise CompositionError("composition requires exactly two treatments")
    _verify_revision(base)
    for treatment in treatments:
        _verify_revision(treatment)
    ordered = sorted(treatments, key=lambda item: (item["package_id"], item["revision"]))
    if len({_hash(_ref(item)) for item in ordered}) != 2:
        raise CompositionError("duplicate treatment revision")
    if package_id in {base["package_id"], *(item["package_id"] for item in ordered)}:
        raise CompositionError("combined package needs a distinct identity")
    deltas = [_delta(base, treatment) for treatment in ordered]
    left, right = deltas
    if (set(left["resources"]) & set(right["resources"])
            or {r["id"] for r in left["relationships"]} &
               {r["id"] for r in right["relationships"]}
            or set(left["diagnostic_hashes"]) & set(right["diagnostic_hashes"])
            or left["footprint"] & right["footprint"]):
        raise CompositionError("treatment deltas collide or overlap in resource scope")
    combined = deepcopy(base)
    combined.pop("revision", None)
    combined["package_id"] = package_id
    combined["title"] = f"{base['title']} with composed provisional treatments"
    combined["lineage"] = [delta["ref"] for delta in deltas]
    combined["composition_base_ref"] = _ref(base)
    combined["composition_recipe"] = RECIPE
    combined["promotion_state"] = "provisional_pending_independent_review"
    combined["component_treatments"] = []
    for delta in deltas:
        combined["resources"].update(delta["resources"])
        combined["relationships"].extend(delta["relationships"])
        combined.setdefault("diagnostics", []).extend(delta["diagnostics"])
        combined["component_treatments"].append({
            "ref": delta["ref"], "review_authority": delta["review_authority"],
            "promotion_state": "provisional_pending_independent_review",
            "review_records": delta["review_records"],
            "added_resource_ids": sorted(delta["resources"]),
            "added_relationship_ids": [item["id"] for item in delta["relationships"]],
            "added_diagnostic_sha256": delta["diagnostic_hashes"],
            "affected_resource_ids": sorted(delta["footprint"]),
        })
    return output_store.save(combined)


def build_combined_review_packet(*, expected: dict[str, Any],
                                 baseline: dict[str, Any],
                                 combined: dict[str, Any]) -> dict[str, Any]:
    """Open every frozen source case against the two-parent package, unjudged."""
    _verify_revision(baseline)
    _verify_revision(combined)
    base_ref = _ref(baseline)
    if (expected.get("review_package_ref") != base_ref
            or combined.get("composition_base_ref") != base_ref
            or combined.get("lineage") !=
               [item.get("ref") for item in combined.get("component_treatments", [])]
            or len(combined.get("lineage", [])) != 2
            or any(combined["resources"].get(rid) != value
                   for rid, value in baseline["resources"].items())):
        raise CompositionError("combined review base or lineage mismatch")
    source_id = f"sha256:{expected['source_pdf_sha256']}"
    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for resource in combined["resources"].values():
        origin = resource.get("origin") or {}
        page_index = origin.get("page_index", origin.get("pdf_page_index"))
        if (origin.get("type") != "source" or origin.get("source_id") != source_id
                or not isinstance(page_index, int) or isinstance(page_index, bool)
                or page_index < 0):
            raise CompositionError("combined resource lacks pinned physical page")
        by_page[page_index + 1].append(resource)
    packet = deepcopy(expected)
    packet["review_package_ref"] = _ref(combined)
    packet["available_resource_ids"] = sorted(combined["resources"])
    packet["treatment_basis"] = "combined_disjoint_provisional_additive_treatments"
    for case in packet["cases"]:
        page = case["evidence"]["pdf_page_1_based"]
        resources = by_page[page]
        case["candidate_text_resources"] = [item for item in resources
                                            if item["kind"] != "asset_reference"]
        case["candidate_asset_references"] = [item for item in resources
                                              if item["kind"] == "asset_reference"]
        case["candidate_resource_ids"] = [item["id"] for item in resources]
        case["review"] = None
    unsigned = {**packet, "cases": [{key: value for key, value in case.items()
                                    if key != "review"} for case in packet["cases"]]}
    unsigned.pop("context_sha256", None)
    packet["context_sha256"] = _hash(unsigned)
    return packet
