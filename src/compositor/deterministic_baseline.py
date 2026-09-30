"""Immutable, no-provider evidence baseline and separate recovery coverage review.

The first result is assembled without access to gold. Coverage is computed only
after that result has been frozen, and says nothing about semantic correctness.
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
RECIPE = "deterministic-evidence-baseline-v1"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CompositionError("baseline input must be a JSON object")
    return value


def _expected(path: Path, digest: str, label: str) -> None:
    if not isinstance(digest, str) or not HEX64.fullmatch(digest) or _sha(path) != digest:
        raise CompositionError(f"{label} revision mismatch")


def _private_output(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise CompositionError("baseline output must be inside private root")
    return resolved


def freeze_first_evidence_result(*, store: JsonPackageStore, package_ref: dict[str, str],
                                 evidence_dir: Path, project_root: Path,
                                 source_manifest_path: Path, source_manifest_sha256: str,
                                 evidence_manifest_sha256: str, rules_ingestion_ref: str,
                                 suite: str, private_root: Path,
                                 output_path: Path) -> dict[str, Any]:
    """Verify the adapter replay and save its exact output once, without gold input."""
    source_manifest_path = Path(source_manifest_path)
    manifest_path = Path(evidence_dir) / "manifest.json"
    _expected(source_manifest_path, source_manifest_sha256, "source manifest")
    _expected(manifest_path, evidence_manifest_sha256, "evidence manifest")
    if not isinstance(suite, str) or not suite.strip():
        raise CompositionError("suite required")
    manifest = _json(manifest_path)
    route = manifest.get("route")
    if route not in {"supplied_markdown", "pdf_text"} or manifest.get("provider_calls") != 0:
        raise CompositionError("baseline requires zero-provider evidence")
    if manifest.get("rules_ingestion_ref") != rules_ingestion_ref:
        raise CompositionError("adapter revision mismatch")
    source_manifest = _json(source_manifest_path)
    source_files = source_manifest.get("source_files") or {}
    if (source_files.get("printer_friendly_pdf", {}).get("sha256") !=
            manifest.get("source_pdf_sha256") or
            (route == "supplied_markdown" and
             source_files.get("normalized_markdown", {}).get("sha256") !=
             manifest.get("supplied_markdown_sha256"))):
        raise CompositionError("source manifest does not bind evidence inputs")
    if not isinstance(manifest.get("recovery_method"), str) or not manifest["recovery_method"].strip():
        raise CompositionError("recovery method required")
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise CompositionError("baseline needs pinned pages")
    page_map = {}
    for page in pages:
        index, printed = page.get("page_index"), page.get("printed_page")
        if not isinstance(index, int) or not isinstance(printed, int) or index in page_map:
            raise CompositionError("invalid page identity in evidence manifest")
        page_map[index] = printed
    indices = list(page_map)
    if (indices != sorted(indices) or len(set(page_map.values())) != len(page_map)
            or list(page_map.values()) != sorted(page_map.values())
            or manifest.get("expected_page_indices") != indices):
        raise CompositionError("evidence page order mismatch")
    original = store.load(package_ref)
    replay = load_evidence_draft(
        store, evidence_dir, project_root=project_root,
        package_id=original["package_id"], title=original["title"],
        expected_rules_ingestion_ref=rules_ingestion_ref,
        expected_manifest_sha256=evidence_manifest_sha256,
    )
    if replay.package != original:
        raise CompositionError("evidence replay differs from pinned package")
    if any(issue.get("kind") == "missing_source" for issue in replay.report["diagnostics"]):
        raise CompositionError("pinned source unavailable")
    direct_sha = (manifest.get("supplied_markdown_sha256") if route == "supplied_markdown"
                  else manifest.get("source_pdf_sha256"))
    if not isinstance(direct_sha, str) or not HEX64.fullmatch(direct_sha):
        raise CompositionError("invalid direct source digest")
    for resource in original["resources"].values():
        origin = resource.get("origin", {})
        index = origin.get("page_index")
        if (index not in page_map or origin.get("source_id") != f"sha256:{direct_sha}"
                or not str(origin.get("locator", "")).startswith(
                    f"{route}/page-{index}/stageB.evidence_units.json#/units/")):
            raise CompositionError("resource provenance differs from evidence route")
    recovery_diagnostics = []
    for page in pages:
        surface = Path(evidence_dir) / page["artifact_dir"] / "stageA.surface.md"
        if not surface.read_text(encoding="utf-8").strip():
            recovery_diagnostics.append({"kind": "missing_text", "page_index": page["page_index"],
                                         "printed_page": page["printed_page"]})
    image_count = manifest.get("embedded_image_entries", 0)
    if not isinstance(image_count, int) or image_count < 0:
        raise CompositionError("invalid embedded image count")
    if image_count:
        recovery_diagnostics.append({"kind": "image_content_unsupported", "count": image_count})
    first = {
        "format_version": 1, "recipe": RECIPE, "recipe_sha256": _sha(Path(__file__)),
        "suite": suite, "route": route, "recovery_method": manifest["recovery_method"],
        "source_manifest_sha256": source_manifest_sha256,
        "evidence_manifest_sha256": evidence_manifest_sha256,
        "direct_source_sha256": direct_sha,
        "rules_ingestion_ref": rules_ingestion_ref,
        "page_map": {str(k): page_map[k] for k in sorted(page_map)},
        "package": original, "adapter_report": replay.report,
        "recovery_diagnostics": recovery_diagnostics,
        "provider_calls": 0, "provider_spend_usd": 0,
    }
    output = _private_output(Path(output_path), Path(private_root))
    encoded = json.dumps(first, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    if output.read_text(encoding="utf-8") != encoded:
        raise CompositionError("first result write integrity mismatch")
    return {"path": str(output), "sha256": _sha(output),
            "resource_count": len(original["resources"]), "provider_calls": 0}


def build_recovery_coverage(*, first_result_path: Path, first_result_sha256: str,
                            gold_path: Path, gold_sha256: str,
                            freeze_record_path: Path,
                            freeze_record_sha256: str) -> dict[str, Any]:
    """Score page-evidence recovery against frozen gold; leave meaning unjudged."""
    first_result_path, gold_path = Path(first_result_path), Path(gold_path)
    freeze_record_path = Path(freeze_record_path)
    _expected(first_result_path, first_result_sha256, "first result")
    _expected(gold_path, gold_sha256, "frozen gold")
    _expected(freeze_record_path, freeze_record_sha256, "gold freeze record")
    first, gold, freeze = (_json(first_result_path), _json(gold_path),
                           _json(freeze_record_path))
    if first.get("recipe") != RECIPE or first.get("provider_calls") != 0:
        raise CompositionError("wrong first-result recipe")
    route = first.get("route", "supplied_markdown")
    if route not in {"supplied_markdown", "pdf_text"}:
        raise CompositionError("unsupported first-result recovery route")
    if (gold.get("status") != "frozen" or gold.get("suite") != first.get("suite")
            or not isinstance(gold.get("cases"), list)
            or len(gold["cases"]) != gold.get("case_count")):
        raise CompositionError("review needs the separately frozen suite")
    files = freeze.get("files") or {}
    if (freeze.get("status") != "frozen" or freeze.get("suite") != first["suite"]
            or freeze.get("case_count") != len(gold["cases"])
            or files.get("proposal.json", {}).get("sha256") != gold_sha256
            or files.get("source_manifest.json", {}).get("sha256") != first["source_manifest_sha256"]):
        raise CompositionError("gold freeze does not bind this source and proposal")
    package = first["package"]
    page_map = {int(k): v for k, v in first["page_map"].items()}
    printed_to_index = {printed: index for index, printed in page_map.items()}
    if len(printed_to_index) != len(page_map):
        raise CompositionError("duplicate printed-page identity")
    by_page: dict[int, list[dict[str, Any]]] = {index: [] for index in page_map}
    for resource in package["resources"].values():
        index = resource["origin"]["page_index"]
        if index not in by_page:
            raise CompositionError("resource page outside first result")
        by_page[index].append(resource)
    gate_failures = Counter(
        str(issue.get("gate_name", "unknown")) for issue in package.get("diagnostics", [])
        if issue.get("kind") == "gate_failure")
    structural = {
        "resource_unit_count": sum(len(items) for items in by_page.values()),
        "pages_with_units": sum(bool(items) for items in by_page.values()),
        "pages_without_units": sum(not items for items in by_page.values()),
        "units_by_printed_page": {str(page_map[index]): len(by_page[index]) for index in page_map},
        "gate_failure_count": sum(gate_failures.values()),
        "gate_failures_by_name": dict(sorted(gate_failures.items())),
    }
    cases, totals = [], {"recovered_page_evidence": 0, "missing_page_evidence": 0,
                          "unsupported_image_evidence": 0}
    seen = set()
    for case in gold["cases"]:
        case_id = case.get("id")
        if not isinstance(case_id, str) or case_id in seen:
            raise CompositionError("invalid or repeated gold case ID")
        seen.add(case_id)
        evidence = case.get("evidence") or {}
        if route == "pdf_text":
            key, additional_key = ("printer_friendly_pdf_printed_page",
                                   "additional_printer_friendly_pdf_printed_pages")
        else:
            key, additional_key = ("normalized_markdown_page_marker",
                                   "additional_normalized_markdown_page_markers")
        markers = [evidence.get(key)]
        markers += evidence.get(additional_key) or []
        markers = sorted({marker for marker in markers if isinstance(marker, int)})
        indices = [printed_to_index.get(marker) for marker in markers]
        resources = [item for index in indices if index is not None for item in by_page[index]]
        image_only = str(case.get("category", "")).startswith("asset_")
        if image_only:
            state = "unsupported_image_evidence"
        elif not markers or any(index is None or not by_page[index] for index in indices):
            state = "missing_page_evidence"
        else:
            state = "recovered_page_evidence"
        totals[state] += 1
        cases.append({"id": case_id, "category": case.get("category"),
                      "printed_pages": markers, "coverage_state": state,
                      "candidate_resource_ids": sorted({item["id"] for item in resources}),
                      "semantic_verdict": None})
    return {"format_version": 1, "score_basis": "page_evidence_recovery_only",
            "score_recipe_sha256": _sha(Path(__file__)),
            "first_result_sha256": first_result_sha256, "frozen_gold_sha256": gold_sha256,
            "freeze_record_sha256": freeze_record_sha256,
            "suite": first["suite"], "recovery_route": route,
            "recovery_diagnostics": first.get("recovery_diagnostics", []),
            "total_cases": len(cases), "totals": totals, "structural": structural,
            "cases": cases, "provider_calls": 0, "provider_spend_usd": 0,
            "limitations": ["Candidate presence does not establish semantic correctness or task readiness.",
                            "Image-dependent cases require a separate asset recovery route."]}
