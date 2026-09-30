"""Review source-backed map-to-prose links without inferring map semantics.

The visual correspondence is an attributed reviewer decision. This module pins
the PDF, embedded image, exact resource, and quote before recording that decision.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .package import CompositionError, JsonPackageStore
from .reviewed_source_decisions import build_treatment_review_packet


RECIPE = "review-map-asset-links-v1"


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode()).hexdigest()


def _normal(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _content_terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", value.casefold())) - {
        "the", "and", "are", "with", "from", "into", "that", "this", "its",
    }


def _verify_revision(package: dict[str, Any]) -> None:
    revision = package.get("revision")
    if not isinstance(revision, str) or _hash({k: v for k, v in package.items()
                                               if k != "revision"}) != revision:
        raise CompositionError("package revision integrity mismatch")


def prepare_map_asset_review(*, base: dict[str, Any], pdf_path: Path,
                             expected_pdf_sha256: str,
                             asset_paths: dict[str, Path]) -> dict[str, Any]:
    """Inventory selected pinned map assets and same-page prose, without gold."""
    _verify_revision(base)
    if sha256(Path(pdf_path).read_bytes()).hexdigest() != expected_pdf_sha256:
        raise CompositionError("source PDF revision mismatch")
    try:
        import fitz
    except ImportError as exc:
        raise CompositionError("PyMuPDF required for PDF quote verification") from exc
    with fitz.open(pdf_path) as document:
        page_count = len(document)
    source_id = f"sha256:{expected_pdf_sha256}"
    assets = []
    for asset_id, path in sorted(asset_paths.items()):
        resource = base["resources"].get(asset_id)
        if not resource or resource.get("kind") != "asset_reference":
            raise CompositionError("selected map asset is absent")
        origin = resource.get("origin") or {}
        page_index = origin.get("pdf_page_index")
        asset = resource.get("asset") or {}
        if (resource.get("audience") != "GM" or asset.get("audience_review") != "gm_only"
                or asset.get("status") != "reference_only"
                or origin.get("type") != "source" or origin.get("source_id") != source_id
                or origin.get("image_sha256") != asset.get("sha256")
                or not isinstance(page_index, int) or isinstance(page_index, bool)
                or not 0 <= page_index < page_count):
            raise CompositionError("map asset lacks pinned GM source scope")
        if sha256(Path(path).read_bytes()).hexdigest() != asset["sha256"]:
            raise CompositionError("map image bytes mismatch")
        candidates = sorted(rid for rid, item in base["resources"].items()
                            if item.get("kind") != "asset_reference"
                            and item.get("audience") == "GM"
                            and (item.get("origin") or {}).get("source_id") == source_id
                            and (item.get("origin") or {}).get("page_index") == page_index)
        assets.append({"asset_id": asset_id, "image_sha256": asset["sha256"],
                       "physical_page_1_based": page_index + 1,
                       "candidate_text_resource_ids": candidates})
    if not assets:
        raise CompositionError("no map asset selected")
    return {"format_version": 1, "recipe": RECIPE,
            "source_pdf_sha256": expected_pdf_sha256,
            "package_ref": {key: base[key] for key in ("package_id", "revision")},
            "assets": assets}


def apply_reviewed_map_asset_links(*, base: dict[str, Any], context: dict[str, Any],
                                   decisions: dict[str, Any], pdf_path: Path,
                                   expected_pdf_sha256: str,
                                   asset_paths: dict[str, Path],
                                   output_store: JsonPackageStore,
                                   package_id: str, max_reviews: int = 8) -> dict[str, Any]:
    """Save only reviewer-attributed, source-verified additive relations."""
    expected = prepare_map_asset_review(base=base, pdf_path=pdf_path,
        expected_pdf_sha256=expected_pdf_sha256, asset_paths=asset_paths)
    if context != expected or decisions.get("context_sha256") != _hash(expected):
        raise CompositionError("map review context changed")
    authority = decisions.get("review_authority")
    if authority not in {"agent", "human"}:
        raise CompositionError("review authority must be agent or human")
    reviews = decisions.get("reviews")
    if not isinstance(reviews, list) or not 0 < len(reviews) <= max_reviews:
        raise CompositionError("map review inventory or cap invalid")
    try:
        import fitz
    except ImportError as exc:
        raise CompositionError("PyMuPDF required for PDF quote verification") from exc
    with fitz.open(pdf_path) as document:
        page_text = [_normal(page.get_text("text")) for page in document]
    assets = {item["asset_id"]: item for item in expected["assets"]}
    relationships = deepcopy(base["relationships"])
    diagnostics = deepcopy(base.get("diagnostics", []))
    accepted = []
    seen: set[tuple[str, str, str]] = set()
    for review in reviews:
        if not isinstance(review, dict):
            raise CompositionError("invalid map review")
        asset_id, target_id = review.get("asset_id"), review.get("target_id")
        place = review.get("place_label")
        asset = assets.get(asset_id)
        if (not asset or target_id not in asset["candidate_text_resource_ids"]
                or not isinstance(place, str) or not place.strip()):
            raise CompositionError("map review target outside pinned page")
        key = (asset_id, target_id, place.casefold())
        if key in seen:
            raise CompositionError("duplicate map link decision")
        seen.add(key)
        choice = review.get("choice")
        if choice not in {"link", "unresolved"}:
            raise CompositionError("invalid map link choice")
        for field in ("reviewer", "rationale", "visual_basis", "source_quote", "pdf_quote"):
            if not isinstance(review.get(field), str) or len(review[field].strip()) < 8:
                raise CompositionError(f"map review needs {field}")
        text = base["resources"][target_id]["text"]
        source_quote = _normal(review["source_quote"])
        pdf_quote = _normal(review["pdf_quote"])
        if (source_quote not in _normal(text)
                or pdf_quote not in page_text[asset["physical_page_1_based"] - 1]
                or len(_content_terms(source_quote) & _content_terms(pdf_quote)) < 2):
            raise CompositionError("map link quote absent from pinned source")
        record = {field: review[field] for field in
                  ("asset_id", "target_id", "place_label", "choice", "reviewer",
                   "rationale", "visual_basis", "source_quote", "pdf_quote")}
        accepted.append(record)
        relation_id = f"reviewed-map-link-{_hash({**record, 'recipe': RECIPE})[:24]}"
        if choice == "unresolved":
            diagnostics.append({"kind": "interpretation_pending",
                "resource_ids": [asset_id, target_id], "detail_kind": "map_place_link_unresolved",
                "place_label": place, "reason": review["rationale"]})
            continue
        relationships.append({"id": relation_id, "source_id": asset_id,
            "target_id": target_id, "kind": "reviewed_map_depicts_place_claim",
            "place_label": place, "audience": "GM", "image_sha256": asset["image_sha256"],
            "physical_page_1_based": asset["physical_page_1_based"],
            "source_quote": source_quote, "pdf_quote": pdf_quote,
            "visual_basis": review["visual_basis"], "reviewer": review["reviewer"],
            "rationale": review["rationale"], "review_authority": authority})
    derived = deepcopy(base)
    derived.pop("revision", None)
    derived["package_id"] = package_id
    derived["title"] = f"{base['title']} with reviewed map asset links"
    derived["lineage"] = [{key: base[key] for key in ("package_id", "revision")}]
    derived["relationships"] = relationships
    derived["diagnostics"] = diagnostics
    derived["reviewed_map_asset_links"] = accepted
    derived["map_review_context_sha256"] = _hash(expected)
    derived["review_authority"] = authority
    derived["promotion_state"] = "provisional_pending_independent_review"
    return output_store.save(derived)


def build_map_treatment_packet(*, expected: dict[str, Any], baseline: dict[str, Any],
                               treated: dict[str, Any]) -> dict[str, Any]:
    """Reopen every frozen case blank; expose map relations for review."""
    _verify_revision(baseline)
    _verify_revision(treated)
    packet = build_treatment_review_packet(expected=expected, baseline=baseline,
                                           treated=treated)
    packet["treatment_basis"] = "additive_reviewed_map_asset_links"
    for case in packet["cases"]:
        page = case["evidence"]["pdf_page_1_based"]
        case["candidate_map_relationships"] = [deepcopy(relation)
            for relation in treated["relationships"]
            if relation.get("kind") == "reviewed_map_depicts_place_claim"
            and relation.get("physical_page_1_based") == page]
    return packet
