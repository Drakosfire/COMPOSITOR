"""Gold adjudication cannot silently score or substitute a source revision."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor.benchmark_review import build_review_packet, validate_review_packet
from compositor.package import CompositionError, JsonPackageStore, make_source_package


class BenchmarkReviewTest(unittest.TestCase):
    def test_packet_is_unjudged_and_requires_complete_explicit_review(self) -> None:
        with TemporaryDirectory() as temp:
            source_sha = "a" * 64
            store = JsonPackageStore(Path(temp))
            package = make_source_package(store, package_id="sample", title="Fixture", resources={
                "nar": {"id": "nar", "kind": "person", "name": "Nar", "text": "Nar has a key",
                        "audience": "GM", "origin": {"type": "source",
                        "source_id": f"sha256:{source_sha}", "locator": "printed-page:2"}},
            }, diagnostics=[{"kind": "asset_inventory_pending"}])
            gold = {"status": "frozen", "suite": "fixture", "case_count": 2, "cases": [
                {"id": "F001", "category": "person", "task": "planning", "severity": "material",
                 "expectation": "Nar has a key", "evidence": {"normalized_markdown_page_marker": 2}},
                {"id": "F002", "category": "rule", "task": "playing", "severity": "critical",
                 "expectation": "No invented rule", "evidence": {"normalized_markdown_page_marker": 3}},
            ]}
            packet = build_review_packet(run_id="run-1", gold=gold, package=package,
                                         gold_sha256="b" * 64, source_sha256=source_sha)
            self.assertEqual(packet["cases"][0]["candidate_resources"][0]["id"], "nar")
            self.assertEqual(packet["cases"][1]["candidate_resources"], [])
            self.assertEqual(packet["global_diagnostics"], [{"kind": "asset_inventory_pending"}])
            self.assertEqual(validate_review_packet(packet, expected=packet,
                                                    require_complete=False)["unreviewed"], 2)
            with self.assertRaisesRegex(CompositionError, "partial"):
                validate_review_packet(packet, expected=packet, require_complete=True)
            edited = deepcopy(packet)
            edited["cases"][0]["review"] = {"verdict": "pass", "reviewer": "parent",
                                             "rationale": "Source page 2 supports this exact key claim.",
                                             "resource_ids": ["nar"]}
            edited["cases"][1]["review"] = {"verdict": "material_gap", "reviewer": "parent",
                                             "rationale": "The package omits the needed rule reference.",
                                             "resource_ids": []}
            summary = validate_review_packet(edited, expected=packet, require_complete=True)
            self.assertEqual(summary["reviewed"], 2)
            self.assertEqual(summary["verdicts"], {"pass": 1, "material_gap": 1})
            edited["cases"][0]["expectation"] = "changed gold"
            with self.assertRaisesRegex(CompositionError, "review context changed"):
                validate_review_packet(edited, expected=packet, require_complete=True)

    def test_source_substitution_is_rejected_before_packet_creation(self) -> None:
        with TemporaryDirectory() as temp:
            store = JsonPackageStore(Path(temp))
            package = make_source_package(store, package_id="sample", title="Fixture", resources={
                "x": {"id": "x", "kind": "person", "name": "X", "text": "X",
                      "audience": "GM", "origin": {"type": "source", "source_id": f"sha256:{'c' * 64}",
                      "locator": "printed-page:2"}},
            })
            gold = {"status": "frozen", "suite": "fixture", "case_count": 0, "cases": []}
            with self.assertRaisesRegex(CompositionError, "source identity differs"):
                build_review_packet(run_id="run-1", gold=gold, package=package,
                                    gold_sha256="b" * 64, source_sha256="a" * 64)


if __name__ == "__main__":
    unittest.main()
