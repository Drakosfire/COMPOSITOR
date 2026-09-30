"""Apply exact, reviewed OCR corrections without editing the first package.

Reviewers supply the source decision. This module verifies pins and creates a
new immutable Composition; it performs no OCR or automatic normalization.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .package import (CompositionError, JsonPackageStore, derive, edit_resource,
                      save_derived)


HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def apply_reviewed_text_corrections(*, source_store: JsonPackageStore,
                                    output_store: JsonPackageStore,
                                    base_ref: dict[str, str], package_id: str,
                                    title: str, source_path: Path,
                                    source_sha256: str,
                                    corrections: list[dict[str, Any]]) -> dict[str, Any]:
    """Save a snapshot with only exact source-checked resource text decisions."""
    if not HEX64.fullmatch(source_sha256) or sha256(Path(source_path).read_bytes()).hexdigest() != source_sha256:
        raise CompositionError("source revision mismatch")
    if not isinstance(corrections, list) or not corrections:
        raise CompositionError("reviewed corrections required")
    base = source_store.load(base_ref)
    if base["form"] != "source":
        raise CompositionError("reviewed correction requires a source package")
    base_path = source_store.path_for(base["package_id"], base["revision"])
    target_path = output_store.path_for(base["package_id"], base["revision"])
    target_path.parent.mkdir(parents=True, exist_ok=True)
    base_bytes = base_path.read_bytes()
    try:
        with target_path.open("xb") as stream:
            stream.write(base_bytes)
    except FileExistsError:
        if target_path.read_bytes() != base_bytes:
            raise CompositionError("output store has conflicting base bytes")
    draft = derive(output_store, base_ref, package_id=package_id, title=title)
    seen: set[str] = set()
    for correction in corrections:
        if not isinstance(correction, dict):
            raise CompositionError("reviewed correction must be an object")
        rid = correction.get("resource_id")
        if not isinstance(rid, str) or rid in seen or rid not in draft.resources:
            raise CompositionError("missing or duplicate correction resource")
        seen.add(rid)
        current = draft.resources[rid]
        origin = current["origin"]
        if (origin.get("type") != "source"
                or origin.get("source_id") != f"sha256:{source_sha256}"
                or origin.get("page_index") != correction.get("page_index")
                or origin.get("locator") != correction.get("locator")):
            raise CompositionError("correction source locator mismatch")
        expected = correction.get("expected_text")
        replacement = correction.get("replacement_text")
        if (not isinstance(expected, str) or current["text"] != expected
                or not isinstance(replacement, str) or not replacement
                or replacement == expected):
            raise CompositionError("correction text differs from pinned evidence")
        if (not isinstance(correction.get("printed_page"), int)
                or correction["printed_page"] < 1
                or not isinstance(correction.get("reviewer"), str)
                or not correction["reviewer"].strip()
                or not isinstance(correction.get("rationale"), str)
                or len(correction["rationale"].strip()) < 12
                or not HEX64.fullmatch(str(correction.get("rendered_page_sha256", "")))):
            raise CompositionError("correction needs reviewed source evidence")
        updated = deepcopy(current)
        updated["text"] = replacement
        updated["origin"] = {
            "type": "authored",
            "reason": "reviewed correction of source OCR text",
            "source_review": {
                "source_pdf_sha256": source_sha256,
                "page_index": correction["page_index"],
                "printed_page": correction["printed_page"],
                "rendered_page_sha256": correction["rendered_page_sha256"],
                "reviewer": correction["reviewer"],
                "rationale": correction["rationale"],
            },
        }
        if edit_resource(draft, updated):
            raise CompositionError("correction has dependent impact requiring separate review")
    return save_derived(output_store, draft, form="snapshot")


def build_correction_review_packet(*, baseline_packet: dict[str, Any],
                                   baseline: dict[str, Any],
                                   treated: dict[str, Any],
                                   changed_resource_ids: list[str]) -> dict[str, Any]:
    """Reopen every case blank against a strictly text-only derived snapshot."""
    base_ref = {key: baseline[key] for key in ("package_id", "revision")}
    if (baseline_packet.get("package_ref") != base_ref
            or treated.get("form") != "snapshot"
            or treated.get("lineage") != [base_ref]
            or set(treated.get("resources", {})) != set(baseline.get("resources", {}))):
        raise CompositionError("correction review base mismatch")
    changed = {rid for rid, resource in treated["resources"].items()
               if resource != baseline["resources"][rid]}
    if not changed or changed != set(changed_resource_ids):
        raise CompositionError("correction changed unexpected resources")
    for rid in changed:
        old = baseline["resources"][rid]
        new = treated["resources"][rid]
        if ({key: value for key, value in old.items() if key not in {"text", "origin"}}
                != {key: value for key, value in new.items() if key not in {"text", "origin"}}
                or new["origin"].get("derived_from", {}).get("resource_id") != rid):
            raise CompositionError("correction changed non-text resource fields")
    packet = deepcopy(baseline_packet)
    packet["package_ref"] = {key: treated[key] for key in ("package_id", "revision")}
    packet["treatment_basis"] = "exact_reviewed_source_text_correction"
    packet["changed_resource_ids"] = sorted(changed)
    for case in packet["cases"]:
        case["candidate_resources"] = [treated["resources"][r["id"]]
                                       for r in case["candidate_resources"]]
        case["review"] = None
    unsigned = {**packet, "cases": [{key: value for key, value in case.items()
                                    if key != "review"} for case in packet["cases"]]}
    unsigned.pop("context_sha256", None)
    packet["context_sha256"] = _hash(unsigned)
    return packet
