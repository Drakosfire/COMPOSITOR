"""Read pinned RulesIngestion Stage A/B artifacts into a source Composition.

This adapter does no extraction or inference. Recovery routes remain explicit in
the manifest, and the Stage B unit stays the source anchor for every resource.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .package import CompositionError, JsonPackageStore, make_source_package


@dataclass
class EvidenceDraftResult:
    package: dict[str, Any]
    report: dict[str, Any]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_path(project_root: Path, name: str) -> Path:
    path = Path(name)
    return path if path.is_absolute() else project_root / path


def _check_source(project_root: Path, path_name: str, expected_sha256: str,
                  diagnostics: list[dict[str, Any]]) -> None:
    path = _source_path(project_root, path_name)
    if not path.is_file():
        diagnostics.append({"kind": "missing_source", "path": path_name})
        return
    actual = sha256(path.read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise CompositionError(f"source revision mismatch for {path_name}")


def load_evidence_draft(store: JsonPackageStore, bundle_dir: Path, *,
                        project_root: Path, package_id: str, title: str,
                        expected_rules_ingestion_ref: str,
                        expected_manifest_sha256: str) -> EvidenceDraftResult:
    """Assemble source units while preserving recovery and failure provenance."""
    bundle_dir = Path(bundle_dir)
    project_root = Path(project_root)
    manifest_path = bundle_dir / "manifest.json"
    if sha256(manifest_path.read_bytes()).hexdigest() != expected_manifest_sha256:
        raise CompositionError("evidence manifest revision mismatch")
    manifest = _read_json(manifest_path)
    if manifest.get("format_version") != 1 or manifest.get("route") not in {"pdf_text", "supplied_markdown"}:
        raise CompositionError("unsupported evidence bundle")
    if manifest.get("rules_ingestion_ref") != expected_rules_ingestion_ref:
        raise CompositionError("RulesIngestion contract revision mismatch")
    route = manifest["route"]
    direct_source_sha256 = (manifest["supplied_markdown_sha256"]
                            if route == "supplied_markdown" else manifest["source_pdf_sha256"])
    diagnostics: list[dict[str, Any]] = []
    _check_source(project_root, manifest["source_pdf"], manifest["source_pdf_sha256"], diagnostics)
    if route == "supplied_markdown":
        _check_source(project_root, manifest["supplied_markdown"],
                      manifest["supplied_markdown_sha256"], diagnostics)
    for asset in manifest.get("expected_assets", []):
        if not _source_path(project_root, asset).is_file():
            diagnostics.append({"kind": "missing_asset", "path": asset})

    pages = {entry["page_index"]: entry for entry in manifest["pages"]}
    resources: dict[str, dict[str, Any]] = {}
    gate_report: list[dict[str, Any]] = []
    for page_index in manifest["expected_page_indices"]:
        page = pages.get(page_index)
        if page is None:
            diagnostics.append({"kind": "missing_page", "page_index": page_index})
            continue
        page_dir = bundle_dir / page["artifact_dir"]
        names = ("stageA.surface.md", "stageA.surface.ast.json", "stageA.gate_diagnostics.json",
                 "stageB.evidence_units.json")
        missing = [name for name in names if not (page_dir / name).is_file()]
        if missing:
            diagnostics.append({"kind": "missing_artifact", "page_index": page_index,
                                "files": missing})
            continue
        for name in names:
            if sha256((page_dir / name).read_bytes()).hexdigest() != page["artifact_sha256"][name]:
                raise CompositionError(f"evidence artifact revision mismatch: {page_index}/{name}")
        surface = (page_dir / names[0]).read_text(encoding="utf-8")
        ast = _read_json(page_dir / names[1])
        stage_a_gates = _read_json(page_dir / names[2])
        stage_b = _read_json(page_dir / names[3])
        if ast.get("page_fingerprint") != page["page_fingerprint"]:
            diagnostics.append({"kind": "evidence_mismatch", "page_index": page_index,
                                "reason": "Stage A fingerprint differs from manifest"})
            continue
        for stage, gates in (("A", stage_a_gates), ("B", stage_b["gate_diagnostics"])):
            for gate in gates:
                item = {"page_index": page_index, "stage": stage, **deepcopy(gate)}
                gate_report.append(item)
                if not gate["passed"]:
                    diagnostics.append({"kind": "gate_failure", "page_index": page_index,
                                        "stage": stage, "gate_name": gate["gate_name"]})
        lines = surface.splitlines()
        for offset, unit in enumerate(stage_b["units"]):
            uid = unit["unit_id"]
            start, end = unit["source_line_start"], unit["source_line_end"]
            if (unit["page_fingerprint"] != page["page_fingerprint"]
                    or not (0 <= start < end <= len(lines)) or uid in resources):
                diagnostics.append({"kind": "evidence_mismatch", "page_index": page_index,
                                    "unit_id": uid, "reason": "fingerprint, line span, or unit identity"})
                continue
            heading = " / ".join(unit["structural_path"]) or f"Page {page_index + 1}"
            origin = {
                "type": "source", "source_id": f"sha256:{direct_source_sha256}",
                "locator": f"{route}/{page['artifact_dir']}/stageB.evidence_units.json#/units/{offset}",
                "page_index": page_index, "source_line_start": start,
                "source_line_end": end, "page_fingerprint": page["page_fingerprint"],
                "content_version": unit.get("content_version", ""),
            }
            if route == "supplied_markdown":
                origin["associated_pdf_sha256"] = manifest["source_pdf_sha256"]
            resources[uid] = {
                "id": uid, "kind": f"evidence_{unit['unit_type']}", "name": heading,
                "text": unit["text"], "audience": "GM",
                "origin": origin,
            }
    package = make_source_package(store, package_id=package_id, title=title,
                                  resources=resources, diagnostics=diagnostics)
    return EvidenceDraftResult(package=package, report={
        "route": route, "recovery_method": manifest["recovery_method"],
        "rules_ingestion_ref": manifest["rules_ingestion_ref"],
        "source_pdf_sha256": manifest["source_pdf_sha256"],
        "supplied_markdown_sha256": manifest.get("supplied_markdown_sha256"),
        "direct_source_sha256": direct_source_sha256,
        "unit_count": len(resources), "gate_report": gate_report,
        "diagnostics": deepcopy(diagnostics), "provider_calls": manifest["provider_calls"],
    })
