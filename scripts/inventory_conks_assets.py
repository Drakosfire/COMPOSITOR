"""Extract two pinned Conks maps privately and make a reference-only package."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compositor import JsonPackageStore  # noqa: E402
from compositor.asset_inventory import project_asset_references  # noqa: E402


SOURCE_MANIFEST_SHA = "eebebb2f802ce31ba5a0be763db37a1dcac6e4d94e02c79b746caac5ee933b2a"
ILLUSTRATED_SHA = "b85eb98ee60110e90de90fa04574ae8a5a2b19f4e24d42acd998ec34fdffba41"
SPECS = ((4, 31, "greenfields-map", "Greenfields regional map"),
         (8, 65, "hempholm-map", "Hempholm village map"))
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def extract_one(document: object, *, printed_page: int, xref: int,
                resource_id: str, name: str, private_file: str) -> tuple[dict, bytes]:
    """Require the exact xref once on its printed/physical illustrated page."""
    page = document[printed_page - 1]
    matches = [item for item in page.get_image_info(xrefs=True) if item["xref"] == xref]
    if len(matches) != 1:
        raise ValueError(f"expected one image at printed page {printed_page}, xref {xref}")
    image = document.extract_image(xref)
    if image is None or image["ext"] != "png":
        raise ValueError(f"expected PNG image at printed page {printed_page}, xref {xref}")
    match = matches[0]
    if (image["width"], image["height"]) != (match["width"], match["height"]):
        raise ValueError(f"image geometry differs at printed page {printed_page}, xref {xref}")
    data = image["image"]
    return ({
        "resource_id": resource_id, "name": name, "audience": "GM",
        "status": "reference_only", "printed_page": printed_page,
        "pdf_page_index": printed_page - 1, "xref": xref,
        "private_file": private_file, "sha256": sha256(data).hexdigest(),
        "width": image["width"], "height": image["height"],
        "bbox_pdf_points": list(match["bbox"]),
    }, data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--base-store", type=Path, required=True)
    parser.add_argument("--base-package-id", required=True)
    parser.add_argument("--base-revision", required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not SAFE_ID.fullmatch(args.run_id) or args.run_id in {".", ".."}:
        parser.error("run ID must be one safe path component")
    private_root = args.private_root.resolve()
    out = (private_root / "runs" / args.run_id).resolve()
    if not out.is_relative_to(private_root) or out.exists():
        parser.error("private output escapes root or already exists")
    if digest(args.source_manifest) != SOURCE_MANIFEST_SHA:
        parser.error("accepted Conks source manifest revision mismatch")
    source_manifest = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    if not source_manifest.get("accepted"):
        parser.error("accepted Conks source manifest required")
    source = source_manifest["source_files"]["illustrated_pdf"]
    pdf_path = Path(source["path"])
    if source["sha256"] != ILLUSTRATED_SHA or digest(pdf_path) != ILLUSTRATED_SHA:
        parser.error("illustrated PDF revision mismatch")
    base_ref = {"package_id": args.base_package_id, "revision": args.base_revision}
    base_store = JsonPackageStore(args.base_store)
    base_store.load(base_ref)  # Fail before output creation on a missing or changed base.

    try:
        import fitz
    except ImportError as exc:
        parser.error(f"PyMuPDF required for private PDF extraction: {exc}")
    extracted = []
    with fitz.open(pdf_path) as document:
        if len(document) != 20:
            parser.error("illustrated PDF must have 20 physical pages")
        for printed_page, xref, resource_id, name in SPECS:
            relative = f"runs/{args.run_id}/{resource_id}-p{printed_page}-xref{xref}.png"
            extracted.append(extract_one(
                document, printed_page=printed_page, xref=xref,
                resource_id=resource_id, name=name, private_file=relative,
            ))
    out.mkdir(parents=True)
    assets = []
    for entry, data in extracted:
        (private_root / entry["private_file"]).write_bytes(data)
        assets.append(entry)
    manifest_path = out / "asset-manifest.json"
    write_json(manifest_path, {
        "format_version": 1, "status": "reference_only", "base_package_ref": base_ref,
        "illustrated_pdf": {"path": str(pdf_path.resolve()), "sha256": ILLUSTRATED_SHA},
        "related_substrates": {
            "printer_friendly_pdf_sha256": source_manifest["source_files"]["printer_friendly_pdf"]["sha256"],
            "normalized_markdown_sha256": source_manifest["source_files"]["normalized_markdown"]["sha256"],
            "image_bytes_in_related_substrates": False,
        },
        "assets": assets,
    })
    package = project_asset_references(
        base_store=base_store, base_ref=base_ref,
        output_store=JsonPackageStore(out / "packages"),
        package_id=f"{args.base_package_id}-illustrated-assets-{args.run_id}",
        manifest_path=manifest_path, expected_manifest_sha256=digest(manifest_path),
        private_root=private_root,
    )
    print(json.dumps({"run_id": args.run_id, "status": "reference_only",
                      "asset_count": len(assets),
                      "asset_manifest_sha256": digest(manifest_path),
                      "package_ref": {"package_id": package["package_id"],
                                      "revision": package["revision"]},
                      "provider_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
