"""Public synthetic proof of immutable evidence output and separate gold coverage."""

from hashlib import sha256
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from compositor import CompositionError, JsonPackageStore, load_evidence_draft
from compositor.deterministic_baseline import build_recovery_coverage, freeze_first_evidence_result


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "fixtures/public/evidence/supplied_markdown"
PDF_PUBLIC = ROOT / "fixtures/public/pdf_text_baseline"
OWNER_REF = "17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class DeterministicBaselineTest(unittest.TestCase):
    def test_pdf_text_page_order_missing_text_and_gold_separation(self) -> None:
        with TemporaryDirectory() as temp:
            private = Path(temp)
            store = JsonPackageStore(private / "packages")
            manifest_path = PDF_PUBLIC / "manifest.json"
            source_manifest = PDF_PUBLIC / "source-manifest.json"
            manifest_sha = digest(manifest_path)
            source_sha = digest(source_manifest)
            loaded = load_evidence_draft(
                store, PDF_PUBLIC, project_root=ROOT, package_id="pdf-text-synthetic",
                title="Synthetic PDF", expected_rules_ingestion_ref=OWNER_REF,
                expected_manifest_sha256=manifest_sha)
            ref = {key: loaded.package[key] for key in ("package_id", "revision")}
            def freeze(path: Path, **overrides: object) -> dict:
                kwargs = dict(store=store, package_ref=ref, evidence_dir=PDF_PUBLIC,
                              project_root=ROOT, source_manifest_path=source_manifest,
                              source_manifest_sha256=source_sha,
                              evidence_manifest_sha256=manifest_sha,
                              rules_ingestion_ref=OWNER_REF, suite="synthetic-pdf-text-baseline",
                              private_root=private, output_path=path)
                kwargs.update(overrides)
                return freeze_first_evidence_result(**kwargs)
            first_path = private / "runs" / "a" / "first.json"
            replay_path = private / "runs" / "b" / "first.json"
            first = freeze(first_path)
            replay = freeze(replay_path)
            self.assertEqual(first["sha256"], replay["sha256"])
            first_doc = json.loads(first_path.read_text())
            self.assertEqual(first_doc["route"], "pdf_text")
            self.assertEqual(first_doc["page_map"], {"0": 1, "1": 2, "2": 3})
            self.assertEqual(first_doc["direct_source_sha256"],
                             json.loads(manifest_path.read_text())["source_pdf_sha256"])
            self.assertIn({"kind": "missing_text", "page_index": 1, "printed_page": 2},
                          first_doc["recovery_diagnostics"])
            self.assertIn({"kind": "image_content_unsupported", "count": 1},
                          first_doc["recovery_diagnostics"])
            gold = {"status": "frozen", "suite": "synthetic-pdf-text-baseline", "case_count": 4,
                    "cases": [
                        {"id": "P1", "category": "narrative", "expectation": "GOLD_ONLY",
                         "evidence": {"printer_friendly_pdf_printed_page": 1}},
                        {"id": "P2", "category": "narrative",
                         "evidence": {"printer_friendly_pdf_printed_page": 2}},
                        {"id": "P3", "category": "narrative",
                         "evidence": {"printer_friendly_pdf_printed_page": 3}},
                        {"id": "P4", "category": "asset_map",
                         "evidence": {"printer_friendly_pdf_printed_page": 3}},
                    ]}
            gold_path = private / "proposal.json"
            gold_path.write_text(json.dumps(gold, sort_keys=True) + "\n")
            freeze_path = private / "freeze.json"
            freeze_path.write_text(json.dumps({
                "status": "frozen", "suite": "synthetic-pdf-text-baseline", "case_count": 4,
                "files": {"proposal.json": {"sha256": digest(gold_path)},
                          "source_manifest.json": {"sha256": source_sha}},
            }, sort_keys=True) + "\n")
            self.assertNotIn("GOLD_ONLY", first_path.read_text())
            packet = build_recovery_coverage(
                first_result_path=first_path, first_result_sha256=first["sha256"],
                gold_path=gold_path, gold_sha256=digest(gold_path),
                freeze_record_path=freeze_path,
                freeze_record_sha256=digest(freeze_path))
            self.assertEqual(packet["totals"], {"recovered_page_evidence": 2,
                                                 "missing_page_evidence": 1,
                                                 "unsupported_image_evidence": 1})
            self.assertEqual(packet["recovery_route"], "pdf_text")
            self.assertEqual(packet["structural"]["resource_unit_count"], 2)
            self.assertEqual(packet["structural"]["pages_without_units"], 1)
            self.assertEqual(packet["structural"]["units_by_printed_page"]["2"], 0)
            self.assertTrue(all(case["semantic_verdict"] is None for case in packet["cases"]))

            wrong_bundle = private / "wrong-bundle"
            shutil.copytree(PDF_PUBLIC, wrong_bundle)
            wrong_manifest = wrong_bundle / "manifest.json"
            altered = json.loads(wrong_manifest.read_text())
            altered["pages"][0], altered["pages"][1] = altered["pages"][1], altered["pages"][0]
            wrong_manifest.write_text(json.dumps(altered, sort_keys=True) + "\n")
            refused = private / "runs" / "refused" / "first.json"
            with self.assertRaisesRegex(CompositionError, "page order mismatch"):
                freeze(refused, evidence_dir=wrong_bundle,
                       evidence_manifest_sha256=digest(wrong_manifest))
            self.assertFalse(refused.exists())
            with self.assertRaisesRegex(CompositionError, "evidence manifest revision mismatch"):
                freeze(refused, evidence_manifest_sha256="0" * 64)
            self.assertFalse(refused.exists())

    def test_replay_identity_gold_separation_and_recovery_scope(self) -> None:
        with TemporaryDirectory() as temp:
            private = Path(temp)
            evidence = private / "evidence"
            shutil.copytree(PUBLIC, evidence)
            manifest_path = evidence / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["pages"][0]["printed_page"] = 1
            manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
            manifest_sha = digest(manifest_path)
            source_manifest = private / "source-manifest.json"
            source_manifest.write_text(json.dumps({"source_files": {
                "normalized_markdown": {"sha256": manifest["supplied_markdown_sha256"]},
                "printer_friendly_pdf": {"sha256": manifest["source_pdf_sha256"]},
            }}, sort_keys=True) + "\n")
            source_sha = digest(source_manifest)
            store = JsonPackageStore(private / "packages")
            loaded = load_evidence_draft(
                store, evidence, project_root=ROOT, package_id="windmill-baseline",
                title="Windmill", expected_rules_ingestion_ref=OWNER_REF,
                expected_manifest_sha256=manifest_sha,
            )
            ref = {key: loaded.package[key] for key in ("package_id", "revision")}
            paths = [private / "runs" / name / "first-result.json" for name in ("a", "b")]
            def freeze(path: Path, **overrides: str) -> dict:
                kwargs = dict(store=store, package_ref=ref, evidence_dir=evidence,
                              project_root=ROOT, source_manifest_path=source_manifest,
                              source_manifest_sha256=source_sha,
                              evidence_manifest_sha256=manifest_sha,
                              rules_ingestion_ref=OWNER_REF, suite="synthetic-windmill",
                              private_root=private, output_path=path)
                kwargs.update(overrides)
                return freeze_first_evidence_result(**kwargs)
            first = freeze(paths[0])
            second = freeze(paths[1])
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(first["provider_calls"], 0)
            with self.assertRaises(FileExistsError):
                freeze(paths[0])

            gold = {"status": "frozen", "suite": "synthetic-windmill", "case_count": 3,
                    "cases": [
                        {"id": "E1", "category": "narrative", "expectation": "GOLD_ONLY",
                         "evidence": {"normalized_markdown_page_marker": 1}},
                        {"id": "E2", "category": "narrative",
                         "evidence": {"normalized_markdown_page_marker": 9}},
                        {"id": "E3", "category": "asset_map",
                         "evidence": {"normalized_markdown_page_marker": 1}},
                    ]}
            gold_path = private / "gold.json"
            gold_path.write_text(json.dumps(gold, sort_keys=True) + "\n")
            freeze_record = private / "freeze.json"
            freeze_record.write_text(json.dumps({
                "status": "frozen", "suite": "synthetic-windmill", "case_count": 3,
                "files": {"proposal.json": {"sha256": digest(gold_path)},
                          "source_manifest.json": {"sha256": source_sha}},
            }, sort_keys=True) + "\n")
            self.assertNotIn("GOLD_ONLY", paths[0].read_text())
            packet = build_recovery_coverage(
                first_result_path=paths[0], first_result_sha256=first["sha256"],
                gold_path=gold_path, gold_sha256=digest(gold_path),
                freeze_record_path=freeze_record,
                freeze_record_sha256=digest(freeze_record))
            self.assertEqual(packet["totals"], {
                "recovered_page_evidence": 1, "missing_page_evidence": 1,
                "unsupported_image_evidence": 1})
            self.assertEqual(packet["recovery_route"], "supplied_markdown")
            self.assertTrue(packet["cases"][0]["candidate_resource_ids"])
            self.assertTrue(all(case["semantic_verdict"] is None for case in packet["cases"]))
            with self.assertRaisesRegex(CompositionError, "gold freeze does not bind"):
                self._wrong_freeze(paths[0], first["sha256"], gold_path,
                                   freeze_record, private)
            wrong_source = private / "wrong-source.json"
            wrong_source.write_text(json.dumps({"source_files": {
                "normalized_markdown": {"sha256": "0" * 64},
                "printer_friendly_pdf": {"sha256": manifest["source_pdf_sha256"]},
            }}, sort_keys=True) + "\n")
            refused = private / "runs" / "refused" / "first-result.json"
            with self.assertRaisesRegex(CompositionError, "does not bind evidence"):
                freeze(refused, source_manifest_path=wrong_source,
                       source_manifest_sha256=digest(wrong_source))
            self.assertFalse(refused.exists())
            with self.assertRaisesRegex(CompositionError, "first result revision mismatch"):
                build_recovery_coverage(
                    first_result_path=paths[0], first_result_sha256="0" * 64,
                    gold_path=gold_path, gold_sha256=digest(gold_path),
                    freeze_record_path=freeze_record,
                    freeze_record_sha256=digest(freeze_record))

    @staticmethod
    def _wrong_freeze(first_path: Path, first_sha: str, gold_path: Path,
                      freeze_path: Path, private: Path) -> None:
        wrong = json.loads(freeze_path.read_text())
        wrong["files"]["source_manifest.json"]["sha256"] = "0" * 64
        wrong_path = private / "wrong-freeze.json"
        wrong_path.write_text(json.dumps(wrong, sort_keys=True) + "\n")
        build_recovery_coverage(first_result_path=first_path, first_result_sha256=first_sha,
                                gold_path=gold_path, gold_sha256=digest(gold_path),
                                freeze_record_path=wrong_path,
                                freeze_record_sha256=digest(wrong_path))

    def test_pin_mismatch_fails_before_output(self) -> None:
        with TemporaryDirectory() as temp:
            private = Path(temp)
            evidence = private / "evidence"
            shutil.copytree(PUBLIC, evidence)
            source_manifest = private / "source.json"
            source_manifest.write_text("{}\n")
            store = JsonPackageStore(private / "packages")
            output = private / "first-result.json"
            with self.assertRaisesRegex(CompositionError, "source manifest revision mismatch"):
                freeze_first_evidence_result(
                    store=store, package_ref={"package_id": "absent", "revision": "0" * 64},
                    evidence_dir=evidence, project_root=ROOT,
                    source_manifest_path=source_manifest,
                    source_manifest_sha256="0" * 64,
                    evidence_manifest_sha256=digest(evidence / "manifest.json"),
                    rules_ingestion_ref=OWNER_REF, suite="synthetic-windmill",
                    private_root=private, output_path=output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
