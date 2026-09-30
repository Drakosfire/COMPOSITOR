"""Persistent private run, immutable first-result, and budget witnesses."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor import CompositionError, SQLiteExperimentLedger


HASH = "a" * 64


class ExperimentLedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.private = Path(self.temp.name) / "private"
        self.database = self.private / "experiments.sqlite3"
        self.private.mkdir()

    def open(self) -> SQLiteExperimentLedger:
        return SQLiteExperimentLedger(self.database, private_root=self.private)

    def create_offline(self, ledger: SQLiteExperimentLedger) -> None:
        ledger.create_run(run_id="conks-offline-01", suite="of-conks-cons-v21",
                          source_manifest_sha256=HASH, frozen_gold_sha256=HASH,
                          recipe_sha256=HASH, recovery_route="supplied_markdown",
                          provider_exposure="none", provider=None, model=None,
                          call_cap=0, spend_cap_usd=0)

    def test_first_result_is_separate_immutable_and_persistent(self) -> None:
        result = self.private / "first-result.json"
        result.write_text('{"first": true}\n')
        with self.open() as ledger:
            self.create_offline(ledger)
            digest = ledger.record_artifact(run_id="conks-offline-01", role="first_result",
                                            name="primary", path=result)
            self.assertEqual(len(digest), 64)
            with self.assertRaisesRegex(Exception, "UNIQUE constraint"):
                ledger.record_artifact(run_id="conks-offline-01", role="first_result",
                                       name="primary", path=result)
            ledger.record_judgment(run_id="conks-offline-01", case_id="C040",
                                   result_role="first_result", verdict="unresolved",
                                   reviewer="parent", rationale="Source ambiguity retained")
            ledger.close_run("conks-offline-01")
        with self.open() as ledger:
            self.assertEqual(ledger.summary("conks-offline-01")["artifact_counts"], {"first_result": 1})
            self.assertEqual(ledger.verify_artifact(run_id="conks-offline-01",
                                                    role="first_result", name="primary"), result)
            result.write_text('{"first": false}\n')
            with self.assertRaisesRegex(CompositionError, "integrity mismatch"):
                ledger.verify_artifact(run_id="conks-offline-01", role="first_result", name="primary")

    def test_live_call_cap_spend_cap_unknown_cost_and_receipt_pin(self) -> None:
        with self.open() as ledger:
            ledger.create_run(run_id="conks-live-01", suite="of-conks-cons-v21",
                              source_manifest_sha256=HASH, frozen_gold_sha256=HASH,
                              recipe_sha256=HASH, recovery_route="supplied_markdown",
                              provider_exposure="approved_private_api",
                              provider="openai", model="example-model",
                              call_cap=2, spend_cap_usd=0.10)
            first = ledger.reserve_call(run_id="conks-live-01", maximum_cost_usd=0.06)
            with self.assertRaisesRegex(CompositionError, "provider or model differs"):
                ledger.record_observation(run_id="conks-live-01", call_index=first,
                                          state="completed", provider="other",
                                          requested_model="example-model", cost_usd=0.02)
            ledger.record_observation(run_id="conks-live-01", call_index=first,
                                      state="completed", provider="openai",
                                      requested_model="example-model", input_tokens=20,
                                      output_tokens=10, cost_usd=0.02,
                                      pricing_source="pinned-test-catalog")
            second = ledger.reserve_call(run_id="conks-live-01", maximum_cost_usd=0.08)
            ledger.record_observation(run_id="conks-live-01", call_index=second,
                                      state="failed", provider="openai",
                                      requested_model="example-model", failure_code="TIMEOUT")
            summary = ledger.summary("conks-live-01")
            self.assertEqual(summary["call_count"], 2)
            self.assertAlmostEqual(summary["charged_or_reserved_usd"], 0.10)
            with self.assertRaisesRegex(CompositionError, "cap reached"):
                ledger.reserve_call(run_id="conks-live-01", maximum_cost_usd=0.01)
            ledger.close_run("conks-live-01")

    def test_private_boundary_and_pending_receipt(self) -> None:
        outside = Path(self.temp.name) / "outside.json"
        outside.write_text("{}")
        with self.assertRaisesRegex(CompositionError, "inside the private root"):
            SQLiteExperimentLedger(outside, private_root=self.private)
        with self.open() as ledger:
            self.create_offline(ledger)
            with self.assertRaisesRegex(CompositionError, "inside the private root"):
                ledger.record_artifact(run_id="conks-offline-01", role="first_result",
                                       name="primary", path=outside)
            with self.assertRaisesRegex(CompositionError, "offline run"):
                ledger.reserve_call(run_id="conks-offline-01", maximum_cost_usd=0.01)
            ledger.create_run(run_id="pending-run", suite="of-conks-cons-v21",
                              source_manifest_sha256=HASH, frozen_gold_sha256=HASH,
                              recipe_sha256=HASH, recovery_route="pdf_text",
                              provider_exposure="approved_private_api", provider="openai",
                              model="example-model", call_cap=1, spend_cap_usd=0.01)
            ledger.reserve_call(run_id="pending-run", maximum_cost_usd=0.01)
            with self.assertRaisesRegex(CompositionError, "pending provider receipts"):
                ledger.close_run("pending-run")


if __name__ == "__main__":
    unittest.main()
