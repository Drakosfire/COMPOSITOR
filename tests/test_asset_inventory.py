"""Synthetic integrity witness for private, reference-only asset projection."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor import CompositionError, JsonPackageStore, make_source_package
from compositor.asset_inventory import project_asset_references


def write_manifest(path: Path, value: dict) -> str:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return sha256(path.read_bytes()).hexdigest()


class AssetInventoryTest(unittest.TestCase):
    def test_reference_projection_reloads_and_rejects_substitution(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            private = root / "private"
            private.mkdir()
            pdf = root / "illustrated.pdf"
            pdf.write_bytes(b"public synthetic PDF identity")
            image = private / "map.png"
            image.write_bytes(b"public synthetic image bytes")
            base_store = JsonPackageStore(root / "base")
            base = make_source_package(base_store, package_id="synthetic-evidence",
                title="Synthetic evidence", resources={
                    "text": {"id": "text", "kind": "note", "name": "Field notes",
                             "text": "A public note", "audience": "GM",
                             "origin": {"type": "authored", "reason": "synthetic fixture"}},
                })
            base_ref = {"package_id": base["package_id"], "revision": base["revision"]}
            manifest = {"format_version": 1, "status": "reference_only",
                "base_package_ref": base_ref,
                "illustrated_pdf": {"path": str(pdf), "sha256": sha256(pdf.read_bytes()).hexdigest()},
                "assets": [{"resource_id": "map", "name": "Synthetic map", "audience": "GM",
                            "status": "reference_only", "printed_page": 4,
                            "pdf_page_index": 3, "xref": 31, "private_file": "map.png",
                            "sha256": sha256(image.read_bytes()).hexdigest(),
                            "width": 10, "height": 10, "bbox_pdf_points": [1, 2, 3, 4]}]}
            manifest_path = private / "manifest.json"
            manifest_sha = write_manifest(manifest_path, manifest)

            def project(output: str = "derived") -> dict:
                return project_asset_references(
                    base_store=base_store, base_ref=base_ref,
                    output_store=JsonPackageStore(root / output), package_id="synthetic-assets",
                    manifest_path=manifest_path, expected_manifest_sha256=manifest_sha,
                    private_root=private)

            package = project()
            reloaded = JsonPackageStore(root / "derived").load({
                "package_id": package["package_id"], "revision": package["revision"]})
            self.assertEqual(reloaded["lineage"], [base_ref])
            self.assertEqual(reloaded["resources"]["map"]["asset"]["status"], "reference_only")
            self.assertEqual(reloaded["resources"]["map"]["origin"]["source_id"],
                             f"sha256:{sha256(pdf.read_bytes()).hexdigest()}")
            self.assertEqual(reloaded["resources"]["text"], base["resources"]["text"])
            self.assertNotIn(image.read_bytes().hex(), json.dumps(reloaded))

            image.write_bytes(b"substituted bytes")
            with self.assertRaisesRegex(CompositionError, "asset byte revision mismatch"):
                project("tampered-image")
            image.write_bytes(b"public synthetic image bytes")
            pdf.write_bytes(b"substituted PDF")
            with self.assertRaisesRegex(CompositionError, "illustrated PDF revision mismatch"):
                project("tampered-pdf")
            pdf.write_bytes(b"public synthetic PDF identity")
            manifest["assets"][0]["status"] = "verified"
            manifest_sha = write_manifest(manifest_path, manifest)
            with self.assertRaisesRegex(CompositionError, "cannot claim verified"):
                project("false-verification")
            manifest["assets"][0]["status"] = "reference_only"
            manifest["assets"][0]["private_file"] = "../outside.png"
            manifest_sha = write_manifest(manifest_path, manifest)
            with self.assertRaisesRegex(CompositionError, "escapes private root"):
                project("outside-private")


if __name__ == "__main__":
    unittest.main()
