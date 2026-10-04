"""Stateless card view over a reviewed lab contribution.

The card does not admit knowledge, publish a World, or own active surface state.
"""

from __future__ import annotations

from typing import Any

from .package import CompositionError
from .scene_contribution import readback_claim, validate_contribution

_LENSES = ("situation", "read_aloud", "do_now", "gm_only", "relevant", "missing_reference")


def project_card(contribution: dict[str, Any], context: dict[str, Any], *,
                 audience: str, active_surface: str) -> dict[str, Any]:
    """Project exact reviewed claims for a caller-selected audience/surface."""
    if audience not in {"GM", "PLAYER"} or not isinstance(active_surface, str) or not active_surface.strip():
        raise CompositionError("audience and active surface required")
    validate_contribution(contribution, context)
    visible = [claim for claim in contribution["claims"] if audience == "GM" or claim["audience"] == "PLAYER"]
    by_id = {c["id"]: c for c in visible}
    lenses = {key: [] for key in _LENSES}
    for claim in visible:
        lenses[claim["lens"]].append({k: claim[k] for k in
            ("id", "kind", "state", "text", "audience") if k in claim} |
            {"reason": claim.get("reason"), "review": claim["review"],
             "evidence": readback_claim(claim, context)})
    choices = []
    for choice in contribution.get("choices", []):
        if choice["action_claim"] not in by_id:
            continue
        choices.append({"id": choice["id"], "mode": "optional",
                        "noncombat": choice["noncombat"],
                        "action_claim": choice["action_claim"],
                        "conditions": [x for x in choice.get("conditions", []) if x in by_id],
                        "consequences": [x for x in choice.get("consequences", []) if x in by_id]})
    return {"format_version": 1, "contribution_id": contribution["id"],
            "source": contribution["source"], "audience": audience,
            "active_surface": active_surface, "lenses": lenses, "choices": choices,
            "knowledge_authority": "reviewed_lab_candidate_only"}


def card_to_source(card: dict[str, Any], claim_id: str,
                   context: dict[str, Any]) -> list[dict[str, Any]]:
    """Read back a displayed claim through exact source/evidence identity."""
    if any(card.get("source", {}).get(k) != context[k] for k in
           ("source_sha256", "manifest_sha256", "package_sha256", "package_id", "package_revision")):
        raise CompositionError("card source revision changed")
    for entries in card.get("lenses", {}).values():
        for claim in entries:
            if claim.get("id") == claim_id:
                return readback_claim(claim, context)
    raise CompositionError("claim absent from selected card")
