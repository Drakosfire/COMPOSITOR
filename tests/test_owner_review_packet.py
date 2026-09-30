"""Synthetic owner first-result review and persistent judgment lifecycle."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor import CompositionError, JsonPackageStore, SQLiteExperimentLedger, load_evidence_draft
from compositor.owner_evidence_first import freeze_owner_first_result
from scripts.review_owner_evidence_first import review_owner_first


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "fixtures/public/evidence/rules_ingestion_ab"
OWNER_REF = "17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8"
SUITE = "synthetic-owner-review"
RUN_ID = "synthetic-owner-review-001"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> str:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return digest(path)


class OwnerReviewPacketTest(unittest.TestCase):
    def test_frozen_packet_stays_unjudged_until_complete_human_review(self) -> None:
        with TemporaryDirectory() as temp:
            private = Path(temp)
            database = private / "experiments.sqlite3"
            store = JsonPackageStore(private / "packages")
            source_path = private / "source_manifest.json"
            manifest = json.loads((BUNDLE / "manifest.json").read_text())
            source_sha = write_json(source_path, {
                "suite": SUITE, "source_files": {"printer_friendly_pdf": {
                    "sha256": manifest["source_pdf_sha256"]}}})
            manifest_sha = digest(BUNDLE / "manifest.json")
            loaded = load_evidence_draft(
                store, BUNDLE, project_root=ROOT, package_id="owner-review",
                title="North Mill Field Notes", expected_rules_ingestion_ref=OWNER_REF,
                expected_manifest_sha256=manifest_sha)
            first_path = private / "first-result.json"
            freeze_owner_first_result(
                store=store, package_ref={key: loaded.package[key]
                                          for key in ("package_id", "revision")},
                evidence_dir=BUNDLE, project_root=ROOT,
                source_manifest_path=source_path,
                source_manifest_sha256=source_sha,
                evidence_manifest_sha256=manifest_sha,
                rules_ingestion_ref=OWNER_REF, suite=SUITE,
                printed_page_map={0: 1}, private_root=private,
                output_path=first_path)
            gold_path = private / "proposal.json"
            gold_sha = write_json(gold_path, {
                "status": "frozen", "suite": SUITE, "case_count": 3,
                "cases": [
                    {"id": "S1", "category": "rule", "task": "playing",
                     "expectation": "Find source rule", "evidence": {
                         "printer_friendly_pdf_printed_page": 1}},
                    {"id": "S2", "category": "rule", "task": "planning",
                     "expectation": "Another page", "evidence": {
                         "printer_friendly_pdf_printed_page": 2}},
                    {"id": "S3", "category": "asset_map", "task": "worldbuilding",
                     "expectation": "Locate a map", "evidence": {
                         "printer_friendly_pdf_printed_page": 1}},
                ]})
            freeze_path = private / "freeze-record.json"
            write_json(freeze_path, {
                "status": "frozen", "suite": SUITE, "case_count": 3,
                "files": {"proposal.json": {"sha256": gold_sha},
                          "source_manifest.json": {"sha256": source_sha}}})
            with SQLiteExperimentLedger(database, private_root=private) as ledger:
                ledger.create_run(
                    run_id=RUN_ID, suite=SUITE,
                    source_manifest_sha256=source_sha,
                    frozen_gold_sha256=gold_sha,
                    recipe_sha256="a" * 64, recovery_route="rules_ingestion_ab",
                    provider_exposure="none", provider=None, model=None,
                    call_cap=0, spend_cap_usd=0)
                ledger.record_artifact(run_id=RUN_ID, role="first_result",
                                       name="primary", path=first_path)
                ledger.close_run(RUN_ID)
            kwargs = dict(private_root=private, database=database,
                          run_id=RUN_ID, gold_path=gold_path,
                          freeze_record_path=freeze_path)
            prepared = review_owner_first(mode="prepare", **kwargs)
            draft_path = Path(prepared["draft_path"])
            packet = json.loads(draft_path.read_text(encoding="utf-8"))
            self.assertEqual([case["coverage_state"] for case in packet["cases"]],
                             ["recovered_page_evidence", "out_of_scope",
                              "unsupported_image_evidence"])
            self.assertTrue(packet["cases"][0]["candidate_resources"])
            self.assertFalse(packet["task_success_inferred_from_page_presence"])
            self.assertTrue(all(case["review"] is None for case in packet["cases"]))
            with self.assertRaisesRegex(CompositionError, "partial gold adjudication"):
                review_owner_first(mode="finalize", **kwargs)
            packet["cases"][0]["expectation"] = "tampered"
            write_json(draft_path, packet)
            with self.assertRaisesRegex(CompositionError, "context changed"):
                review_owner_first(mode="finalize", **kwargs)
            packet["cases"][0]["expectation"] = "Find source rule"
            for case in packet["cases"]:
                case["review"] = {
                    "verdict": "unresolved", "reviewer": "synthetic-reviewer",
                    "rationale": "Source page presence alone cannot prove this task.",
                    "resource_ids": [],
                }
            write_json(draft_path, packet)
            completed = review_owner_first(mode="finalize", **kwargs)
            self.assertEqual(completed["summary"]["reviewed"], 3)
            with SQLiteExperimentLedger(database, private_root=private) as ledger:
                self.assertEqual(ledger.connection.execute(
                    "SELECT COUNT(*) FROM judgments WHERE run_id = ?",
                    (RUN_ID,)).fetchone()[0], 3)
                self.assertEqual(ledger.verify_artifact(
                    run_id=RUN_ID, role="owner_gold_adjudication",
                    name="primary"), Path(completed["artifact_path"]))


if __name__ == "__main__":
    unittest.main()
