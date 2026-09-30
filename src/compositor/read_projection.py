"""Stateless, audience-scoped reads over caller-selected Composition revisions.

The caller owns the active set. This module neither stores selection nor changes a
World; every call materializes only the exact revisions supplied for that read.
"""

from __future__ import annotations

from typing import Any, Literal

from .package import CompositionError, JsonPackageStore, _ref, effective_content, query


def project_query(store: JsonPackageStore, refs: list[dict[str, str]], term: str, *,
                  audience: Literal["GM", "PLAYER"]) -> dict[str, Any]:
    """Return namespaced hits, readiness, and missing exact-revision diagnostics.

    Package diagnostics can mention GM-only resources, so they are deliberately
    absent from this audience-facing projection. Readiness is aggregate only.
    """
    if not isinstance(refs, list):
        raise CompositionError("selected package refs must be a list")
    if audience not in {"GM", "PLAYER"}:
        raise CompositionError("audience must be GM or PLAYER")
    if not isinstance(term, str) or not term.strip():
        raise CompositionError("query text required")

    selected: dict[str, dict[str, str]] = {}
    for value in refs:
        exact = _ref(value)
        if exact["package_id"] in selected:
            raise CompositionError("duplicate package identity in selected refs")
        selected[exact["package_id"]] = exact

    hits: list[dict[str, Any]] = []
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
        for hit in query(content, term, audience=audience):
            hits.append({**hit, "resource_ref": {**exact,
                                                 "resource_id": hit["resource"]["id"]}})
    return {"hits": hits, "packages": packages, "diagnostics": diagnostics}
