"""Synthetic PDF witness for gold-blind, attributed source decisions."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

try:
    import fitz
except ImportError:
    fitz = None

from compositor import CompositionError, JsonPackageStore, make_source_package
from compositor.benchmark_review import validate_review_packet
from compositor.reviewed_source_decisions import (
    apply_reviewed_source_decisions, build_treatment_review_packet,
    discover_source_decisions,
)


@unittest.skipUnless(fitz is not None, "PyMuPDF required for source-quote verification")
class ReviewedSourceDecisionsTest(unittest.TestCase):
    def test_gold_blind_discovery_review_and_additive_package(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            pdf = root / "source.pdf"
            lines = [
                "The fox introduces itself as Mira Hollow, a mage in need of aid.",
                "If the ritual fails, Mira dies permanently.",
                "If they fail by five or less, the spell transforms the target into stone.",
                "Each time a charge is used the user must pass a check.",
                "If they fail by more than five, deal damage for each charge remaining.",
            ]
            document = fitz.open()
            page = document.new_page(width=1200, height=600)
            page.insert_text((50, 50), "\n".join(lines), fontsize=12)
            document.save(pdf)
            document.close()
            pdf_sha = sha256(pdf.read_bytes()).hexdigest()
            resources = {}
            for index, line in enumerate(lines):
                rid = f"line-{index}"
                resources[rid] = {"id": rid, "kind": "evidence_prose", "name": rid,
                    "text": line, "audience": "GM",
                    "origin": {"type": "source", "source_id": f"sha256:{pdf_sha}",
                               "locator": f"pdf/page-1#line-{index}", "page_index": 0}}
            base_store = JsonPackageStore(root / "base")
            base = make_source_package(base_store, package_id="fixture-base",
                                       title="Invented fixture", resources=resources)
            candidates = discover_source_decisions(
                package=base, pdf_path=pdf, expected_pdf_sha256=pdf_sha)
            self.assertEqual(candidates["scanned_resources"], 5)
            self.assertEqual({item["kind"] for item in candidates["candidates"]},
                             {"identity_form", "outcome_tension", "charge_timing"})
            with fitz.open(pdf) as source:
                text = " ".join(source[0].get_text("text").split())
            for candidate in candidates["candidates"]:
                for evidence in candidate["evidence"]:
                    self.assertIn(evidence["source_quote"], text)
                    self.assertIn(evidence["resource_id"], resources)

            context_sha = sha256(json.dumps(candidates, sort_keys=True,
                ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            decisions = {"candidate_context_sha256": context_sha, "review_authority": "agent",
                "reviews": [{"candidate_id": item["id"],
                             "choice": {"identity_form": "accept_identity_form",
                                        "outcome_tension": "record_attributed_tension",
                                        "charge_timing": "record_unresolved_timing"}[item["kind"]],
                             "reviewer": "fixture agent", "rationale":
                             "The source page supports this typed review decision."}
                            for item in candidates["candidates"]]}
            output_store = JsonPackageStore(root / "treated")

            def apply(value: dict = decisions, *, package_id: str = "fixture-treated") -> dict:
                return apply_reviewed_source_decisions(
                    base=base, candidates=candidates, decisions=value,
                    pdf_path=pdf, expected_pdf_sha256=pdf_sha,
                    output_store=output_store, package_id=package_id)

            treated = apply()
            ref = {"package_id": treated["package_id"], "revision": treated["revision"]}
            self.assertEqual(output_store.load(ref), treated)
            self.assertEqual(treated["lineage"], [{"package_id": base["package_id"],
                                                   "revision": base["revision"]}])
            self.assertEqual(treated["review_authority"], "agent")
            self.assertEqual(treated["promotion_state"], "provisional_pending_independent_review")
            self.assertEqual({rid: treated["resources"][rid] for rid in resources}, resources)
            identity = [r for r in treated["resources"].values()
                        if r["kind"] == "character_identity"]
            self.assertEqual(len(identity), 1)
            self.assertEqual(identity[0]["name"], "Mira Hollow")
            self.assertEqual(identity[0]["form_state"]["current_form"], "fox")
            self.assertEqual({r["kind"] for r in treated["relationships"]},
                             {"evidence_for_identity", "source_outcome_tension",
                              "source_charge_timing_ambiguity"})
            self.assertEqual(sum(d["kind"] == "interpretation_pending"
                                 for d in treated["diagnostics"]), 2)

            expected = {"review_package_ref": {"package_id": base["package_id"],
                                               "revision": base["revision"]},
                "source_pdf_sha256": pdf_sha,
                "available_resource_ids": sorted(base["resources"]),
                "cases": [{"id": "fixture-case", "evidence": {"pdf_page_1_based": 1},
                           "candidate_text_resources": list(base["resources"].values()),
                           "candidate_asset_references": [],
                           "candidate_resource_ids": list(base["resources"]),
                           "review": None}],
                "integration_cases": [{"id": "fixture-integration",
                                       "execution_state": "unexecuted"}]}
            packet = build_treatment_review_packet(expected=expected,
                                                   baseline=base, treated=treated)
            self.assertIsNone(packet["cases"][0]["review"])
            self.assertEqual(packet["integration_cases"], expected["integration_cases"])
            self.assertIn(identity[0]["id"], packet["cases"][0]["candidate_resource_ids"])
            reviewed = deepcopy(packet)
            reviewed["cases"][0]["review"] = {"verdict": "pass",
                "reviewer": "fixture agent", "rationale": "Checked the invented source page.",
                "resource_ids": [identity[0]["id"]]}
            self.assertEqual(validate_review_packet(reviewed, expected=packet,
                                                    require_complete=True)["reviewed"], 1)

            changed = deepcopy(candidates)
            changed["candidates"][0]["evidence"][0]["source_quote"] = "invented quote"
            with self.assertRaisesRegex(CompositionError, "candidate context changed"):
                apply_reviewed_source_decisions(base=base, candidates=changed,
                    decisions=decisions, pdf_path=pdf, expected_pdf_sha256=pdf_sha,
                    output_store=output_store, package_id="changed")
            fabricated = deepcopy(base)
            fabricated["resources"]["line-0"]["text"] = (
                "The badger introduces itself as Violet Meadow, a mage in need of aid.")
            with self.assertRaisesRegex(CompositionError, "substantial exact PDF quote"):
                discover_source_decisions(package=fabricated, pdf_path=pdf,
                                          expected_pdf_sha256=pdf_sha)
            duplicate = deepcopy(decisions)
            duplicate["reviews"][1]["candidate_id"] = duplicate["reviews"][0]["candidate_id"]
            with self.assertRaisesRegex(CompositionError, "duplicate decision"):
                apply(duplicate, package_id="duplicate")
            unreviewed = deepcopy(decisions)
            unreviewed["reviews"][0]["reviewer"] = ""
            with self.assertRaisesRegex(CompositionError, "reviewer and rationale"):
                apply(unreviewed, package_id="no-reviewer")
            no_authority = deepcopy(decisions)
            del no_authority["review_authority"]
            with self.assertRaisesRegex(CompositionError, "review authority"):
                apply(no_authority, package_id="no-authority")
            pdf.write_bytes(b"changed PDF")
            with self.assertRaisesRegex(CompositionError, "source PDF revision mismatch"):
                apply(decisions, package_id="bad-source")


if __name__ == "__main__":
    unittest.main()
