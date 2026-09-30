"""Portable, source-linked Composition packages."""

from .package import (
    CompositionError, JsonPackageStore, WorkingDraft, accept_impact, derive,
    edit_resource, effective_content, make_source_package, query, resolve_rule,
    save_derived, select_dependency,
)
from .evidence_adapter import EvidenceDraftResult, load_evidence_draft

__all__ = [
    "CompositionError", "JsonPackageStore", "WorkingDraft", "accept_impact",
    "derive", "edit_resource", "effective_content", "make_source_package",
    "query", "resolve_rule", "save_derived", "select_dependency",
    "EvidenceDraftResult", "load_evidence_draft",
]
