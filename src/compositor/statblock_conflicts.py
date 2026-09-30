"""Detect printed ability modifier conflicts without changing source values.

The PDF word geometry is the source check. A parsed table cell is trusted only
when all six ability cells match one physical row on the pinned PDF page.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any

from .package import CompositionError, JsonPackageStore
from .reviewed_source_decisions import build_treatment_review_packet


RECIPE = "statblock-ability-conflicts-v1"
ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
CELL = re.compile(r"^(?P<score>\d{1,2})\((?P<modifier>[+-]\d{1,2})\)$")


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode()).hexdigest()


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value).replace("−", "-")


class _Table(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.spans = False
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.rows.append([])
        elif tag in {"td", "th"}:
            if any(key in {"rowspan", "colspan"} and value != "1" for key, value in attrs):
                self.spans = True
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None:
            if not self.rows:
                raise CompositionError("table cell outside row")
            self.rows[-1].append("".join(self._cell).strip())
            self._cell = None


def _pdf_rows(page: Any) -> list[dict[str, Any]]:
    """Recover six physical ability columns from PDF word positions."""
    words = page.get_text("words")
    found = []
    for first in (word for word in words if word[4] == "STR"):
        same_line = sorted((word for word in words if abs(word[1] - first[1]) <= 2),
                           key=lambda word: word[0])
        start = next((i for i, word in enumerate(same_line) if word == first), None)
        if start is None:
            continue
        headers = same_line[start:start + 6]
        if tuple(word[4] for word in headers) != ABILITIES:
            continue
        centers = [(word[0] + word[2]) / 2 for word in headers]
        if centers != sorted(centers) or len(set(centers)) != 6:
            continue
        edges = [headers[0][0] - 15]
        edges.extend((centers[i] + centers[i + 1]) / 2 for i in range(5))
        edges.append(headers[-1][2] + 15)
        header_y = sum(word[1] for word in headers) / 6
        value_words = [word for word in words
                       if header_y + 5 <= word[1] <= header_y + 19]
        cells = []
        boxes = []
        for column in range(6):
            picked = sorted((word for word in value_words
                             if edges[column] <= (word[0] + word[2]) / 2 < edges[column + 1]),
                            key=lambda word: word[0])
            cells.append(_compact("".join(word[4] for word in picked)))
            boxes.append([round(min((word[0] for word in picked), default=0), 2),
                          round(min((word[1] for word in picked), default=0), 2),
                          round(max((word[2] for word in picked), default=0), 2),
                          round(max((word[3] for word in picked), default=0), 2)])
        found.append({"cells": cells, "cell_boxes": boxes})
    return found


def scan_statblock_conflicts(*, package: dict[str, Any], pdf_path: Path,
                             expected_pdf_sha256: str) -> dict[str, Any]:
    """Scan all evidence tables without gold and reject unsupported rows visibly."""
    if sha256(Path(pdf_path).read_bytes()).hexdigest() != expected_pdf_sha256:
        raise CompositionError("source PDF revision mismatch")
    try:
        import fitz
    except ImportError as exc:
        raise CompositionError("PyMuPDF required for physical cell verification") from exc
    with fitz.open(pdf_path) as document:
        physical = [_pdf_rows(page) for page in document]
    source_id = f"sha256:{expected_pdf_sha256}"
    candidates = []
    rejections = []
    consistent = []
    scanned = 0
    for resource in sorted(package["resources"].values(), key=lambda value: value["id"]):
        if resource["kind"] != "evidence_table":
            continue
        scanned += 1
        rid = resource["id"]
        origin = resource.get("origin") or {}
        page_index = origin.get("page_index", origin.get("pdf_page_index"))
        if (origin.get("type") != "source" or origin.get("source_id") != source_id
                or not isinstance(page_index, int) or isinstance(page_index, bool)
                or not 0 <= page_index < len(physical)):
            raise CompositionError("table source identity or physical page invalid")
        parsed = _Table()
        parsed.feed(resource["text"])
        if not parsed.rows or tuple(_compact(cell) for cell in parsed.rows[0]) != ABILITIES:
            rejections.append({"resource_id": rid, "reason": "non_statblock_table"})
            continue
        if (parsed.spans or len(parsed.rows) != 2 or len(parsed.rows[1]) != 6
                or any(CELL.fullmatch(_compact(cell)) is None for cell in parsed.rows[1])):
            rejections.append({"resource_id": rid, "reason": "ambiguous_ability_table"})
            continue
        cells = [_compact(cell) for cell in parsed.rows[1]]
        matches = [row for row in physical[page_index] if row["cells"] == cells]
        if len(matches) != 1:
            rejections.append({"resource_id": rid, "reason": "pdf_cell_mismatch_or_ambiguous",
                               "physical_page_1_based": page_index + 1})
            continue
        row = matches[0]
        mismatches = []
        for index, cell in enumerate(cells):
            match = CELL.fullmatch(cell)
            assert match is not None
            score = int(match.group("score"))
            printed = int(match.group("modifier"))
            expected = (score - 10) // 2
            if printed != expected:
                mismatches.append({"ability": ABILITIES[index], "printed_score": score,
                                   "printed_modifier": printed, "calculated_modifier": expected,
                                   "pdf_cell": cell, "pdf_cell_bbox": row["cell_boxes"][index]})
        if not mismatches:
            consistent.append(rid)
            continue
        body = {"kind": "printed_ability_modifier_inconsistency",
                "resource_id": rid, "physical_page_1_based": page_index + 1,
                "printed_cells": cells, "mismatches": mismatches}
        candidates.append({"id": _hash({"recipe": RECIPE, **body}), **body})
    return {"format_version": 1, "recipe": RECIPE,
            "source_pdf_sha256": expected_pdf_sha256,
            "package_ref": {key: package[key] for key in ("package_id", "revision")},
            "scanned_tables": scanned, "consistent_resource_ids": consistent,
            "rejections": rejections, "candidates": candidates}


def apply_statblock_conflict_reviews(*, base: dict[str, Any], scan: dict[str, Any],
                                     decisions: dict[str, Any], pdf_path: Path,
                                     expected_pdf_sha256: str, output_store: JsonPackageStore,
                                     package_id: str) -> dict[str, Any]:
    """Save an additive provisional revision after attributed source review."""
    if scan != scan_statblock_conflicts(package=base, pdf_path=pdf_path,
                                       expected_pdf_sha256=expected_pdf_sha256):
        raise CompositionError("statblock scan context changed")
    if decisions.get("scan_context_sha256") != _hash(scan):
        raise CompositionError("statblock decision context mismatch")
    authority = decisions.get("review_authority")
    if authority not in {"agent", "human"}:
        raise CompositionError("review authority must be agent or human")
    reviews = decisions.get("reviews")
    if not isinstance(reviews, list) or len(reviews) != len(scan["candidates"]):
        raise CompositionError("every conflict candidate needs an explicit review")
    by_id = {item["id"]: item for item in scan["candidates"]}
    seen = set()
    diagnostics = deepcopy(base.get("diagnostics", []))
    accepted = []
    for review in reviews:
        if not isinstance(review, dict) or review.get("candidate_id") not in by_id:
            raise CompositionError("unknown statblock conflict candidate")
        cid = review["candidate_id"]
        if cid in seen:
            raise CompositionError("duplicate statblock conflict review")
        seen.add(cid)
        choice = review.get("choice")
        if choice not in {"record_source_inconsistency", "unresolved"}:
            raise CompositionError("invalid statblock conflict choice")
        if (not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip()
                or not isinstance(review.get("rationale"), str)
                or len(review["rationale"].strip()) < 12):
            raise CompositionError("reviewer and rationale required")
        candidate = by_id[cid]
        accepted.append({"candidate_id": cid, "choice": choice,
                         "reviewer": review["reviewer"], "rationale": review["rationale"]})
        if choice == "record_source_inconsistency":
            diagnostics.append({"kind": "interpretation_pending",
                "detail_kind": "statblock_modifier_inconsistency",
                "resource_id": candidate["resource_id"], "candidate_id": cid,
                "physical_page_1_based": candidate["physical_page_1_based"],
                "mismatches": candidate["mismatches"],
                "reason": "printed score and modifier disagree; source values retained"})
        else:
            diagnostics.append({"kind": "interpretation_pending",
                "resource_id": candidate["resource_id"], "candidate_id": cid,
                "reason": "review left printed modifier conflict unresolved"})
    derived = deepcopy(base)
    derived.pop("revision", None)
    derived["package_id"] = package_id
    derived["title"] = f"{base['title']} with reviewed statblock conflicts"
    derived["lineage"] = [{key: base[key] for key in ("package_id", "revision")}]
    derived["diagnostics"] = diagnostics
    derived["reviewed_statblock_conflicts"] = accepted
    derived["scan_context_sha256"] = _hash(scan)
    derived["review_authority"] = authority
    derived["promotion_state"] = "provisional_pending_independent_review"
    return output_store.save(derived)


def build_statblock_treatment_packet(*, expected: dict[str, Any],
                                     baseline: dict[str, Any],
                                     treated: dict[str, Any]) -> dict[str, Any]:
    """Open every frozen source case against this additive treatment, unjudged."""
    if (treated.get("promotion_state") != "provisional_pending_independent_review"
            or "reviewed_statblock_conflicts" not in treated):
        raise CompositionError("statblock treatment package is not provisional review output")
    packet = build_treatment_review_packet(expected=expected, baseline=baseline,
                                           treated=treated)
    packet["treatment_basis"] = "additive_reviewed_statblock_conflicts"
    unsigned = {**packet, "cases": [{key: value for key, value in case.items()
                                    if key != "review"} for case in packet["cases"]]}
    unsigned.pop("context_sha256", None)
    packet["context_sha256"] = _hash(unsigned)
    return packet
