"""Portable, source-linked Composition packages."""

from .package import (
    CompositionError, JsonPackageStore, WorkingDraft, accept_impact, derive,
    edit_resource, effective_content, make_source_package, query, resolve_rule,
    save_derived, select_dependency,
)

__all__ = [
    "CompositionError", "JsonPackageStore", "WorkingDraft", "accept_impact",
    "derive", "edit_resource", "effective_content", "make_source_package",
    "query", "resolve_rule", "save_derived", "select_dependency",
]
