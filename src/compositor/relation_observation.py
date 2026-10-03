"""Small deterministic relation-observation baseline over pinned evidence units.

This is a lexical proposal generator, not semantic adjudication or graph admission.
It never merges names, resolves pronouns, or treats quote containment as truth.
"""

from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

from .package import CompositionError

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
_PATTERNS = (
    ("conditional", re.compile(r"^(?:If|Should)\s+(.{3,180}?),\s+(.{3,240})$", re.I)),
    ("self_identity", re.compile(r"(.{2,160}?)\bintroduc(?:es|ed) itself as\s+(.{2,160})", re.I)),
    ("request", re.compile(r"(.{2,120}?)\bwants?\s+(.{2,200})", re.I)),
    ("transfer", re.compile(r"(.{2,120}?)\b(?:sold|gave|gives)\s+(.{2,200})", re.I)),
    ("possession_change", re.compile(r"(.{2,120}?)\b(?:stole|lifted|planted)\s+(.{2,200})", re.I)),
)
_PRONOUNS = {"he", "she", "they", "it", "him", "her", "them", "his", "their", "theirs"}


def _surface(value: str) -> str:
    value = value.strip(" \t\n\r,;:—-\"'“”")
    if " — " in value:
        value = value.rsplit(" — ", 1)[-1]
    if ", " in value:
        value = value.rsplit(", ", 1)[-1]
    return value.strip()


def _endpoint(value: str) -> dict[str, str]:
    clean = _surface(value)
    if not clean or len(clean) > 120:
        return {"state": "unresolved", "reason": "empty_or_long_surface"}
    if clean.lower() in _PRONOUNS or re.match(r"^(?:he|she|they|it|him|her|them)\b", clean, re.I):
        return {"state": "unresolved", "reason": "pronoun_requires_review", "surface": clean}
    return {"state": "surface_only", "surface": clean,
            "surface_id": sha256(clean.casefold().encode("utf-8")).hexdigest()[:16]}


def observe_units(units: list[dict[str, Any]], *, max_units: int = 32,
                  max_sentences_per_unit: int = 24) -> dict[str, Any]:
    """Propose typed phrase relations from exact units, preserving unsupported text."""
    if not 1 <= len(units) <= max_units <= 100 or not 1 <= max_sentences_per_unit <= 100:
        raise CompositionError("observation bounds exceeded")
    seen: set[str] = set()
    observations: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    for unit in units:
        unit_id = unit.get("unit_id")
        page = unit.get("page_index")
        text = unit.get("text")
        if not isinstance(unit_id, str) or not unit_id or unit_id in seen or type(page) is not int or page < 0 or not isinstance(text, str) or not text.strip():
            raise CompositionError("invalid observation source unit")
        seen.add(unit_id)
        sentences = [s.strip() for s in _SENTENCE_BOUNDARY.split(text) if s.strip()]
        if len(sentences) > max_sentences_per_unit:
            raise CompositionError("sentence cap exceeded")
        for number, sentence in enumerate(sentences):
            matched = False
            for kind, pattern in _PATTERNS:
                match = pattern.search(sentence)
                if match is None:
                    continue
                left, right = (_surface(x) for x in match.groups())
                if not left or not right:
                    continue
                observation = {
                    "id": f"{unit_id}:{number}:{kind}", "kind": kind,
                    "source_unit_id": unit_id, "page_index": page,
                    "quote": sentence, "subject": _endpoint(left),
                    "object": _endpoint(right), "support_state": "lexical_candidate_only",
                }
                if kind == "conditional":
                    observation["modality"] = "conditional"
                observations.append(observation)
                matched = True
                break
            if not matched:
                unsupported.append({"source_unit_id": unit_id, "page_index": page,
                                    "sentence_index": number, "reason": "no_supported_pattern"})
    return {"format_version": 1, "units_seen": len(units),
            "sentences_seen": len(observations) + len(unsupported),
            "observations": observations, "unsupported": unsupported}


def probe_paths(result: dict[str, Any], *, max_edges: int = 3,
                max_paths: int = 16) -> dict[str, Any]:
    """Enumerate bounded surface-only paths; unresolved endpoints remain explicit."""
    if not 1 <= max_edges <= 5 or not 1 <= max_paths <= 100:
        raise CompositionError("path bounds exceeded")
    edges = []
    unresolved = []
    for obs in result["observations"]:
        source, target = obs["subject"], obs["object"]
        if source["state"] != "surface_only" or target["state"] != "surface_only":
            unresolved.append(obs["id"])
            continue
        edges.append({"id": obs["id"], "source": source["surface_id"],
                      "target": target["surface_id"], "kind": obs["kind"]})
    paths = []
    frontier = [{"nodes": [edge["source"], edge["target"]], "edges": [edge["id"]]}
                for edge in edges]
    for depth in range(1, max_edges + 1):
        if depth >= 2:
            paths.extend(frontier)
            if len(paths) > max_paths:
                return {"paths": paths[:max_paths], "truncated": True,
                        "bound_edges": len(edges), "unresolved_observations": unresolved}
        if depth == max_edges:
            break
        next_frontier = []
        for path in frontier:
            for edge in edges:
                if edge["source"] == path["nodes"][-1] and edge["target"] not in path["nodes"]:
                    next_frontier.append({"nodes": path["nodes"] + [edge["target"]],
                                          "edges": path["edges"] + [edge["id"]]})
                    if len(next_frontier) > max_paths * 10:
                        raise CompositionError("path expansion cap exceeded")
        frontier = next_frontier
    return {"paths": paths, "truncated": False,
            "bound_edges": len(edges), "unresolved_observations": unresolved}


def canonical_json_hash(value: Any) -> str:
    """Digest a result without depending on whitespace or key order."""
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest()
