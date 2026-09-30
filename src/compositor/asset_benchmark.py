"""Unjudged recovery review for packages with distinct text and image sources."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any

from .package import CompositionError


HEX64 = re.compile(r"^[0-9a-f]{64}$")
IMAGE_LOCATOR = re.compile(r"^illustrated_pdf/page-([1-9][0-9]*)#xref=([1-9][0-9]*)$")
ASSET_CATEGORIES = {"asset_map", "asset_reference"}


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def build_asset_review_packet(*, run_id: str, gold: dict[str, Any],
                              source_manifest: dict[str, Any],
                              asset_manifest: dict[str, Any], package: dict[str, Any],
                              gold_sha256: str, source_manifest_sha256: str,
                              asset_manifest_sha256: str) -> dict[str, Any]:
    """Report source asset recovery facts without deciding gold verdicts."""
    if any(not HEX64.fullmatch(value) for value in
           (gold_sha256, source_manifest_sha256, asset_manifest_sha256)):
        raise CompositionError("asset review requires exact SHA-256 pins")
    cases = gold.get("cases")
    if gold.get("status") != "frozen" or not isinstance(cases, list) or len(cases) != gold.get("case_count"):
        raise CompositionError("asset review needs a complete frozen gold suite")
    sources = source_manifest.get("source_files") or {}
    illustrated = (sources.get("illustrated_pdf") or {}).get("sha256")
    markdown = (sources.get("normalized_markdown") or {}).get("sha256")
    if not source_manifest.get("accepted") or not all(
        isinstance(value, str) and HEX64.fullmatch(value) for value in (illustrated, markdown)
    ):
        raise CompositionError("accepted illustrated and Markdown source pins required")
    if asset_manifest.get("status") != "reference_only" or not isinstance(asset_manifest.get("assets"), list):
        raise CompositionError("reference-only asset manifest required")
    if (asset_manifest.get("illustrated_pdf") or {}).get("sha256") != illustrated:
        raise CompositionError("asset manifest illustrated source differs")
    package_ref = {"package_id": package.get("package_id"), "revision": package.get("revision")}
    if package.get("form") != "source" or not isinstance(package.get("resources"), dict) or \
            not isinstance(package_ref["revision"], str) or not HEX64.fullmatch(package_ref["revision"]):
        raise CompositionError("asset review needs an immutable source package")
    if package.get("asset_manifest_sha256") != asset_manifest_sha256:
        raise CompositionError("package asset manifest pin differs")
    resources = package["resources"]
    declared = {item["resource_id"]: item for item in asset_manifest["assets"]}
    if len(declared) != len(asset_manifest["assets"]):
        raise CompositionError("duplicate asset manifest identity")
    image_resources: dict[str, dict[str, Any]] = {}
    for resource_id, resource in resources.items():
        origin = resource.get("origin") or {}
        if resource.get("kind") == "asset_reference":
            item = declared.get(resource_id)
            if item is None or origin.get("source_id") != f"sha256:{illustrated}":
                raise CompositionError("asset source identity differs from illustrated source")
            match = IMAGE_LOCATOR.fullmatch(str(origin.get("locator", "")))
            if match is None or (int(match[1]), int(match[2])) != (item.get("printed_page"), item.get("xref")):
                raise CompositionError("asset page/xref locator differs from manifest")
            if (origin.get("printed_page") != item.get("printed_page")
                    or origin.get("pdf_page_index") != item.get("pdf_page_index")):
                raise CompositionError("asset page metadata differs from manifest")
            if (origin.get("image_sha256") != item.get("sha256")
                    or resource.get("asset", {}).get("sha256") != item.get("sha256")
                    or resource.get("asset", {}).get("status") != "reference_only"):
                raise CompositionError("asset digest or status differs from manifest")
            image_resources[resource_id] = resource
        elif origin.get("source_id") != f"sha256:{markdown}":
            raise CompositionError("text evidence source identity differs from Markdown")
    if set(image_resources) != set(declared):
        raise CompositionError("asset manifest and package resource inventory differ")
    entries = []
    seen: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise CompositionError("gold case IDs must be unique")
        seen.add(case_id)
        if case.get("category") not in ASSET_CATEGORIES:
            continue
        page = (case.get("evidence") or {}).get("illustrated_pdf_printed_page")
        if not isinstance(page, int) or page < 1:
            raise CompositionError(f"asset gold case {case_id} lacks illustrated page")
        candidates = [deepcopy(resource) for resource in image_resources.values()
                      if resource["origin"]["printed_page"] == page]
        candidates.sort(key=lambda item: item["id"])
        entries.append({
            "id": case_id, "category": case["category"], "task": case.get("task"),
            "severity": case.get("severity"), "audience": case.get("audience"),
            "source_evidence": deepcopy(case["evidence"]),
            "expectation": case.get("expectation"),
            "acceptable_alternatives": deepcopy(case.get("acceptable_alternatives", [])),
            "forbidden_outcomes": deepcopy(case.get("forbidden_outcomes", [])),
            "candidate_resources": candidates,
            "observed_recovery": "private_bytes_reference_only" if candidates else "no_package_asset_candidate",
            "semantic_competence": "not_assessed", "task_competence": "not_assessed",
            "review": None,
        })
    if not entries:
        raise CompositionError("frozen gold has no declared asset cases")
    packet = {"format_version": 1, "score_basis": "asset_recovery_only",
              "status": "unjudged", "run_id": run_id, "suite": gold.get("suite"),
              "gold_sha256": gold_sha256, "source_manifest_sha256": source_manifest_sha256,
              "asset_manifest_sha256": asset_manifest_sha256,
              "package_ref": package_ref,
              "available_resource_ids": sorted(image_resources), "cases": entries}
    packet["context_sha256"] = _hash({**packet, "cases": [
        {key: value for key, value in entry.items() if key != "review"} for entry in entries]})
    return packet
