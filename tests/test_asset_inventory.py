"""Synthetic integrity witness for private, reference-only asset projection."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

try:
    import fitz
except ImportError:
    fitz = None

from compositor import CompositionError, JsonPackageStore, make_source_package
from compositor.asset_inventory import project_asset_references


def write_manifest(path: Path, value: dict) -> str:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(fitz is not None, "PyMuPDF required for real-PDF provenance regression")
class AssetInventoryTest(unittest.TestCase):
    def test_jpeg_projection_requires_exact_mime_and_audience_review(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            private = root / "private"
            private.mkdir()
            pdf = root / "illustrated.pdf"
            pixels = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10), False)
            pixels.clear_with(255)
            jpeg = pixels.tobytes("jpg")
            document = fitz.open()
            page = document.new_page(width=100, height=100)
            page.insert_image(fitz.Rect(10, 20, 40, 50), stream=jpeg)
            document.save(pdf)
            document.close()
            with fitz.open(pdf) as document:
                occurrence = document[0].get_image_info(xrefs=True)[0]
                extracted = document.extract_image(occurrence["xref"])
            self.assertEqual(extracted["ext"], "jpeg")
            image = private / "figure.jpeg"
            image.write_bytes(extracted["image"])
            base_store = JsonPackageStore(root / "base")
            base = make_source_package(base_store, package_id="jpeg-evidence",
                title="Synthetic JPEG evidence", resources={
                    "text": {"id": "text", "kind": "note", "name": "Field notes",
                             "text": "A public note", "audience": "GM",
                             "origin": {"type": "authored", "reason": "synthetic fixture"}},
                })
            base_ref = {"package_id": base["package_id"], "revision": base["revision"]}
            manifest = {"format_version": 1, "status": "reference_only",
                "base_package_ref": base_ref,
                "illustrated_pdf": {"path": str(pdf), "sha256": sha256(pdf.read_bytes()).hexdigest()},
                "assets": [{"resource_id": "figure", "name": "Synthetic figure",
                            "audience": "GM", "audience_review": "gm_only",
                            "mime_type": "image/jpeg", "status": "reference_only",
                            "printed_page": 1, "pdf_page_index": 0,
                            "xref": occurrence["xref"], "private_file": "figure.jpeg",
                            "sha256": sha256(image.read_bytes()).hexdigest(),
                            "width": extracted["width"], "height": extracted["height"],
                            "bbox_pdf_points": list(occurrence["bbox"])}]}
            manifest_path = private / "manifest.json"

            def project(output: str) -> dict:
                manifest_sha = write_manifest(manifest_path, manifest)
                return project_asset_references(
                    base_store=base_store, base_ref=base_ref,
                    output_store=JsonPackageStore(root / output), package_id="jpeg-assets",
                    manifest_path=manifest_path, expected_manifest_sha256=manifest_sha,
                    private_root=private)

            package = project("valid")
            self.assertEqual(package["resources"]["figure"]["asset"]["mime_type"],
                             "image/jpeg")
            self.assertEqual(package["resources"]["figure"]["asset"]["audience_review"],
                             "gm_only")
            self.assertIn({"kind": "asset_reference_only", "count": 1,
                "reason": "private image bytes verified; visual meaning and player presentation not approved"},
                package["diagnostics"])
            self.assertNotIn(image.read_bytes().hex(), json.dumps(package))

            del manifest["assets"][0]["mime_type"]
            with self.assertRaisesRegex(CompositionError, "MIME type mismatch"):
                project("missing-mime")
            manifest["assets"][0]["mime_type"] = "image/jpeg"
            del manifest["assets"][0]["audience_review"]
            with self.assertRaisesRegex(CompositionError, "audience review"):
                project("missing-audience-review")
            manifest["assets"][0]["audience_review"] = "gm_only"
            manifest["assets"][0]["mime_type"] = "image/png"
            with self.assertRaisesRegex(CompositionError, "MIME type mismatch"):
                project("wrong-mime")
            manifest["assets"][0]["mime_type"] = "image/jpeg"
            manifest["assets"][0]["audience_review"] = "player_safe_reviewed"
            with self.assertRaisesRegex(CompositionError, "audience review"):
                project("wrong-audience-review")
            manifest["assets"][0]["audience_review"] = "gm_only"
            manifest["assets"][0]["audience"] = "PLAYER"
            with self.assertRaisesRegex(CompositionError, "audience review"):
                project("unreviewed-player")
            manifest["assets"][0]["audience"] = "GM"
            manifest["assets"][0]["xref"] += 1
            with self.assertRaisesRegex(CompositionError, "page/xref occurrence mismatch"):
                project("wrong-locator")
            manifest["assets"][0]["xref"] -= 1
            image.write_bytes(b"substituted JPEG")
            manifest["assets"][0]["sha256"] = sha256(image.read_bytes()).hexdigest()
            with self.assertRaisesRegex(CompositionError, "differ from PDF image"):
                project("rehashed-image")

    def test_reference_projection_reloads_and_rejects_substitution(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            private = root / "private"
            private.mkdir()
            pdf = root / "illustrated.pdf"
            document = fitz.open()
            page = document.new_page(width=100, height=100)
            pixels = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10), False)
            pixels.clear_with(255)
            page.insert_image(fitz.Rect(10, 20, 40, 50), stream=pixels.tobytes("png"))
            document.save(pdf)
            document.close()
            with fitz.open(pdf) as document:
                occurrence = document[0].get_image_info(xrefs=True)[0]
                extracted = document.extract_image(occurrence["xref"])
            image = private / "map.png"
            image.write_bytes(extracted["image"])
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
                            "status": "reference_only", "printed_page": 1,
                            "pdf_page_index": 0, "xref": occurrence["xref"], "private_file": "map.png",
                            "sha256": sha256(image.read_bytes()).hexdigest(),
                            "width": extracted["width"], "height": extracted["height"],
                            "bbox_pdf_points": list(occurrence["bbox"])}]}
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
            manifest["assets"][0]["sha256"] = sha256(image.read_bytes()).hexdigest()
            manifest_sha = write_manifest(manifest_path, manifest)
            with self.assertRaisesRegex(CompositionError, "differ from PDF image"):
                project("rehashed-substitution")
            image.write_bytes(extracted["image"])
            manifest["assets"][0]["sha256"] = sha256(image.read_bytes()).hexdigest()
            manifest_sha = write_manifest(manifest_path, manifest)
            pdf.write_bytes(b"substituted PDF")
            with self.assertRaisesRegex(CompositionError, "illustrated PDF revision mismatch"):
                project("tampered-pdf")
            with fitz.open() as replacement:
                replacement.new_page(width=100, height=100)
                replacement.save(pdf)
            manifest["illustrated_pdf"]["sha256"] = sha256(pdf.read_bytes()).hexdigest()
            manifest_sha = write_manifest(manifest_path, manifest)
            with self.assertRaisesRegex(CompositionError, "page/xref occurrence mismatch"):
                project("rehashed-pdf-substitution")
            # Restore the exact original PDF for status/path checks.
            pdf.unlink()
            document = fitz.open()
            page = document.new_page(width=100, height=100)
            page.insert_image(fitz.Rect(10, 20, 40, 50), stream=pixels.tobytes("png"))
            document.save(pdf)
            document.close()
            manifest["illustrated_pdf"]["sha256"] = sha256(pdf.read_bytes()).hexdigest()
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
