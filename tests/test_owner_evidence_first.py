"""Synthetic owner A/B first-result and selected-page coverage witnesses."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor import CompositionError, JsonPackageStore, load_evidence_draft
from compositor.owner_evidence_first import freeze_owner_first_result, score_owner_page_coverage


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "fixtures/public/evidence/rules_ingestion_ab"
OWNER_REF = "17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8"
SUITE = "synthetic-owner-ab"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> str:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return digest(path)


class OwnerEvidenceFirstTest(unittest.TestCase):
    def test_freeze_then_score_selected_page_without_claiming_semantics(self) -> None:
        with TemporaryDirectory() as temp:
            private = Path(temp)
            store = JsonPackageStore(private / "packages")
            manifest = json.loads((BUNDLE / "manifest.json").read_text())
            manifest_sha = digest(BUNDLE / "manifest.json")
            source_path = private / "source_manifest.json"
            source_sha = write_json(source_path, {
                "suite": SUITE, "source_files": {"printer_friendly_pdf": {
                    "sha256": manifest["source_pdf_sha256"]}}})
            loaded = load_evidence_draft(
                store, BUNDLE, project_root=ROOT, package_id="owner-first",
                title="North Mill Field Notes", expected_rules_ingestion_ref=OWNER_REF,
                expected_manifest_sha256=manifest_sha)
            package_ref = {key: loaded.package[key] for key in ("package_id", "revision")}
            first_path = private / "first-result.json"
            first = freeze_owner_first_result(
                store=store, package_ref=package_ref, evidence_dir=BUNDLE,
                project_root=ROOT, source_manifest_path=source_path,
                source_manifest_sha256=source_sha,
                evidence_manifest_sha256=manifest_sha,
                rules_ingestion_ref=OWNER_REF, suite=SUITE,
                printed_page_map={0: 1}, private_root=private,
                output_path=first_path)
            self.assertEqual(first["sha256"], digest(first_path))
            self.assertEqual(first["provider_usage"]["status"], "unknown")
            self.assertIsNone(first["provider_usage"]["calls"])
            self.assertNotIn("GOLD_ONLY", first_path.read_text())
            with self.assertRaises(FileExistsError):
                freeze_owner_first_result(
                    store=store, package_ref=package_ref, evidence_dir=BUNDLE,
                    project_root=ROOT, source_manifest_path=source_path,
                    source_manifest_sha256=source_sha,
                    evidence_manifest_sha256=manifest_sha,
                    rules_ingestion_ref=OWNER_REF, suite=SUITE,
                    printed_page_map={0: 1}, private_root=private,
                    output_path=first_path)
            gold_path = private / "proposal.json"
            gold_sha = write_json(gold_path, {
                "status": "frozen", "suite": SUITE, "case_count": 5,
                "cases": [
                    {"id": "S1", "category": "rule", "expectation": "GOLD_ONLY",
                     "evidence": {"printer_friendly_pdf_printed_page": 1}},
                    {"id": "S2", "category": "rule",
                     "evidence": {"printer_friendly_pdf_printed_page": 2}},
                    {"id": "S3", "category": "rule",
                     "evidence": {"printer_friendly_pdf_printed_page": 1,
                                  "additional_printer_friendly_pdf_printed_pages": [2]}},
                    {"id": "S4", "category": "asset_map",
                     "evidence": {"printer_friendly_pdf_printed_page": 1}},
                    {"id": "S5", "category": "rule", "evidence": {}},
                ]})
            freeze_path = private / "freeze-record.json"
            freeze_sha = write_json(freeze_path, {
                "status": "frozen", "suite": SUITE, "case_count": 5,
                "files": {"proposal.json": {"sha256": gold_sha},
                          "source_manifest.json": {"sha256": source_sha}}})
            scored = score_owner_page_coverage(
                first_result_path=first_path, first_result_sha256=first["sha256"],
                gold_path=gold_path, gold_sha256=gold_sha,
                freeze_record_path=freeze_path, freeze_record_sha256=freeze_sha)
            self.assertEqual(scored["totals"], {
                "out_of_scope": 2, "partial_scope": 1, "recovered_page_evidence": 1,
                "missing_page_evidence": 0, "unsupported_image_evidence": 1})
            self.assertEqual(scored["fully_scoped_cases"], 2)
            self.assertTrue(scored["cases"][2]["candidate_resource_ids"])
            self.assertTrue(all(case["semantic_verdict"] is None for case in scored["cases"]))
            self.assertIsNone(scored["provider_usage"]["calls"])
            with self.assertRaisesRegex(CompositionError, "first result revision mismatch"):
                score_owner_page_coverage(
                    first_result_path=first_path, first_result_sha256="0" * 64,
                    gold_path=gold_path, gold_sha256=gold_sha,
                    freeze_record_path=freeze_path, freeze_record_sha256=freeze_sha)

    def test_source_and_page_map_mismatch_fail_before_output(self) -> None:
        with TemporaryDirectory() as temp:
            private = Path(temp)
            store = JsonPackageStore(private / "packages")
            manifest_sha = digest(BUNDLE / "manifest.json")
            loaded = load_evidence_draft(
                store, BUNDLE, project_root=ROOT, package_id="owner-first",
                title="North Mill Field Notes", expected_rules_ingestion_ref=OWNER_REF,
                expected_manifest_sha256=manifest_sha)
            package_ref = {key: loaded.package[key] for key in ("package_id", "revision")}
            source_path = private / "source.json"
            source_sha = write_json(source_path, {
                "suite": SUITE, "source_files": {"printer_friendly_pdf": {
                    "sha256": "0" * 64}}})
            output = private / "first-result.json"
            kwargs = dict(store=store, package_ref=package_ref, evidence_dir=BUNDLE,
                          project_root=ROOT, source_manifest_path=source_path,
                          source_manifest_sha256=source_sha,
                          evidence_manifest_sha256=manifest_sha,
                          rules_ingestion_ref=OWNER_REF, suite=SUITE,
                          printed_page_map={0: 1}, private_root=private,
                          output_path=output)
            with self.assertRaisesRegex(CompositionError, "does not bind owner PDF"):
                freeze_owner_first_result(**kwargs)
            self.assertFalse(output.exists())
            manifest = json.loads((BUNDLE / "manifest.json").read_text())
            source_sha = write_json(source_path, {
                "suite": SUITE, "source_files": {"printer_friendly_pdf": {
                    "sha256": manifest["source_pdf_sha256"]}}})
            kwargs.update(source_manifest_sha256=source_sha, printed_page_map={1: 2})
            with self.assertRaisesRegex(CompositionError, "printed-page map"):
                freeze_owner_first_result(**kwargs)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
