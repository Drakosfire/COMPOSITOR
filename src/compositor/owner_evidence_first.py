"""Freeze owner-produced A/B evidence before consulting frozen gold.

This module consumes the RulesIngestion A/B bridge. It does no OCR, inference,
semantic scoring, or repair. A selected-page pilot must not imply full coverage.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .evidence_adapter import load_evidence_draft
from .package import CompositionError, JsonPackageStore


HEX64 = re.compile(r"^[0-9a-f]{64}$")
RECIPE = "rules-ingestion-ab-first-result-v1"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _pinned_json(path: Path, expected: str, label: str) -> dict[str, Any]:
    if not isinstance(expected, str) or not HEX64.fullmatch(expected) or _sha(path) != expected:
        raise CompositionError(f"{label} revision mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CompositionError(f"{label} must be a JSON object")
    return value


def freeze_owner_first_result(*, store: JsonPackageStore,
                              package_ref: dict[str, str], evidence_dir: Path,
                              project_root: Path, source_manifest_path: Path,
                              source_manifest_sha256: str,
                              evidence_manifest_sha256: str,
                              rules_ingestion_ref: str, suite: str,
                              printed_page_map: dict[int, int],
                              private_root: Path, output_path: Path) -> dict[str, Any]:
    """Verify owner bundle replay and write an immutable, gold-free first result."""
    evidence_dir = Path(evidence_dir)
    manifest = _pinned_json(evidence_dir / "manifest.json", evidence_manifest_sha256,
                            "evidence manifest")
    source_manifest = _pinned_json(Path(source_manifest_path), source_manifest_sha256,
                                   "source manifest")
    if manifest.get("route") != "rules_ingestion_ab":
        raise CompositionError("first result requires owner A/B evidence")
    if manifest.get("rules_ingestion_ref") != rules_ingestion_ref:
        raise CompositionError("RulesIngestion ref mismatch")
    if not isinstance(suite, str) or not suite.strip() or source_manifest.get("suite") != suite:
        raise CompositionError("source suite mismatch")
    source_files = source_manifest.get("source_files")
    if (not isinstance(source_files, dict) or
            source_files.get("printer_friendly_pdf", {}).get("sha256")
            != manifest.get("source_pdf_sha256")):
        raise CompositionError("source manifest does not bind owner PDF")
    indices = manifest.get("expected_page_indices")
    if (not isinstance(printed_page_map, dict) or not isinstance(indices, list)
            or sorted(printed_page_map) != indices
            or any(type(index) is not int or type(page) is not int or
                   index < 0 or page < 1 for index, page in printed_page_map.items())
            or len(set(printed_page_map.values())) != len(indices)
            or [printed_page_map[index] for index in indices] !=
            sorted(printed_page_map.values())):
        raise CompositionError("printed-page map must match selected owner pages")
    output = Path(output_path).resolve()
    if not output.is_relative_to(Path(private_root).resolve()):
        raise CompositionError("first result output must be inside private root")
    original = store.load(package_ref)
    replay = load_evidence_draft(
        store, evidence_dir, project_root=project_root,
        package_id=original["package_id"], title=original["title"],
        expected_rules_ingestion_ref=rules_ingestion_ref,
        expected_manifest_sha256=evidence_manifest_sha256,
    )
    if replay.package != original:
        raise CompositionError("owner evidence replay differs from pinned package")
    if any(item.get("kind") == "missing_source" for item in replay.report["diagnostics"]):
        raise CompositionError("pinned owner source unavailable")
    source_sha = manifest["source_pdf_sha256"]
    for resource in original["resources"].values():
        origin = resource.get("origin", {})
        index = origin.get("page_index")
        if (index not in printed_page_map or origin.get("source_id") != f"sha256:{source_sha}"
                or not str(origin.get("locator", "")).startswith(
                    f"rules_ingestion_ab/page-{index}/stageB.evidence_units.json#/units/")):
            raise CompositionError("resource provenance differs from owner A/B evidence")
    first = {
        "format_version": 1, "recipe": RECIPE, "recipe_sha256": _sha(Path(__file__)),
        "suite": suite, "route": "rules_ingestion_ab",
        "source_manifest_sha256": source_manifest_sha256,
        "evidence_manifest_sha256": evidence_manifest_sha256,
        "direct_source_sha256": source_sha,
        "rules_ingestion_ref": rules_ingestion_ref,
        "page_map": {str(index): printed_page_map[index] for index in indices},
        "package": original, "adapter_report": replay.report,
        "owner_recipe": manifest["owner_recipe"],
        "provider_usage": manifest["provider_usage"],
    }
    encoded = json.dumps(first, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    if output.read_text(encoding="utf-8") != encoded:
        raise CompositionError("first result write integrity mismatch")
    return {"path": str(output), "sha256": _sha(output),
            "resource_count": len(original["resources"]),
            "provider_usage": manifest["provider_usage"]}


def score_owner_page_coverage(*, first_result_path: Path, first_result_sha256: str,
                              gold_path: Path, gold_sha256: str,
                              freeze_record_path: Path,
                              freeze_record_sha256: str) -> dict[str, Any]:
    """Map frozen gold to selected owner pages without judging semantic quality."""
    first = _pinned_json(Path(first_result_path), first_result_sha256, "first result")
    gold = _pinned_json(Path(gold_path), gold_sha256, "frozen gold")
    freeze = _pinned_json(Path(freeze_record_path), freeze_record_sha256,
                          "gold freeze record")
    if first.get("recipe") != RECIPE or first.get("route") != "rules_ingestion_ab":
        raise CompositionError("wrong owner first-result recipe")
    if (gold.get("status") != "frozen" or gold.get("suite") != first.get("suite")
            or not isinstance(gold.get("cases"), list)
            or len(gold["cases"]) != gold.get("case_count")):
        raise CompositionError("review needs separately frozen gold")
    files = freeze.get("files") or {}
    if (freeze.get("status") != "frozen" or freeze.get("suite") != first["suite"]
            or freeze.get("case_count") != len(gold["cases"])
            or files.get("proposal.json", {}).get("sha256") != gold_sha256
            or files.get("source_manifest.json", {}).get("sha256") !=
            first["source_manifest_sha256"]):
        raise CompositionError("gold freeze does not bind this source and proposal")
    page_map = {int(index): page for index, page in first["page_map"].items()}
    printed_to_index = {printed: index for index, printed in page_map.items()}
    if len(printed_to_index) != len(page_map):
        raise CompositionError("duplicate printed-page identity")
    by_page: dict[int, list[str]] = {index: [] for index in page_map}
    for resource in first["package"]["resources"].values():
        index = resource["origin"]["page_index"]
        if index not in by_page:
            raise CompositionError("resource page outside first result")
        by_page[index].append(resource["id"])
    states = Counter()
    cases = []
    seen = set()
    for case in gold["cases"]:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise CompositionError("invalid or repeated gold case ID")
        seen.add(case_id)
        evidence = case.get("evidence") or {}
        markers = [evidence.get("printer_friendly_pdf_printed_page")]
        markers.extend(evidence.get("additional_printer_friendly_pdf_printed_pages") or [])
        markers = sorted({page for page in markers if type(page) is int and page > 0})
        in_scope = [page for page in markers if page in printed_to_index]
        missing = [page for page in markers if page not in printed_to_index]
        candidates = sorted({uid for page in in_scope
                             for uid in by_page[printed_to_index[page]]})
        if not markers or not in_scope:
            state = "out_of_scope"
        elif missing:
            state = "partial_scope"
        elif str(case.get("category", "")).startswith("asset_"):
            state = "unsupported_image_evidence"
        elif any(not by_page[printed_to_index[page]] for page in in_scope):
            state = "missing_page_evidence"
        else:
            state = "recovered_page_evidence"
        states[state] += 1
        cases.append({"id": case_id, "category": case.get("category"),
                      "task": case.get("task"), "severity": case.get("severity"),
                      "printed_pages": markers, "selected_printed_pages": in_scope,
                      "unselected_printed_pages": missing, "coverage_state": state,
                      "candidate_resource_ids": candidates, "semantic_verdict": None})
    fully_scoped = (states["recovered_page_evidence"] + states["missing_page_evidence"]
                    + states["unsupported_image_evidence"])
    failures = Counter(str(item.get("gate_name", "unknown"))
                       for item in first["package"].get("diagnostics", [])
                       if item.get("kind") == "gate_failure")
    return {
        "format_version": 1, "score_basis": "selected_owner_page_evidence_only",
        "score_recipe_sha256": _sha(Path(__file__)),
        "first_result_sha256": first_result_sha256,
        "frozen_gold_sha256": gold_sha256,
        "freeze_record_sha256": freeze_record_sha256,
        "suite": first["suite"], "recovery_route": first["route"],
        "selected_page_map": first["page_map"],
        "total_cases": len(cases), "fully_scoped_cases": fully_scoped,
        "totals": {state: states[state] for state in (
            "out_of_scope", "partial_scope", "recovered_page_evidence",
            "missing_page_evidence", "unsupported_image_evidence")},
        "structural": {"resource_unit_count": len(first["package"]["resources"]),
                       "units_by_printed_page": {str(page_map[index]): len(by_page[index])
                                                 for index in page_map},
                       "gate_failures_by_name": dict(sorted(failures.items()))},
        "provider_usage": first["provider_usage"],
        "cases": cases,
        "limitations": ["Page presence does not establish semantic correctness or task readiness.",
                        "Unselected cases are excluded from the fully scoped denominator.",
                        "Image-dependent cases need a separate asset treatment."],
    }
