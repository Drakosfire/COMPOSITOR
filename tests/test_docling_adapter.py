"""Project-authored Docling fixture and source-pin boundaries."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor import (CompositionError, JsonPackageStore, effective_content,
                        load_docling_evidence_draft)


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "fixtures/public/windmill-field-notes.pdf"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class DoclingAdapterTest(unittest.TestCase):
    def test_pinned_intermediate_preserves_text_table_and_picture_locators(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            docling_path = root / "docling.json"
            table = {"num_rows": 1, "num_cols": 2, "table_cells": [
                {"row_span": 1, "col_span": 1, "start_row_offset_idx": 0,
                 "start_col_offset_idx": 0, "text": "Wind"},
                {"row_span": 1, "col_span": 1, "start_row_offset_idx": 0,
                 "start_col_offset_idx": 1, "text": "Step"}]}
            doc = {"schema_name": "DoclingDocument", "version": "1.0.0",
                   "pages": {"1": {"page_no": 1}},
                   "texts": [{"self_ref": "#/texts/0", "parent": {"$ref": "#/body"},
                              "children": [], "label": "section_header", "level": 1,
                              "text": "North Mill Field Notes",
                              "prov": [{"page_no": 1, "bbox": {"l": 1, "t": 2, "r": 3, "b": 4}}]}],
                   "tables": [{"self_ref": "#/tables/0", "data": table,
                               "prov": [{"page_no": 1}]}],
                   "pictures": [{"self_ref": "#/pictures/0", "prov": [{"page_no": 1}]}]}
            docling_path.write_text(json.dumps(doc), encoding="utf-8")
            store = JsonPackageStore(root / "packages")

            def load(**overrides: object):
                args = {"pdf_path": PDF, "docling_path": docling_path,
                        "expected_pdf_sha256": digest(PDF),
                        "expected_docling_sha256": digest(docling_path),
                        "package_id": "windmill-docling", "title": "North Mill Field Notes"}
                args.update(overrides)
                return load_docling_evidence_draft(store, **args)

            first = load()
            again = load()
            self.assertEqual(first.package["revision"], again.package["revision"])
            content = effective_content(store, {"package_id": first.package["package_id"],
                                                "revision": first.package["revision"]})
            self.assertEqual(first.report["resource_counts"],
                             {"texts": 1, "tables": 1, "pictures": 1})
            self.assertEqual(first.report["provider_calls"], 0)
            self.assertEqual(content["readiness"],
                             {"worldbuilding": "limited", "planning": "limited", "playing": "limited"})
            self.assertIn("source_correspondence_unverified",
                          {issue["kind"] for issue in content["issues"]})
            for collection, index in (("texts", 0), ("tables", 0), ("pictures", 0)):
                resource = content["resources"][f"docling-{collection}-{index}"]
                self.assertEqual(resource["origin"]["source_id"], f"sha256:{digest(PDF)}")
                self.assertEqual(resource["origin"]["locator"],
                                 f"docling-json#/{collection}/{index}")
                self.assertEqual(resource["origin"]["intermediate_sha256"], digest(docling_path))
                self.assertEqual(resource["origin"]["pages"], [1])
            self.assertEqual(content["resources"]["docling-tables-0"]["table_data"], table)
            self.assertEqual(content["resources"]["docling-texts-0"]["origin"]["docling_parent"],
                             {"$ref": "#/body"})
            self.assertEqual(content["resources"]["docling-texts-0"]["origin"]["docling_level"], 1)
            self.assertEqual(content["resources"]["docling-pictures-0"]["asset"]["status"],
                             "reference_only")

            with self.assertRaisesRegex(CompositionError, "source PDF revision mismatch"):
                load(expected_pdf_sha256="0" * 64)
            with self.assertRaisesRegex(CompositionError, "Docling intermediate revision mismatch"):
                load(expected_docling_sha256="0" * 64)
            non_pdf = root / "not-a-pdf.bin"
            non_pdf.write_bytes(b"plain text")
            with self.assertRaisesRegex(CompositionError, "source PDF is not a PDF"):
                load(pdf_path=non_pdf, expected_pdf_sha256=digest(non_pdf))
            with self.assertRaisesRegex(CompositionError, "selected pages must exist"):
                load(selected_pages=[2])
            with self.assertRaisesRegex(CompositionError, "integer page numbers"):
                load(selected_pages=[True])

    def test_missing_provenance_is_diagnostic_not_a_fabricated_resource(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "docling.json"
            path.write_text(json.dumps({"schema_name": "DoclingDocument", "pages": {"1": {"page_no": 1}},
                                        "texts": [{"text": "Unsupported", "prov": []}],
                                        "tables": [], "pictures": []}))
            result = load_docling_evidence_draft(
                JsonPackageStore(root / "packages"), pdf_path=PDF, docling_path=path,
                expected_pdf_sha256=digest(PDF), expected_docling_sha256=digest(path),
                package_id="missing-provenance", title="Missing provenance")
            self.assertEqual(result.package["resources"], {})
            self.assertIn("missing_element_provenance",
                          {issue["kind"] for issue in result.report["diagnostics"]})


if __name__ == "__main__":
    unittest.main()
