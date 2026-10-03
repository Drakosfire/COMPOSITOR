import json
from pathlib import Path
import unittest

from compositor.package import CompositionError
from compositor.relation_observation import canonical_json_hash, observe_units, probe_paths


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/public/adventure_graph/conditional-disclosure.json"


class RelationObservationTests(unittest.TestCase):
    def setUp(self):
        self.units = json.loads(FIXTURE.read_text())["units"]

    def test_discovers_lexical_candidates_and_preserves_unsupported(self):
        result = observe_units(self.units)
        self.assertEqual(result["units_seen"], 3)
        self.assertEqual([o["kind"] for o in result["observations"]],
                         ["conditional", "self_identity", "request", "transfer"])
        self.assertGreaterEqual(len(result["unsupported"]), 1)
        self.assertTrue(all(o["support_state"] == "lexical_candidate_only" for o in result["observations"]))
        self.assertEqual(result["observations"][0]["modality"], "conditional")
        self.assertEqual(result["observations"][-1]["subject"]["state"], "unresolved")
        self.assertEqual(canonical_json_hash(result), canonical_json_hash(json.loads(json.dumps(result))))

    def test_endpoints_and_path_are_separate(self):
        result = observe_units(self.units)
        paths = probe_paths(result)
        self.assertEqual(paths["bound_edges"], 3)
        self.assertEqual(len(paths["unresolved_observations"]), 1)
        self.assertEqual(paths["paths"], [])

    def test_fail_closed_on_bad_units_and_caps(self):
        with self.assertRaisesRegex(CompositionError, "invalid observation source unit"):
            observe_units([self.units[0], self.units[0]])
        with self.assertRaisesRegex(CompositionError, "observation bounds"):
            observe_units(self.units, max_units=2)
        with self.assertRaisesRegex(CompositionError, "path bounds"):
            probe_paths({"observations": []}, max_edges=0)


if __name__ == "__main__":
    unittest.main()
