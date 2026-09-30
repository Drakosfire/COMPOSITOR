"""Private, human-readable adjudication packets for frozen one-shot gold.

The packet suggests source-local candidates but never infers a verdict. Reviewers
must inspect source and package evidence and record their own rationale.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import re
from typing import Any

from .package import CompositionError


VERDICTS = {"pass", "material_gap", "critical_failure", "minor_gap", "unresolved"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode()).hexdigest()


def build_review_packet(*, run_id: str, gold: dict[str, Any], package: dict[str, Any],
                        gold_sha256: str, source_sha256: str) -> dict[str, Any]:
    """Suggest page-local evidence while leaving every case unjudged."""
    if not HEX64.fullmatch(gold_sha256) or not HEX64.fullmatch(source_sha256):
        raise CompositionError("review needs exact gold and source SHA-256 pins")
    cases = gold.get("cases")
    if gold.get("status") != "frozen" or not isinstance(cases, list) or len(cases) != gold.get("case_count"):
        raise CompositionError("review needs frozen gold with a complete case inventory")
    if package.get("form") != "source" or not HEX64.fullmatch(str(package.get("revision", ""))):
        raise CompositionError("review needs an immutable source package revision")
    resources = package.get("resources")
    if not isinstance(resources, dict):
        raise CompositionError("package resources unavailable")
    source_id = f"sha256:{source_sha256}"
    for resource in resources.values():
        if resource.get("origin", {}).get("source_id") != source_id:
            raise CompositionError("package resource source identity differs from pinned Markdown")
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise CompositionError("gold case IDs must be unique")
        seen.add(case_id)
        evidence = case.get("evidence") or {}
        pages = [evidence.get("normalized_markdown_page_marker")]
        pages.extend(evidence.get("additional_normalized_markdown_page_markers") or [])
        pages = sorted({page for page in pages if isinstance(page, int)})
        candidates = [resource for resource in resources.values()
                      if resource.get("origin", {}).get("locator") in
                      {f"printed-page:{page}" for page in pages}]
        diagnostics = [issue for issue in package.get("diagnostics", [])
                       if issue.get("page_index") in {page - 2 for page in pages}]
        entries.append({"id": case_id, "category": case.get("category"),
                        "task": case.get("task"), "severity": case.get("severity"),
                        "audience": case.get("audience"),
                        "expectation_origin": case.get("expectation_origin"),
                        "expectation": case.get("expectation"),
                        "acceptable_alternatives": case.get("acceptable_alternatives", []),
                        "forbidden_outcomes": case.get("forbidden_outcomes", []),
                        "rationale": case.get("rationale"), "source_evidence": evidence,
                        "candidate_resources": candidates,
                        "page_diagnostics": diagnostics,
                        "review": None})
    context = {"format_version": 1, "run_id": run_id, "suite": gold.get("suite"),
               "gold_sha256": gold_sha256, "source_sha256": source_sha256,
               "package_ref": {"package_id": package["package_id"],
                               "revision": package["revision"]},
               "global_diagnostics": [issue for issue in package.get("diagnostics", [])
                                      if "page_index" not in issue],
               "available_resource_ids": sorted(resources), "cases": entries}
    context["context_sha256"] = _hash({**context, "cases": [{k: v for k, v in entry.items()
                                                       if k != "review"} for entry in entries]})
    return context


def validate_review_packet(edited: dict[str, Any], *, expected: dict[str, Any],
                           require_complete: bool) -> dict[str, Any]:
    """Reject changed gold/package context and validate explicit judgments."""
    if {k: v for k, v in edited.items() if k != "cases"} != \
            {k: v for k, v in expected.items() if k != "cases"}:
        raise CompositionError("review packet pins or resource index changed")
    edited_cases = edited.get("cases")
    expected_cases = expected["cases"]
    if not isinstance(edited_cases, list) or len(edited_cases) != len(expected_cases):
        raise CompositionError("review case inventory changed")
    summary = {"total": len(expected_cases), "reviewed": 0, "unreviewed": 0,
               "verdicts": Counter(), "by_task": {}, "by_severity": {}}
    available = set(expected["available_resource_ids"])
    for entry, original in zip(edited_cases, expected_cases, strict=True):
        if {k: v for k, v in entry.items() if k != "review"} != \
                {k: v for k, v in original.items() if k != "review"}:
            raise CompositionError(f"review context changed for {original['id']}")
        review = entry.get("review")
        if review is None:
            summary["unreviewed"] += 1
            continue
        if not isinstance(review, dict) or review.get("verdict") not in VERDICTS:
            raise CompositionError(f"invalid verdict for {original['id']}")
        if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
            raise CompositionError(f"reviewer required for {original['id']}")
        if not isinstance(review.get("rationale"), str) or len(review["rationale"].strip()) < 12:
            raise CompositionError(f"source-grounded rationale required for {original['id']}")
        cited = review.get("resource_ids")
        if not isinstance(cited, list) or any(not isinstance(rid, str) or rid not in available
                                               for rid in cited):
            raise CompositionError(f"invalid resource citation for {original['id']}")
        summary["reviewed"] += 1
        summary["verdicts"][review["verdict"]] += 1
        for axis, bucket in (("by_task", original.get("task")),
                             ("by_severity", original.get("severity"))):
            key = str(bucket)
            counts = summary[axis].setdefault(key, Counter())
            counts[review["verdict"]] += 1
    if require_complete and summary["unreviewed"]:
        raise CompositionError("cannot finalize a partial gold adjudication")
    return {**summary, "verdicts": dict(summary["verdicts"]),
            "by_task": {key: dict(value) for key, value in summary["by_task"].items()},
            "by_severity": {key: dict(value) for key, value in summary["by_severity"].items()}}
