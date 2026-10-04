"""Reviewable, source-linked scene contribution for an offline Composition lab.

All identifiers here are lab-local candidates. DungeonMind owns any later durable
space, source, evidence, contribution and graph identities.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .package import CompositionError

_HEX = re.compile(r"^[0-9a-f]{64}$")
_STATES = {"source_supported", "proposed_connective", "unresolved"}
_LENSES = {"situation", "read_aloud", "do_now", "gm_only", "relevant", "missing_reference"}
_KINDS = {"scene", "actor", "goal", "location", "condition", "action", "consequence",
          "mechanic", "asset", "reference", "read_aloud", "situation"}


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise CompositionError(f"{label} needs an exact SHA-256")
    return value


def load_pinned_context(*, source_path: Path, source_sha256: str,
                        manifest_path: Path, manifest_sha256: str,
                        page_files: dict[int, tuple[Path, str]],
                        package_path: Path, package_sha256: str,
                        package_id: str, package_revision: str) -> dict[str, Any]:
    """Hash-check exact source/owner artifacts, then index Stage B units."""
    for path, expected in ((source_path, source_sha256), (manifest_path, manifest_sha256),
                           (package_path, package_sha256)):
        if sha256(Path(path).read_bytes()).hexdigest() != _digest(expected, "input"):
            raise CompositionError("pinned source or manifest changed")
    _digest(package_revision, "package revision")
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    package = json.loads(Path(package_path).read_text(encoding="utf-8"))
    if manifest.get("source_pdf_sha256") != source_sha256:
        raise CompositionError("manifest source identity mismatch")
    if package.get("package_id") != package_id or package.get("revision") != package_revision:
        raise CompositionError("package identity mismatch")
    manifest_pages = {p["page_index"]: p for p in manifest.get("pages", [])}
    units: dict[str, dict[str, Any]] = {}
    for page, (path, expected) in sorted(page_files.items()):
        if type(page) is not int or page < 0 or sha256(Path(path).read_bytes()).hexdigest() != _digest(expected, "page"):
            raise CompositionError("pinned Stage B page changed")
        if manifest_pages.get(page, {}).get("artifact_sha256", {}).get("stageB.evidence_units.json") != expected:
            raise CompositionError("Stage B page is not pinned by manifest")
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("gates_passed") is not True:
            raise CompositionError("Stage B gate failed")
        for unit in data.get("units", []):
            uid, text = unit.get("unit_id"), unit.get("text")
            if not isinstance(uid, str) or not uid or uid in units or not isinstance(text, str):
                raise CompositionError("invalid or duplicate evidence unit")
            units[uid] = {"page_index": page, "text": text}
    if not isinstance(package_id, str) or not package_id:
        raise CompositionError("package id required")
    return {"source_sha256": source_sha256, "manifest_sha256": manifest_sha256,
            "package_sha256": package_sha256,
            "package_id": package_id, "package_revision": package_revision, "units": units}


def _citations(value: Any, context: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise CompositionError("source-supported claim needs evidence")
    checked = []
    for citation in value:
        if not isinstance(citation, dict):
            raise CompositionError("invalid evidence citation")
        unit = context["units"].get(citation.get("unit_id"))
        quote = citation.get("quote")
        if (unit is None or citation.get("page_index") != unit["page_index"] or
                not isinstance(quote, str) or not quote or quote not in unit["text"]):
            raise CompositionError("citation does not reopen exact evidence")
        checked.append({"unit_id": citation["unit_id"], "page_index": citation["page_index"],
                        "quote": quote})
    return checked


def validate_contribution(contribution: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Check authority labels, review decisions, evidence and local references."""
    if not isinstance(contribution, dict) or not isinstance(contribution.get("id"), str) or not contribution["id"]:
        raise CompositionError("scene contribution id required")
    source = contribution.get("source")
    if not isinstance(source, dict) or any(source.get(k) != context[k] for k in
                                            ("source_sha256", "manifest_sha256", "package_sha256", "package_id", "package_revision")):
        raise CompositionError("contribution source identity mismatch")
    claims = contribution.get("claims")
    if not isinstance(claims, list) or not claims:
        raise CompositionError("scene claims required")
    by_id: dict[str, dict[str, Any]] = {}
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("id"), str) or not claim["id"] or claim["id"] in by_id:
            raise CompositionError("invalid or duplicate claim id")
        if claim.get("lens") not in _LENSES or claim.get("kind") not in _KINDS or claim.get("state") not in _STATES:
            raise CompositionError("invalid lens, kind or authority state")
        if claim.get("audience") not in {"GM", "PLAYER"}:
            raise CompositionError("claim audience required")
        review = claim.get("review")
        if (not isinstance(review, dict) or not isinstance(review.get("reviewer"), str) or
                not review["reviewer"] or not isinstance(review.get("rationale"), str) or
                not review["rationale"]):
            raise CompositionError("attributed review decision required")
        state = claim["state"]
        if state == "source_supported":
            if review.get("decision") != "accepted" or not isinstance(claim.get("text"), str) or not claim["text"].strip():
                raise CompositionError("source claim needs accepted review and text")
            _citations(claim.get("evidence"), context)
            if claim["lens"] == "read_aloud" and (claim["audience"] != "PLAYER" or
                    claim.get("disclosure") != "reviewed_player_safe"):
                raise CompositionError("read-aloud needs deliberate player-safe review")
        elif state == "proposed_connective":
            if (review.get("decision") != "proposed" or not isinstance(claim.get("text"), str) or
                    not claim["text"].strip() or claim.get("evidence")):
                raise CompositionError("connective must remain attributed proposal without source citation")
            if claim["lens"] == "read_aloud":
                raise CompositionError("proposed prose cannot be source read-aloud")
        else:
            if (review.get("decision") != "unresolved" or not isinstance(claim.get("reason"), str) or
                    not claim["reason"] or claim.get("evidence")):
                raise CompositionError("unresolved claim needs reason, not claimed support")
        by_id[claim["id"]] = claim
    choices = contribution.get("choices", [])
    if not isinstance(choices, list):
        raise CompositionError("choices must be a list")
    seen_choices = set()
    for choice in choices:
        if not isinstance(choice, dict) or not isinstance(choice.get("id"), str) or choice["id"] in seen_choices:
            raise CompositionError("invalid or duplicate choice")
        seen_choices.add(choice["id"])
        action = by_id.get(choice.get("action_claim"))
        if action is None or action["kind"] != "action" or action["state"] == "unresolved":
            raise CompositionError("choice needs available action claim")
        if choice.get("mode") != "optional" or type(choice.get("noncombat")) is not bool:
            raise CompositionError("choice must remain optional with explicit noncombat state")
        for key, expected_kind in (("conditions", "condition"), ("consequences", "consequence")):
            refs = choice.get(key, [])
            if not isinstance(refs, list) or any(x not in by_id or by_id[x]["kind"] != expected_kind for x in refs):
                raise CompositionError("choice has invalid condition or consequence ref")
    return {"claim_count": len(by_id), "choice_count": len(choices),
            "unresolved_count": sum(x["state"] == "unresolved" for x in claims)}


def readback_claim(claim: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    """Reopen each cited unit exactly; absent support fails rather than falls back."""
    if claim.get("state") != "source_supported":
        return []
    return _citations(claim.get("evidence"), context)
