"""Project a pinned Docling intermediate into source evidence resources.

This is recovery, not rule interpretation. Text, table structures, and image
references retain reversible intermediate locators and the exact PDF identity.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .package import CompositionError, JsonPackageStore, make_source_package


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class DoclingDraftResult:
    package: dict[str, Any]
    report: dict[str, Any]


def _pinned_bytes(path: Path, expected: str, label: str) -> bytes:
    if not _SHA256.fullmatch(expected):
        raise CompositionError(f"{label} requires an exact SHA-256 pin")
    try:
        raw = Path(path).read_bytes()
    except FileNotFoundError as exc:
        raise CompositionError(f"{label} unavailable") from exc
    if sha256(raw).hexdigest() != expected:
        raise CompositionError(f"{label} revision mismatch")
    return raw


def _pages(document: dict[str, Any]) -> set[int]:
    listed = document.get("pages")
    if not isinstance(listed, dict) or not listed:
        raise CompositionError("Docling pages unavailable")
    numbers: set[int] = set()
    for key, value in listed.items():
        if not isinstance(key, str) or not key.isdecimal() or not isinstance(value, dict):
            raise CompositionError("invalid Docling page index")
        number = int(key)
        if number < 1 or value.get("page_no") != number:
            raise CompositionError("Docling page key and page number differ")
        numbers.add(number)
    return numbers


def _provenance(item: dict[str, Any], valid_pages: set[int]) -> list[dict[str, Any]]:
    prov = item.get("prov")
    if not isinstance(prov, list) or not prov:
        return []
    valid = []
    for entry in prov:
        if not isinstance(entry, dict) or entry.get("page_no") not in valid_pages:
            return []
        valid.append(deepcopy(entry))
    return valid


def load_docling_evidence_draft(
    store: JsonPackageStore, *, pdf_path: Path, docling_path: Path,
    expected_pdf_sha256: str, expected_docling_sha256: str,
    package_id: str, title: str, selected_pages: list[int] | None = None,
) -> DoclingDraftResult:
    """Save a source package from exact PDF/Docling bytes, without inference."""
    pdf = _pinned_bytes(pdf_path, expected_pdf_sha256, "source PDF")
    if not pdf.startswith(b"%PDF-"):
        raise CompositionError("source PDF is not a PDF")
    raw = _pinned_bytes(docling_path, expected_docling_sha256, "Docling intermediate")
    try:
        document = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CompositionError("invalid Docling JSON") from exc
    if not isinstance(document, dict) or document.get("schema_name") != "DoclingDocument":
        raise CompositionError("unsupported Docling document")
    valid_pages = _pages(document)
    if selected_pages is not None and (not isinstance(selected_pages, list)
            or any(not isinstance(page, int) or isinstance(page, bool) for page in selected_pages)):
        raise CompositionError("selected pages must be integer page numbers")
    scope = valid_pages if selected_pages is None else set(selected_pages)
    if not scope or not scope.issubset(valid_pages):
        raise CompositionError("selected pages must exist in the Docling document")
    diagnostics: list[dict[str, Any]] = [
        {"kind": "interpretation_pending"},
        {"kind": "source_correspondence_unverified"},
    ]
    if scope != valid_pages:
        diagnostics.append({"kind": "partial_source_scope", "selected_pages": sorted(scope),
                            "total_pages": len(valid_pages)})
    resources: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}
    for collection, kind in (("texts", "evidence_text"), ("tables", "evidence_table"),
                             ("pictures", "asset_reference")):
        items = document.get(collection)
        if not isinstance(items, list):
            raise CompositionError(f"Docling {collection} unavailable")
        counts[collection] = 0
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                diagnostics.append({"kind": "invalid_docling_element", "collection": collection,
                                    "index": index})
                continue
            prov = _provenance(item, valid_pages)
            if not prov:
                diagnostics.append({"kind": "missing_element_provenance", "collection": collection,
                                    "index": index})
                continue
            item_pages = {entry["page_no"] for entry in prov}
            if not item_pages & scope:
                continue
            rid = f"docling-{collection}-{index}"
            origin = {"type": "source", "source_id": f"sha256:{expected_pdf_sha256}",
                      "locator": f"docling-json#/{collection}/{index}",
                      "intermediate_sha256": expected_docling_sha256,
                      "docling_self_ref": item.get("self_ref"),
                      "pages": sorted(item_pages), "provenance": prov}
            for key in ("parent", "children", "label", "level", "captions", "references"):
                if key in item:
                    origin[f"docling_{key}"] = deepcopy(item[key])
            if collection == "texts":
                body = item.get("text")
                if not isinstance(body, str):
                    diagnostics.append({"kind": "invalid_docling_text", "index": index})
                    continue
                name = str(item.get("label") or "text")
                resource = {"id": rid, "kind": kind, "name": name,
                            "text": body, "audience": "GM", "origin": origin}
            elif collection == "tables":
                data = item.get("data")
                if not isinstance(data, dict):
                    diagnostics.append({"kind": "invalid_docling_table", "index": index})
                    continue
                resource = {"id": rid, "kind": kind, "name": "Docling table",
                            "text": json.dumps(data, sort_keys=True, ensure_ascii=False),
                            "table_data": deepcopy(data), "audience": "GM", "origin": origin}
                diagnostics.append({"kind": "table_cell_review_pending", "resource_id": rid})
            else:
                resource = {"id": rid, "kind": kind, "name": "Docling picture",
                            "text": "Image reference; bytes not recovered by this adapter.",
                            "audience": "GM", "origin": origin,
                            "asset": {"status": "reference_only"}}
                diagnostics.append({"kind": "asset_inventory_pending", "resource_id": rid})
            resources[rid] = resource
            counts[collection] += 1
    package = make_source_package(store, package_id=package_id, title=title,
                                  resources=resources, diagnostics=diagnostics)
    return DoclingDraftResult(package=package, report={
        "route": "pinned_docling_intermediate", "docling_version": document.get("version"),
        "source_pdf_sha256": expected_pdf_sha256,
        "docling_sha256": expected_docling_sha256, "selected_pages": sorted(scope),
        "total_pages": len(valid_pages), "resource_counts": counts,
        "diagnostics": deepcopy(diagnostics), "provider_calls": 0,
        "semantic_interpretation": "not_performed",
        "pdf_to_intermediate_correspondence": "not_verified_by_adapter",
    })
