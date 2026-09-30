"""Verify private source assets and project reference-only package resources."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .package import CompositionError, JsonPackageStore


_SHA = re.compile(r"^[0-9a-f]{64}$")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _private_file(private_root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise CompositionError("asset needs a private relative path")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or any(part in {"", ".", ".."} for part in parts.parts):
        raise CompositionError("asset path escapes private root")
    path = (private_root / relative).resolve()
    if not path.is_relative_to(private_root.resolve()):
        raise CompositionError("asset path escapes private root")
    if not path.is_file():
        raise CompositionError("private asset bytes missing")
    return path


def project_asset_references(*, base_store: JsonPackageStore, base_ref: dict[str, str],
                             output_store: JsonPackageStore, package_id: str,
                             manifest_path: Path, expected_manifest_sha256: str,
                             private_root: Path) -> dict[str, Any]:
    """Materialize checked asset references without copying image bytes into JSON."""
    manifest_path = Path(manifest_path)
    if not _SHA.fullmatch(expected_manifest_sha256) or _digest(manifest_path) != expected_manifest_sha256:
        raise CompositionError("asset manifest revision mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format_version") != 1 or manifest.get("status") != "reference_only":
        raise CompositionError("unsupported asset manifest")
    base = base_store.load(base_ref)
    exact_base = {"package_id": base["package_id"], "revision": base["revision"]}
    if manifest.get("base_package_ref") != exact_base or base["form"] != "source":
        raise CompositionError("asset manifest base package mismatch")
    source = manifest.get("illustrated_pdf") or {}
    pdf_path = Path(source.get("path", ""))
    pdf_sha = source.get("sha256", "")
    if not pdf_path.is_file() or not _SHA.fullmatch(pdf_sha) or _digest(pdf_path) != pdf_sha:
        raise CompositionError("illustrated PDF revision mismatch")
    try:
        import fitz
    except ImportError as exc:
        raise CompositionError("PyMuPDF required to verify PDF asset provenance") from exc
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise CompositionError("asset manifest needs reviewed references")
    resources = deepcopy(base["resources"])
    seen: set[str] = set()
    with fitz.open(pdf_path) as document:
        for asset in assets:
            if not isinstance(asset, dict) or asset.get("status") != "reference_only":
                raise CompositionError("asset cannot claim verified publication")
            resource_id = asset.get("resource_id")
            if not isinstance(resource_id, str) or not resource_id or resource_id in resources or resource_id in seen:
                raise CompositionError("asset resource identity missing or duplicated")
            seen.add(resource_id)
            printed_page, page_index, xref = (asset.get(key) for key in
                                               ("printed_page", "pdf_page_index", "xref"))
            if (not isinstance(printed_page, int) or printed_page < 1
                    or not isinstance(page_index, int) or page_index != printed_page - 1
                    or page_index >= len(document)
                    or not isinstance(xref, int) or xref < 1):
                raise CompositionError("asset PDF locator invalid")
            matches = [item for item in document[page_index].get_image_info(xrefs=True)
                       if item["xref"] == xref]
            if len(matches) != 1:
                raise CompositionError("asset PDF page/xref occurrence mismatch")
            extracted = document.extract_image(xref)
            if extracted is None or extracted["ext"] != "png":
                raise CompositionError("asset PDF image format mismatch")
            actual_image = extracted["image"]
            expected = asset.get("sha256", "")
            image_path = _private_file(Path(private_root), asset.get("private_file"))
            if not _SHA.fullmatch(expected) or _digest(image_path) != expected:
                raise CompositionError("private asset byte revision mismatch")
            if sha256(actual_image).hexdigest() != expected or image_path.read_bytes() != actual_image:
                raise CompositionError("private asset bytes differ from PDF image")
            match = matches[0]
            if ((asset.get("width"), asset.get("height")) != (extracted["width"], extracted["height"])
                    or (extracted["width"], extracted["height"]) != (match["width"], match["height"])
                    or asset.get("bbox_pdf_points") != list(match["bbox"])):
                raise CompositionError("asset PDF geometry mismatch")
            if asset.get("audience") not in {"GM", "PLAYER"} or not asset.get("name"):
                raise CompositionError("asset audience or name missing")
            resources[resource_id] = {
                "id": resource_id, "kind": "asset_reference", "name": asset["name"],
                "text": "Source image available privately; reference only pending content review.",
                "audience": asset["audience"],
                "origin": {"type": "source", "source_id": f"sha256:{pdf_sha}",
                           "locator": f"illustrated_pdf/page-{printed_page}#xref={xref}",
                           "printed_page": printed_page, "pdf_page_index": page_index,
                           "image_sha256": expected},
                "asset": {"status": "reference_only", "private_file": asset["private_file"],
                          "sha256": expected, "width": extracted["width"],
                          "height": extracted["height"],
                          "bbox_pdf_points": list(match["bbox"])},
            }
    diagnostics = deepcopy(base.get("diagnostics", []))
    diagnostics.append({"kind": "map_reference_only", "count": len(assets),
                        "reason": "private bytes extracted but map meaning and presentation not approved"})
    return output_store.save({
        "format_version": 1, "package_id": package_id,
        "title": f"{base['title']} with illustrated asset references", "form": "source",
        "lineage": [exact_base], "resources": resources,
        "relationships": deepcopy(base["relationships"]),
        "dependencies": deepcopy(base["dependencies"]),
        "proposals": [], "diagnostics": diagnostics,
        "asset_manifest_sha256": expected_manifest_sha256,
    })
