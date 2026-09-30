"""Bounded lexical candidates from caller-selected Composition revisions.

The caller owns query interpretation, active refs, permissions, and final model
context. This function keeps no state and performs no inference.
"""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Literal

from .package import CompositionError, JsonPackageStore, _ref, effective_content


MAX_REFS = 8
MAX_HITS = 50
MAX_BYTES = 65536
MAX_QUERY_CHARS = 200


def _size(value: dict[str, Any]) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8"))


def _rank(name: str, body: str, needle: str) -> tuple[int, int] | None:
    name_folded = name.casefold()
    body_folded = body.casefold()
    if name_folded == needle:
        return 3, name_folded.count(needle) + body_folded.count(needle)
    if needle in name_folded:
        return 2, name_folded.count(needle) + body_folded.count(needle)
    if needle in body_folded:
        return 1, body_folded.count(needle)
    return None


def retrieve_candidates(store: JsonPackageStore, refs: list[dict[str, str]],
                        query: str, *, audience: Literal["GM", "PLAYER"],
                        max_hits: int, max_bytes: int) -> dict[str, Any]:
    """Return ranked exact-ref candidates within both caller-supplied hard caps.

    Rank is exact resource name, name substring, then text substring; within a
    class, more occurrences rank first. Exact refs and resource IDs break ties.
    A byte cap omits whole resources rather than altering source text.
    """
    if not isinstance(refs, list) or len(refs) > MAX_REFS:
        raise CompositionError("selected refs must be a list of at most eight")
    if audience not in {"GM", "PLAYER"}:
        raise CompositionError("audience must be GM or PLAYER")
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARS:
        raise CompositionError("lexical query must be 1–200 characters")
    if type(max_hits) is not int or not 1 <= max_hits <= MAX_HITS:
        raise CompositionError("hit limit must be 1–50")
    if type(max_bytes) is not int or not 1024 <= max_bytes <= MAX_BYTES:
        raise CompositionError("byte limit must be 1024–65536")

    selected: dict[str, dict[str, str]] = {}
    for value in refs:
        exact = _ref(value)
        if exact["package_id"] in selected:
            raise CompositionError("duplicate package identity in selected refs")
        selected[exact["package_id"]] = exact

    needle = query.strip().casefold()
    candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    packages: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for package_id in sorted(selected):
        exact = selected[package_id]
        try:
            content = effective_content(store, exact)
        except CompositionError as exc:
            if not str(exc).startswith("missing package revision"):
                raise
            packages.append({"ref": exact, "state": "missing", "readiness": None})
            diagnostics.append({"kind": "missing_revision", "ref": exact})
            continue
        packages.append({"ref": exact, "state": "available",
                         "readiness": content["readiness"]})
        for resource_id, resource in content["resources"].items():
            # Filter before matching, scoring, counting, or applying limits.
            if audience == "PLAYER" and resource["audience"] != "PLAYER":
                continue
            rank = _rank(resource["name"], resource["text"], needle)
            if rank is None:
                continue
            hit = {
                "resource": deepcopy(resource),
                "resource_ref": {**exact, "resource_id": resource_id},
                "match": {"class": {3: "name_exact", 2: "name_contains",
                                     1: "text_contains"}[rank[0]],
                          "occurrences": rank[1]},
            }
            sort_key = (-rank[0], -rank[1], package_id, exact["revision"],
                        resource_id)
            candidates.append((sort_key, hit))
    candidates.sort(key=lambda item: item[0])

    result: dict[str, Any] = {
        "hits": [], "packages": packages, "diagnostics": diagnostics,
        "limits": {"max_hits": max_hits, "max_bytes": max_bytes},
        "truncation": {"omitted_hits": len(candidates),
                       "hit_cap_reached": False, "byte_cap_reached": False},
    }
    if _size(result) > max_bytes:
        raise CompositionError("response metadata exceeds byte limit")
    for _, hit in candidates:
        if len(result["hits"]) >= max_hits:
            result["truncation"]["hit_cap_reached"] = True
            break
        proposed = deepcopy(result)
        proposed["hits"].append(hit)
        proposed["truncation"]["omitted_hits"] -= 1
        if _size(proposed) > max_bytes:
            result["truncation"]["byte_cap_reached"] = True
            break
        result = proposed
    if result["truncation"]["omitted_hits"] == 0:
        result["truncation"]["hit_cap_reached"] = False
        result["truncation"]["byte_cap_reached"] = False
    return result
