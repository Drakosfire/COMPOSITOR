"""Public, synthetic checks for bounded Composition candidate reads."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor.candidate_retrieval import retrieve_candidates
from compositor.package import CompositionError, JsonPackageStore, make_source_package


def resource(rid: str, name: str, text: str, audience: str = "GM") -> dict:
    return {"id": rid, "kind": "evidence_prose", "name": name,
            "text": text, "audience": audience,
            "origin": {"type": "source", "source_id": "sha256:synthetic",
                       "locator": f"authored-test#{rid}"}}


class CandidateRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = JsonPackageStore(Path(self.temp.name))
        a = make_source_package(self.store, package_id="alpha", title="Alpha",
                                resources={
                                    "z": resource("z", "Noke", "Noke arrives."),
                                    "a": resource("a", "Noke", "Noke arrives."),
                                    "b": resource("b", "Noke's Wand", "A strange wand."),
                                    "c": resource("c", "Encounter", "Noke returns."),
                                    "secret": resource("secret", "Noke", "GM secret"),
                                    "public": resource("public", "Noke's shop", "A public shop", "PLAYER"),
                                })
        b = make_source_package(self.store, package_id="beta", title="Beta",
                                resources={"a": resource("a", "Noke", "An alternate Noke.")})
        self.alpha = {key: a[key] for key in ("package_id", "revision")}
        self.beta = {key: b[key] for key in ("package_id", "revision")}

    def read(self, refs=None, query="Noke", audience="GM", max_hits=50,
             max_bytes=65536):
        return retrieve_candidates(self.store, [self.alpha, self.beta] if refs is None else refs,
                                   query, audience=audience, max_hits=max_hits,
                                   max_bytes=max_bytes)

    def test_rank_ties_namespace_and_exact_provenance(self) -> None:
        result = self.read(refs=[self.beta, self.alpha])
        refs = [hit["resource_ref"] for hit in result["hits"]]
        self.assertEqual([(r["package_id"], r["resource_id"]) for r in refs[:4]],
                         [("alpha", "a"), ("alpha", "z"),
                          ("beta", "a"), ("alpha", "secret")])
        self.assertEqual([h["match"]["class"] for h in result["hits"][:4]],
                         ["name_exact"] * 4)
        self.assertEqual(result["hits"][-1]["match"]["class"], "text_contains")
        self.assertTrue(all(h["resource"]["origin"]["locator"].startswith("authored-test#")
                            for h in result["hits"]))
        self.assertEqual(result["truncation"]["omitted_hits"], 0)
        self.assertEqual(result, self.read(refs=[self.alpha, self.beta]))

    def test_audience_is_filtered_before_ranking_counts_and_caps(self) -> None:
        player = self.read(audience="PLAYER", max_hits=1)
        self.assertEqual([h["resource_ref"]["resource_id"] for h in player["hits"]],
                         ["public"])
        self.assertEqual(player["truncation"]["omitted_hits"], 0)
        self.assertNotIn("secret", json.dumps(player))
        self.assertEqual(self.read(refs=[], audience="PLAYER")["hits"], [])

    def test_hard_hit_and_utf8_byte_caps_keep_whole_resources(self) -> None:
        limited = self.read(max_hits=2)
        self.assertEqual(len(limited["hits"]), 2)
        self.assertEqual(limited["truncation"], {
            "omitted_hits": 5, "hit_cap_reached": True, "byte_cap_reached": False})
        tiny = self.read(max_bytes=1024)
        self.assertTrue(tiny["truncation"]["byte_cap_reached"])
        self.assertGreater(tiny["truncation"]["omitted_hits"], 0)
        self.assertLessEqual(len(json.dumps(tiny, ensure_ascii=False, sort_keys=True,
                                            separators=(",", ":")).encode()), 1024)
        self.assertFalse(any("…" in h["resource"]["text"] for h in tiny["hits"]))

    def test_missing_exact_ref_and_no_fallback(self) -> None:
        absent = {"package_id": "alpha", "revision": "0" * 64}
        result = self.read(refs=[absent, self.beta])
        self.assertEqual(len(result["hits"]), 1)
        self.assertEqual(result["hits"][0]["resource_ref"]["package_id"], "beta")
        self.assertEqual(result["diagnostics"], [{"kind": "missing_revision", "ref": absent}])
        self.assertEqual(result["packages"][0]["state"], "missing")

    def test_invalid_inputs_fail(self) -> None:
        invalid = [
            {"refs": [self.alpha, self.alpha]},
            {"refs": [self.alpha] * 9},
            {"query": " "}, {"query": "x" * 201},
            {"audience": "invalid"},
            {"max_hits": 0}, {"max_hits": True}, {"max_hits": 51},
            {"max_bytes": 1023}, {"max_bytes": 65537},
            {"refs": [{"package_id": "bad", "revision": "wrong"}]},
        ]
        for override in invalid:
            with self.subTest(override=override), self.assertRaises(CompositionError):
                self.read(**override)
        self.assertEqual(self.read(query="absent")["hits"], [])


if __name__ == "__main__":
    unittest.main()
