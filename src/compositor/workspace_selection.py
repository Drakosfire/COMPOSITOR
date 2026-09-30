"""Ephemeral exact-package selection for scoped Composition reads.

Selection holds no World or provider handle. Durable publication remains an
explicit operation through the owning World boundary.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .package import CompositionError, JsonPackageStore, effective_content, query


def _exact_ref(value: dict[str, Any]) -> dict[str, str]:
    if not isinstance(value, dict) or not isinstance(value.get("package_id"), str):
        raise CompositionError("exact package reference required")
    if not isinstance(value.get("revision"), str):
        raise CompositionError("exact package revision required")
    return {"package_id": value["package_id"], "revision": value["revision"]}


@dataclass
class WorkspaceSelection:
    """One session's active package refs; every read reloads exact revisions."""

    store: JsonPackageStore
    _active: dict[str, dict[str, str]] = field(default_factory=dict)

    def select(self, ref: dict[str, str]) -> dict[str, Any]:
        exact = _exact_ref(ref)
        previous = self._active.get(exact["package_id"])
        if previous is not None and previous != exact:
            raise CompositionError("unload active package revision before selecting another")
        content = effective_content(self.store, exact)
        self._active[exact["package_id"]] = exact
        return {"package_ref": deepcopy(exact), "readiness": deepcopy(content["readiness"]),
                "issues": deepcopy(content["issues"])}

    def unload(self, ref: dict[str, str]) -> None:
        exact = _exact_ref(ref)
        if self._active.get(exact["package_id"]) != exact:
            raise CompositionError("exact active package revision not selected")
        del self._active[exact["package_id"]]

    def active_refs(self) -> list[dict[str, str]]:
        return [deepcopy(self._active[key]) for key in sorted(self._active)]

    def query(self, term: str, *, audience: str,
              package_ids: list[str] | None = None) -> list[dict[str, Any]]:
        selected = sorted(self._active) if package_ids is None else sorted(set(package_ids))
        if not selected or any(package_id not in self._active for package_id in selected):
            raise CompositionError("query scope contains no active package or an inactive package")
        results: list[dict[str, Any]] = []
        for package_id in selected:
            content = effective_content(self.store, self._active[package_id])
            results.extend(query(content, term, audience=audience))
        return results
