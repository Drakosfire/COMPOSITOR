"""Pinned, unjudged review context for a PDF evidence package and its assets."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .asset_inventory import project_asset_references
from .package import CompositionError, JsonPackageStore


def _pinned(path: Path, expected: str, label: str) -> dict[str, Any]:
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise CompositionError(f"{label} needs a SHA-256 pin")
    data = Path(path).read_bytes()
    if sha256(data).hexdigest() != expected:
        raise CompositionError(f"{label} revision mismatch")
    value = json.loads(data)
    if not isinstance(value, dict):
        raise CompositionError(f"{label} must be an object")
    return value


def _ref(package: dict[str, Any]) -> dict[str, str]:
    return {key: package[key] for key in ("package_id", "revision")}


def _page(resource: dict[str, Any], source_id: str, page_count: int) -> int:
    origin = resource.get("origin") or {}
    if origin.get("type") != "source" or origin.get("source_id") != source_id:
        raise CompositionError("package resource source identity mismatch")
    index = origin.get("page_index", origin.get("pdf_page_index"))
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < page_count:
        raise CompositionError("package resource physical page invalid")
    return index + 1


def build_package_review_packet(*, first_result_path: Path, first_result_sha256: str,
                                source_manifest_path: Path, source_manifest_sha256: str,
                                evidence_manifest_path: Path, evidence_manifest_sha256: str,
                                assembly_manifest_path: Path, assembly_manifest_sha256: str,
                                base_store: JsonPackageStore, base_ref: dict[str, str],
                                gold_path: Path, gold_sha256: str,
                                freeze_record_path: Path, freeze_record_sha256: str,
                                asset_store: JsonPackageStore | None = None,
                                asset_ref: dict[str, str] | None = None,
                                asset_manifest_path: Path | None = None,
                                asset_manifest_sha256: str | None = None,
                                private_root: Path | None = None) -> dict[str, Any]:
    """Reopen exact inputs, suggest page-local candidates, and leave verdicts blank.

    The source and package paths can contain private material. Save the returned
    packet only in the authorized private experiment store.
    """
    source = _pinned(source_manifest_path, source_manifest_sha256, "source manifest")
    first = _pinned(first_result_path, first_result_sha256, "first result")
    evidence = _pinned(evidence_manifest_path, evidence_manifest_sha256, "owner evidence manifest")
    assembly = _pinned(assembly_manifest_path, assembly_manifest_sha256, "assembly manifest")
    gold = _pinned(gold_path, gold_sha256, "frozen gold")
    freeze = _pinned(freeze_record_path, freeze_record_sha256, "gold freeze record")
    pdf = source.get("pdf") or {}
    pdf_sha = pdf.get("sha256")
    pdf_path = Path(pdf.get("path") or "")
    page_count = pdf.get("pages")
    if (not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 1
            or not pdf_path.is_file() or sha256(pdf_path.read_bytes()).hexdigest() != pdf_sha):
        raise CompositionError("source PDF revision or page count mismatch")
    try:
        import fitz
    except ImportError as exc:
        raise CompositionError("PyMuPDF required to verify source PDF pages") from exc
    with fitz.open(pdf_path) as document:
        if len(document) != page_count:
            raise CompositionError("source PDF physical page count mismatch")
    suite = source.get("suite")
    if any(value != suite for value in (first.get("suite"), gold.get("suite"), freeze.get("suite"))):
        raise CompositionError("suite identity mismatch")
    if any(value != source_manifest_sha256 for value in (
            first.get("source_manifest_sha256"), evidence.get("source_manifest_sha256"),
            gold.get("source_manifest_sha256"), freeze.get("source_manifest_sha256"))):
        raise CompositionError("source manifest identity mismatch")
    if any(value != pdf_sha for value in (
            first.get("source_pdf_sha256"), evidence.get("source_pdf_sha256"),
            gold.get("source_pdf_sha256"), freeze.get("source_pdf_sha256"))):
        raise CompositionError("source PDF identity mismatch")
    if (first.get("status") != "first_result_frozen_unscored" or first.get("gold_consulted") is not False
            or first.get("page_indices") != list(range(page_count))
            or evidence.get("expected_page_indices") != list(range(page_count))
            or first.get("owner_ref") != evidence.get("rules_ingestion_ref")
            or first.get("owner_receipt_sha256") != evidence.get("owner_output_receipt_sha256")):
        raise CompositionError("first result and owner evidence pins disagree")
    recipe = evidence.get("owner_recipe") or {}
    usage = evidence.get("provider_usage") or {}
    if (first.get("model") != recipe.get("model_id")
            or first.get("dpi") != recipe.get("dpi")
            or first.get("prompt") != recipe.get("prompt")
            or first.get("local_model_invocations") != usage.get("local_model_invocations")
            or first.get("provider_calls") != usage.get("calls")
            or first.get("provider_spend_usd") != usage.get("spend_usd")):
        raise CompositionError("owner recipe or usage pins disagree")
    if (assembly.get("first_result_sha256") != first_result_sha256
            or assembly.get("evidence_manifest_sha256") != evidence_manifest_sha256
            or assembly.get("package_ref") != base_ref
            or assembly.get("provider_calls") != first.get("provider_calls")):
        raise CompositionError("assembly pins disagree")
    if (gold.get("status") != "frozen" or freeze.get("status") != "frozen"
            or freeze.get("files", {}).get("proposal.json", {}).get("sha256") != gold_sha256
            or gold.get("case_count") != freeze.get("case_count")
            or len(gold.get("cases", [])) != gold.get("case_count")):
        raise CompositionError("gold freeze pins disagree")
    frozen_dir = Path(freeze_record_path).parent.resolve()
    for name, entry in freeze["files"].items():
        path = (frozen_dir / name).resolve()
        if (Path(name).is_absolute() or not path.is_relative_to(frozen_dir)
                or not path.is_file() or sha256(path.read_bytes()).hexdigest() != entry.get("sha256")):
            raise CompositionError(f"gold freeze file mismatch: {name}")
    base = base_store.load(base_ref)
    if _ref(base) != base_ref or base.get("form") != "source" or base.get("lineage"):
        raise CompositionError("base source package mismatch")
    if assembly.get("resource_count") != len(base["resources"]):
        raise CompositionError("assembly resource count mismatch")

    optional = (asset_store, asset_ref, asset_manifest_path, asset_manifest_sha256, private_root)
    if any(value is not None for value in optional) and not all(value is not None for value in optional):
        raise CompositionError("asset replay needs store, ref, manifest, hash, and private root")
    package = base
    if asset_store is not None:
        asset_manifest = _pinned(asset_manifest_path, asset_manifest_sha256, "asset manifest")
        if (asset_manifest.get("base_package_ref") != base_ref
                or asset_manifest.get("illustrated_pdf", {}).get("sha256") != pdf_sha):
            raise CompositionError("asset source or base package mismatch")
        package = asset_store.load(asset_ref)
        if (package.get("form") != "source" or package.get("lineage") != [base_ref]
                or package.get("asset_manifest_sha256") != asset_manifest_sha256
                or any(package["resources"].get(rid) != resource
                       for rid, resource in base["resources"].items())):
            raise CompositionError("derived asset package mismatch")
        with TemporaryDirectory() as temp:
            replay = project_asset_references(
                base_store=base_store, base_ref=base_ref,
                output_store=JsonPackageStore(Path(temp)), package_id=asset_ref["package_id"],
                manifest_path=asset_manifest_path,
                expected_manifest_sha256=asset_manifest_sha256, private_root=private_root)
        if replay != package:
            raise CompositionError("derived asset package replay mismatch")

    source_id = f"sha256:{pdf_sha}"
    candidates_by_page: dict[int, list[dict[str, Any]]] = {page: [] for page in range(1, page_count + 1)}
    for resource in package["resources"].values():
        candidates_by_page[_page(resource, source_id, page_count)].append(resource)
    groups = Counter(case.get("denominator_group") for case in gold["cases"])
    if (groups.get("source_fidelity") != freeze.get("denominators", {}).get("source_fidelity")
            or groups.get("integration_contract") != freeze.get("denominators", {}).get("integration_contract")
            or sum(groups.values()) != gold["case_count"]):
        raise CompositionError("gold denominator groups disagree")
    cases: list[dict[str, Any]] = []
    integration_cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for case in gold["cases"]:
        case_id = case.get("id")
        page = (case.get("evidence") or {}).get("pdf_page_1_based")
        if (not isinstance(case_id, str) or not case_id or case_id in seen
                or not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= page_count):
            raise CompositionError("gold case identity or physical page invalid")
        seen.add(case_id)
        common = {key: case.get(key) for key in (
            "id", "category", "task", "severity", "audience", "expectation_origin",
            "expectation", "acceptable_alternatives", "forbidden_outcomes", "rationale",
            "evidence", "denominator_group", "query_scope")}
        if case["denominator_group"] == "integration_contract":
            integration_cases.append({**common, "execution_state": "unexecuted",
                                      "required_owner_witness": True})
        else:
            candidates = candidates_by_page[page]
            cases.append({**common, "candidate_text_resources": [r for r in candidates
                          if r["kind"] != "asset_reference"],
                          "candidate_asset_references": [r for r in candidates
                          if r["kind"] == "asset_reference"],
                          "candidate_resource_ids": [r["id"] for r in candidates],
                          "review": None})
    context: dict[str, Any] = {
        "format_version": 1, "review_basis": "pinned_pdf_source_package",
        "task_success_inferred_from_candidates": False,
        "suite": suite, "source_manifest_sha256": source_manifest_sha256,
        "source_pdf_sha256": pdf_sha, "first_result_sha256": first_result_sha256,
        "owner_evidence_manifest_sha256": evidence_manifest_sha256,
        "assembly_manifest_sha256": assembly_manifest_sha256,
        "gold_sha256": gold_sha256, "freeze_record_sha256": freeze_record_sha256,
        "base_package_ref": base_ref, "review_package_ref": _ref(package),
        "asset_manifest_sha256": asset_manifest_sha256,
        "denominators": dict(groups), "provider_calls": first.get("provider_calls"),
        "available_resource_ids": sorted(package["resources"]),
        "cases": cases, "integration_cases": integration_cases,
    }
    unsigned = {**context, "cases": [{key: value for key, value in case.items()
                                     if key != "review"} for case in cases]}
    context["context_sha256"] = sha256(json.dumps(
        unsigned, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode()).hexdigest()
    return context
