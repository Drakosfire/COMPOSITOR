"""Offline, supplied-candidate Adventure graph checks for lab evidence.

This module validates quoted OCR evidence and typed endpoints. It performs no
candidate discovery, model call, owner admission, or World publication.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .package import CompositionError


def read_pinned_units(page_files: dict[int, tuple[Path, str]]) -> dict[str, dict[str, Any]]:
    """Read exact Stage B page files; fail on a changed file or duplicate unit."""
    units: dict[str, dict[str, Any]] = {}
    for page_index, (path, expected_hash) in sorted(page_files.items()):
        raw = Path(path).read_bytes()
        if sha256(raw).hexdigest() != expected_hash:
            raise CompositionError(f"Stage B page {page_index} revision mismatch")
        page = json.loads(raw)
        if page.get("gates_passed") is not True:
            raise CompositionError(f"Stage B page {page_index} failed gates")
        for unit in page.get("units", []):
            unit_id = unit.get("unit_id")
            if not isinstance(unit_id, str) or unit_id in units:
                raise CompositionError("missing or duplicate Stage B unit id")
            units[unit_id] = {"page_index": page_index, "text": unit.get("text", "")}
    return units


def validate_candidate_graph(graph: dict[str, Any], units: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Check every supplied node/edge and its native evidence before path use."""
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise CompositionError("candidate nodes and edges required")
    node_ids = [n.get("id") for n in nodes if isinstance(n, dict)]
    if len(node_ids) != len(nodes) or len(set(node_ids)) != len(nodes) or any(
            not isinstance(n, str) or not n for n in node_ids):
        raise CompositionError("invalid or duplicate candidate node")
    edge_ids: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            raise CompositionError("candidate edge has unavailable endpoint")
        edge_id = edge.get("id")
        if not isinstance(edge_id, str) or not edge_id or edge_id in edge_ids:
            raise CompositionError("invalid or duplicate candidate edge")
        edge_ids.add(edge_id)
        if not isinstance(edge.get("kind"), str) or not edge["kind"]:
            raise CompositionError("candidate edge needs a kind")
        evidence = edge.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise CompositionError("relation-native evidence required")
        pages: set[int] = set()
        for citation in evidence:
            if not isinstance(citation, dict):
                raise CompositionError("invalid evidence citation")
            unit = units.get(citation.get("unit_id"))
            quote = citation.get("quote")
            if unit is None or not isinstance(quote, str) or not quote or quote not in unit["text"]:
                raise CompositionError("edge quote absent from pinned Stage B unit")
            if citation.get("page_index") != unit["page_index"]:
                raise CompositionError("edge evidence page mismatch")
            pages.add(unit["page_index"])
        if edge["kind"] == "same_person":
            if len(pages) < 2 or edge.get("reviewed") is not True:
                raise CompositionError("cross-page identity needs two pages and review")
        if "attribution" in edge and (not isinstance(edge["attribution"], str) or
                                      not edge["attribution"].strip()):
            raise CompositionError("edge attribution must name its speaker or source")
    return {"node_count": len(nodes), "edge_count": len(edges), "evidence_pages": sorted({
        citation["page_index"] for edge in edges for citation in edge["evidence"]})}


def probe_path(graph: dict[str, Any], start: str, steps: list[dict[str, str]], *, max_paths: int = 8) -> list[dict[str, Any]]:
    """Find bounded typed paths through validated candidate edges."""
    if not 1 <= len(steps) <= 3 or not 1 <= max_paths <= 32:
        raise CompositionError("path bounds exceeded")
    node_ids = {n["id"] for n in graph["nodes"]}
    if start not in node_ids:
        raise CompositionError("path start absent from candidates")
    paths = [{"nodes": [start], "edges": []}]
    for step in steps:
        kind = step.get("kind")
        direction = step.get("direction", "forward")
        if direction not in {"forward", "reverse"} or not isinstance(kind, str) or not kind:
            raise CompositionError("invalid path step")
        next_paths = []
        for path in paths:
            here = path["nodes"][-1]
            for edge in graph["edges"]:
                if edge["kind"] != kind:
                    continue
                source = edge["source"] if direction == "forward" else edge["target"]
                target = edge["target"] if direction == "forward" else edge["source"]
                if source == here and target not in path["nodes"]:
                    next_paths.append({"nodes": path["nodes"] + [target], "edges": path["edges"] + [edge["id"]]})
                    if len(next_paths) > max_paths:
                        raise CompositionError("path result cap exceeded")
        paths = next_paths
    return paths


def evaluate_probe(graph: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    """Run a question plan without reading scorer gold."""
    paths = probe_path(graph, probe["start"], probe["steps"], max_paths=probe.get("max_paths", 8))
    return {"id": probe["id"], "paths": paths, "status": "paths_found" if paths else "no_path"}


def attribute_failure(result: dict[str, Any], expected_end: str, *, source_present: bool,
                      expected_node_present: bool, expected_edges_present: bool) -> str:
    """Classify a scored miss after the immutable first result exists."""
    if any(path["nodes"][-1] == expected_end for path in result["paths"]):
        return "pass"
    if not source_present:
        return "absent_source"
    if not expected_node_present:
        return "absent_candidate"
    if not expected_edges_present:
        return "wrong_identity_or_endpoint"
    return "failed_path_selection"
