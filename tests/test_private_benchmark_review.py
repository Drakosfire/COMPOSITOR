"""Private packet lifecycle requires a closed, pinned first run."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor.experiment_ledger import SQLiteExperimentLedger
from compositor.package import CompositionError, JsonPackageStore, make_source_package
from scripts.review_private_benchmark import review_benchmark


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


class PrivateBenchmarkReviewTest(unittest.TestCase):
    def test_prepare_then_explicit_complete_review_is_persisted(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "fixture-first-001"
            source_sha = "a" * 64
            gold_path = root / "gold.json"
            write_json(gold_path, {"status": "frozen", "suite": "fixture", "case_count": 1,
                                   "cases": [{"id": "F001", "category": "person", "task": "planning",
                                              "severity": "material", "expectation": "Nar has a key",
                                              "evidence": {"normalized_markdown_page_marker": 2}}]})
            db_path = root / "experiments.sqlite3"
            store = JsonPackageStore(root / "runs" / run_id / "packages")
            package = make_source_package(store, package_id="fixture-package", title="Fixture",
                                          resources={"nar": {"id": "nar", "kind": "person",
                                          "name": "Nar", "text": "Nar has a key", "audience": "GM",
                                          "origin": {"type": "source",
                                          "source_id": f"sha256:{source_sha}",
                                          "locator": "printed-page:2"}}})
            package_path = store.path_for(package["package_id"], package["revision"])
            first_path = root / "runs" / run_id / "first-result.json"
            report_path = root / "runs" / run_id / "first-semantic-report.json"
            write_json(first_path, {"pages": []})
            write_json(report_path, {"run_id": run_id, "supplied_markdown_sha256": source_sha})
            with SQLiteExperimentLedger(db_path, private_root=root) as ledger:
                ledger.create_run(run_id=run_id, suite="fixture", source_manifest_sha256="b" * 64,
                                  frozen_gold_sha256=sha256(gold_path.read_bytes()).hexdigest(),
                                  recipe_sha256="c" * 64, recovery_route="fixture",
                                  provider_exposure="none", provider=None, model=None,
                                  call_cap=0, spend_cap_usd=0)
                ledger.record_artifact(run_id=run_id, role="first_result", name="primary", path=first_path)
                ledger.record_artifact(run_id=run_id, role="assembled_package", name="primary",
                                       path=package_path)
                ledger.record_artifact(run_id=run_id, role="run_report", name="primary", path=report_path)
                ledger.close_run(run_id)
            prepared = review_benchmark(mode="prepare", private_root=root, database=db_path,
                                        run_id=run_id, gold_path=gold_path)
            self.assertEqual(prepared["verdicts"], "none")
            draft_path = Path(prepared["draft_path"])
            draft = json.loads(draft_path.read_text())
            self.assertIsNone(draft["cases"][0]["review"])
            with self.assertRaisesRegex(CompositionError, "partial"):
                review_benchmark(mode="finalize", private_root=root, database=db_path,
                                 run_id=run_id, gold_path=gold_path)
            draft["cases"][0]["review"] = {"verdict": "pass", "reviewer": "parent",
                                             "rationale": "The source and package both state Nar has a key.",
                                             "resource_ids": ["nar"]}
            write_json(draft_path, draft)
            finalized = review_benchmark(mode="finalize", private_root=root, database=db_path,
                                         run_id=run_id, gold_path=gold_path)
            self.assertEqual(finalized["summary"]["reviewed"], 1)
            with SQLiteExperimentLedger(db_path, private_root=root) as ledger:
                self.assertEqual(ledger.verify_artifact(run_id=run_id, role="gold_adjudication",
                                                        name="primary"), Path(finalized["artifact_path"]))
                self.assertEqual(ledger.connection.execute(
                    "SELECT COUNT(*) FROM judgments WHERE run_id = ?", (run_id,)).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
