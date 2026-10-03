import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor.adventure_candidates import (
    attribute_failure, evaluate_probe, read_pinned_units, validate_candidate_graph,
)
from compositor.package import CompositionError


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/public/adventure_graph/north-mill-candidates.json"


class AdventureCandidateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_text())
        self.units = {u["unit_id"]: {"page_index": u["page_index"], "text": u["text"]}
                      for u in self.fixture["source_units"]}
        self.graph = self.fixture["graph"]

    def test_three_edge_path_and_negative(self):
        summary = validate_candidate_graph(self.graph, self.units)
        self.assertEqual(summary["evidence_pages"], [0, 1])
        found = evaluate_probe(self.graph, {"id": "chain", "start": "courier", "steps": [
            {"kind": "same_person"}, {"kind": "conditional_gives"}, {"kind": "receives"}]})
        self.assertEqual(found["paths"][0]["nodes"], ["courier", "mira", "nar", "key"])
        self.assertEqual(attribute_failure(found, "key", source_present=True,
                         expected_node_present=True, expected_edges_present=True), "pass")
        self.assertFalse(any(p["nodes"][-1] == "gate" for p in found["paths"]))

    def test_requires_relation_evidence_and_cross_page_review(self):
        self.graph["edges"][0]["reviewed"] = False
        with self.assertRaisesRegex(CompositionError, "two pages and review"):
            validate_candidate_graph(self.graph, self.units)
        self.graph["edges"][0]["reviewed"] = True
        self.graph["edges"][1]["evidence"][0]["quote"] = "invented quote"
        with self.assertRaisesRegex(CompositionError, "quote absent"):
            validate_candidate_graph(self.graph, self.units)

    def test_endpoint_and_pinned_page_fail_closed(self):
        self.graph["edges"][0]["target"] = "unknown"
        with self.assertRaisesRegex(CompositionError, "unavailable endpoint"):
            validate_candidate_graph(self.graph, self.units)
        with TemporaryDirectory() as temp:
            p = Path(temp) / "units.json"
            p.write_text(json.dumps({"gates_passed": True, "units": [{"unit_id": "u", "text": "text"}]}))
            digest = sha256(p.read_bytes()).hexdigest()
            self.assertIn("u", read_pinned_units({0: (p, digest)}))
            with self.assertRaisesRegex(CompositionError, "revision mismatch"):
                read_pinned_units({0: (p, "0" * 64)})

    def test_failure_attribution(self):
        miss = {"paths": []}
        self.assertEqual(attribute_failure(miss, "key", source_present=False,
                         expected_node_present=False, expected_edges_present=False), "absent_source")
        self.assertEqual(attribute_failure(miss, "key", source_present=True,
                         expected_node_present=False, expected_edges_present=False), "absent_candidate")
        self.assertEqual(attribute_failure(miss, "key", source_present=True,
                         expected_node_present=True, expected_edges_present=False), "wrong_identity_or_endpoint")
        self.assertEqual(attribute_failure(miss, "key", source_present=True,
                         expected_node_present=True, expected_edges_present=True), "failed_path_selection")


if __name__ == "__main__":
    unittest.main()
