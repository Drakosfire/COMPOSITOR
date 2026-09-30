"""Gold-blind candidate discovery and reviewed, additive source decisions.

This module makes no model calls. A candidate is a prompt for explicit review, not
an assertion that two source statements have the same scope or meaning.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from difflib import SequenceMatcher
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .package import CompositionError, JsonPackageStore


RECIPE_VERSION = "reviewed-source-decisions-v1"
IDENTITY = re.compile(
    r"\b(?:[Tt]he|[Aa]n?)\s+(?P<form>[a-z][a-z -]{1,35}?)\s+introduces itself as\s+"
    r"(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})(?:,\s+an?\s+(?P<role>[a-z]+))?",
)
FAILURE = re.compile(r"\bfail(?:s|ed|ure)?\b", re.IGNORECASE)
FATAL = re.compile(r"\b(?:die|dies|died|death|dead)\b", re.IGNORECASE)
TRANSFORM = re.compile(r"\b(?:transmut\w*|transform\w*)\b", re.IGNORECASE)
CHARGE_USED = re.compile(r"\b(?:a|one|each)\s+charge\s+is\s+used\b", re.IGNORECASE)
CHARGE_REMAINING = re.compile(r"\b(?:each|per)\s+charge\s+remaining\b", re.IGNORECASE)


def _digest(path: Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clause(text: str, match: re.Match[str]) -> str:
    """Keep a matched phrase with nearby context, stopping at sentence edges."""
    start = max(text.rfind(".", 0, match.start()) + 1, text.rfind("\n", 0, match.start()) + 1)
    end = text.find(".", match.end())
    if end < 0:
        end = len(text)
    else:
        end += 1
    return _normal(text[start:end])


def _source_quote(page_text: str, excerpt: str, *, required_terms: tuple[str, ...],
                  full_excerpt: bool = False) -> str:
    """Return a PDF span that contains every term needed for the proposed claim."""
    source = _normal(page_text)
    normalized_excerpt = _normal(excerpt)
    if full_excerpt:
        start = source.find(normalized_excerpt)
        if start < 0:
            raise CompositionError("candidate assertion absent from exact PDF quote")
        quote = source[start:start + len(normalized_excerpt)]
    else:
        match = SequenceMatcher(None, source, normalized_excerpt, autojunk=False).find_longest_match()
        start, end = match.a, match.a + match.size
        while start > 0 and source[start - 1].isalnum():
            start -= 1
        while end < len(source) and source[end].isalnum():
            end += 1
        quote = source[start:end].strip()
        if match.size < 0.45 * len(normalized_excerpt):
            raise CompositionError("candidate lacks a substantial exact PDF quote")
    if (len(quote) < 35 or not re.search(r"[A-Za-z]", quote)
            or any(_normal(term).casefold() not in quote.casefold() for term in required_terms)):
        raise CompositionError("candidate lacks a substantial exact PDF quote")
    return quote


def _resource_page(resource: dict[str, Any], source_id: str, page_count: int) -> int:
    origin = resource.get("origin") or {}
    if origin.get("type") != "source" or origin.get("source_id") != source_id:
        raise CompositionError("candidate package source identity mismatch")
    index = origin.get("page_index", origin.get("pdf_page_index"))
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < page_count:
        raise CompositionError("candidate package physical page invalid")
    return index + 1


def discover_source_decisions(*, package: dict[str, Any], pdf_path: Path,
                              expected_pdf_sha256: str) -> dict[str, Any]:
    """Scan every resource without gold, then emit source-anchored review cues."""
    if _digest(pdf_path) != expected_pdf_sha256:
        raise CompositionError("source PDF revision mismatch")
    try:
        import fitz
    except ImportError as exc:
        raise CompositionError("PyMuPDF required for source quote verification") from exc
    with fitz.open(pdf_path) as document:
        page_texts = [page.get_text("text") for page in document]
    source_id = f"sha256:{expected_pdf_sha256}"
    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    scanned = 0
    text_scanned = 0
    for resource in package["resources"].values():
        scanned += 1
        page = _resource_page(resource, source_id, len(page_texts))
        if resource["kind"] != "asset_reference":
            text_scanned += 1
            by_page[page].append(resource)
    candidates: list[dict[str, Any]] = []

    def emit(kind: str, page: int, resources: list[dict[str, Any]],
             excerpts: list[str], proposed: dict[str, Any],
             required_terms: list[tuple[str, ...]], *, full_excerpt: bool = False) -> None:
        evidence = []
        for resource, excerpt, terms in zip(resources, excerpts, required_terms, strict=True):
            evidence.append({"resource_id": resource["id"], "source_quote":
                             _source_quote(page_texts[page - 1], excerpt,
                                           required_terms=terms, full_excerpt=full_excerpt),
                             "evidence_excerpt": excerpt})
        body = {"kind": kind, "physical_page_1_based": page,
                "resource_ids": [resource["id"] for resource in resources],
                "evidence": evidence, "proposed": proposed}
        candidates.append({"id": _hash({"recipe": RECIPE_VERSION, **body}), **body})

    for page in sorted(by_page):
        resources = sorted(by_page[page], key=lambda item: item["id"])
        for resource in resources:
            for match in IDENTITY.finditer(resource["text"]):
                emit("identity_form", page, [resource], [_normal(match.group(0))],
                     {"name": match.group("name"), "form": match.group("form").strip(),
                      "role": match.group("role")},
                     [(match.group("name"), match.group("form"))], full_excerpt=True)
        fatal = [resource for resource in resources if FAILURE.search(resource["text"])
                 and FATAL.search(resource["text"])]
        transformed = [resource for resource in resources if FAILURE.search(resource["text"])
                       and TRANSFORM.search(resource["text"])]
        for left in fatal:
            for right in transformed:
                if left["id"] == right["id"]:
                    continue
                emit("outcome_tension", page, [left, right],
                     [_clause(left["text"], FATAL.search(left["text"])),
                      _clause(right["text"], TRANSFORM.search(right["text"]))],
                     {"status": "potential_tension_not_equivalence"},
                     [(FAILURE.search(left["text"]).group(0), FATAL.search(left["text"]).group(0)),
                      (FAILURE.search(right["text"]).group(0), TRANSFORM.search(right["text"]).group(0))])
        used = [resource for resource in resources if CHARGE_USED.search(resource["text"])]
        remaining = [resource for resource in resources if CHARGE_REMAINING.search(resource["text"])]
        for left in used:
            for right in remaining:
                if left["id"] == right["id"]:
                    continue
                emit("charge_timing", page, [left, right],
                     [_clause(left["text"], CHARGE_USED.search(left["text"])),
                      _clause(right["text"], CHARGE_REMAINING.search(right["text"]))],
                     {"status": "timing_unresolved"},
                     [(CHARGE_USED.search(left["text"]).group(0),),
                      (CHARGE_REMAINING.search(right["text"]).group(0),)])
    candidates.sort(key=lambda item: (item["physical_page_1_based"], item["kind"], item["id"]))
    if len({candidate["id"] for candidate in candidates}) != len(candidates):
        raise CompositionError("duplicate source decision candidate")
    return {"format_version": 1, "recipe": RECIPE_VERSION,
            "source_pdf_sha256": expected_pdf_sha256,
            "package_ref": {key: package[key] for key in ("package_id", "revision")},
            "scanned_resources": scanned, "scanned_text_resources": text_scanned,
            "candidates": candidates}


CHOICES = {"identity_form": "accept_identity_form",
           "outcome_tension": "record_attributed_tension",
           "charge_timing": "record_unresolved_timing"}


def apply_reviewed_source_decisions(*, base: dict[str, Any], candidates: dict[str, Any],
                                    decisions: dict[str, Any], pdf_path: Path,
                                    expected_pdf_sha256: str,
                                    output_store: JsonPackageStore,
                                    package_id: str, max_reviewed: int = 3) -> dict[str, Any]:
    """Recompute candidates and validate attributed choices before an additive save."""
    expected = discover_source_decisions(package=base, pdf_path=pdf_path,
                                         expected_pdf_sha256=expected_pdf_sha256)
    if candidates != expected:
        raise CompositionError("candidate context changed")
    if decisions.get("candidate_context_sha256") != _hash(candidates):
        raise CompositionError("decision candidate pin mismatch")
    review_authority = decisions.get("review_authority")
    if review_authority not in {"agent", "human"}:
        raise CompositionError("review authority must be agent or human")
    reviews = decisions.get("reviews")
    if not isinstance(reviews, list) or not 0 < len(reviews) <= max_reviewed:
        raise CompositionError("review decision cap or inventory invalid")
    by_id = {candidate["id"]: candidate for candidate in candidates["candidates"]}
    resources = deepcopy(base["resources"])
    relations = deepcopy(base["relationships"])
    diagnostics = deepcopy(base.get("diagnostics", []))
    seen: set[str] = set()
    accepted = []
    for review in reviews:
        if not isinstance(review, dict) or review.get("candidate_id") not in by_id:
            raise CompositionError("unknown decision candidate")
        cid = review["candidate_id"]
        if cid in seen:
            raise CompositionError("duplicate decision candidate")
        seen.add(cid)
        candidate = by_id[cid]
        choice = review.get("choice")
        if choice not in {CHOICES[candidate["kind"]], "unresolved"}:
            raise CompositionError("invalid typed decision choice")
        if (not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip()
                or not isinstance(review.get("rationale"), str)
                or len(review["rationale"].strip()) < 12):
            raise CompositionError("reviewer and rationale required")
        accepted.append({"candidate_id": cid, "kind": candidate["kind"],
                         "choice": choice, "reviewer": review["reviewer"],
                         "rationale": review["rationale"]})
        if choice == "unresolved":
            diagnostics.append({"kind": "interpretation_pending",
                                "resource_ids": candidate["resource_ids"],
                                "candidate_id": cid, "reason": "review left source decision unresolved"})
            continue
        page = candidate["physical_page_1_based"]
        if candidate["kind"] == "identity_form":
            rid = f"reviewed-identity-{cid[:20]}"
            if rid in resources:
                raise CompositionError("reviewed identity resource collision")
            proposed = candidate["proposed"]
            resources[rid] = {"id": rid, "kind": "character_identity",
                "name": proposed["name"],
                "text": f"{proposed['name']} is identified in the source as {proposed['form']}.",
                "audience": "GM", "form_state": {"current_form": proposed["form"],
                                                  "role": proposed["role"]},
                "origin": {"type": "source", "source_id": f"sha256:{expected_pdf_sha256}",
                           "locator": f"pdf/page-{page}#reviewed-decision={cid}",
                           "page_index": page - 1,
                           "quote": candidate["evidence"][0]["source_quote"]}}
            relations.append({"id": f"reviewed-relation-{cid[:20]}",
                "source_id": candidate["resource_ids"][0], "target_id": rid,
                "kind": "evidence_for_identity", "reviewed_candidate_id": cid})
        else:
            kind = ("source_outcome_tension" if candidate["kind"] == "outcome_tension"
                    else "source_charge_timing_ambiguity")
            relation_id = f"reviewed-relation-{cid[:20]}"
            relations.append({"id": relation_id,
                "source_id": candidate["resource_ids"][0],
                "target_id": candidate["resource_ids"][1],
                "kind": kind, "status": "unresolved", "reviewed_candidate_id": cid,
                "source_quotes": [item["source_quote"] for item in candidate["evidence"]]})
            diagnostics.append({"kind": "interpretation_pending", "relationship_id": relation_id,
                "resource_ids": candidate["resource_ids"], "candidate_id": cid,
                "reason": "source statements require scoped interpretation"})
    derived = deepcopy(base)
    derived.pop("revision", None)
    derived["package_id"] = package_id
    derived["title"] = f"{base['title']} with reviewed source decisions"
    derived["lineage"] = [{key: base[key] for key in ("package_id", "revision")}]
    derived["resources"] = resources
    derived["relationships"] = relations
    derived["diagnostics"] = diagnostics
    derived["reviewed_source_decisions"] = accepted
    derived["review_authority"] = review_authority
    derived["promotion_state"] = "provisional_pending_independent_review"
    derived["candidate_context_sha256"] = _hash(candidates)
    return output_store.save(derived)


def build_treatment_review_packet(*, expected: dict[str, Any], baseline: dict[str, Any],
                                  treated: dict[str, Any]) -> dict[str, Any]:
    """Open all frozen source cases against a derived package; infer no verdict."""
    base_ref = {key: baseline[key] for key in ("package_id", "revision")}
    if (expected.get("review_package_ref") != base_ref
            or treated.get("lineage") != [base_ref]
            or any(treated["resources"].get(rid) != resource
                   for rid, resource in baseline["resources"].items())):
        raise CompositionError("treatment review base mismatch")
    source_id = f"sha256:{expected['source_pdf_sha256']}"
    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    page_count = max(
        [case["evidence"]["pdf_page_1_based"] for case in expected["cases"]]
        + [resource["origin"].get("page_index", resource["origin"].get("pdf_page_index", -1)) + 1
           for resource in treated["resources"].values()]
    )
    for resource in treated["resources"].values():
        by_page[_resource_page(resource, source_id, page_count)].append(resource)
    packet = deepcopy(expected)
    packet["review_package_ref"] = {key: treated[key] for key in ("package_id", "revision")}
    packet["available_resource_ids"] = sorted(treated["resources"])
    packet["treatment_basis"] = "additive_reviewed_source_decisions"
    for case in packet["cases"]:
        page = case["evidence"]["pdf_page_1_based"]
        resources = by_page[page]
        case["candidate_text_resources"] = [r for r in resources if r["kind"] != "asset_reference"]
        case["candidate_asset_references"] = [r for r in resources if r["kind"] == "asset_reference"]
        case["candidate_resource_ids"] = [r["id"] for r in resources]
        case["review"] = None
    unsigned = {**packet, "cases": [{key: value for key, value in case.items()
                                    if key != "review"} for case in packet["cases"]]}
    unsigned.pop("context_sha256", None)
    packet["context_sha256"] = _hash(unsigned)
    return packet
