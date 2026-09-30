"""Mixed-source recovery packet and explicit-review boundary."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor import CompositionError, JsonPackageStore
from compositor.asset_benchmark import build_asset_review_packet
from compositor.benchmark_review import validate_review_packet


MD_SHA = "a" * 64
PDF_SHA = "b" * 64
ASSET_SHA = "c" * 64


def image(resource_id: str, page: int, xref: int, digest: str) -> dict:
    return {"id": resource_id, "kind": "asset_reference", "name": resource_id,
            "text": "Private bytes; reference only", "audience": "GM",
            "origin": {"type": "source", "source_id": f"sha256:{PDF_SHA}",
                       "locator": f"illustrated_pdf/page-{page}#xref={xref}",
                       "printed_page": page, "pdf_page_index": page - 1,
                       "image_sha256": digest},
            "asset": {"status": "reference_only", "sha256": digest}}


def case(case_id: str, page: int, category: str) -> dict:
    return {"id": case_id, "category": category, "task": "planning", "severity": "material",
            "audience": "gm", "evidence": {"illustrated_pdf_printed_page": page},
            "expectation": f"Source asset on page {page}", "acceptable_alternatives": [],
            "forbidden_outcomes": ["Do not fabricate image bytes."]}


class AssetBenchmarkTest(unittest.TestCase):
    def test_mixed_source_candidates_stay_unjudged_and_context_is_immutable(self) -> None:
        with TemporaryDirectory() as temp:
            store = JsonPackageStore(Path(temp) / "packages")
            resources = {
                "text": {"id": "text", "kind": "evidence_prose", "name": "Text",
                         "text": "Public fixture", "audience": "GM",
                         "origin": {"type": "source", "source_id": f"sha256:{MD_SHA}",
                                    "locator": "supplied_markdown/page-1/stageB.evidence_units.json#/units/0"}},
                "regional-map": image("regional-map", 4, 31, "d" * 64),
                "village-map": image("village-map", 8, 65, "e" * 64),
            }
            package = store.save({"format_version": 1, "package_id": "public-mixed",
                                  "title": "Mixed source fixture", "form": "source",
                                  "lineage": [], "resources": resources,
                                  "relationships": [], "dependencies": [], "proposals": [],
                                  "asset_manifest_sha256": ASSET_SHA})
            gold = {"status": "frozen", "suite": "public-fixture", "case_count": 4,
                    "cases": [case("MAP-REGIONAL", 4, "asset_map"),
                              case("MAP-VILLAGE", 8, "asset_map"),
                              case("FIGURE-MISSING", 9, "asset_reference"),
                              {"id": "TEXT-ONLY", "category": "narrative"}]}
            source = {"accepted": True, "source_files": {
                "illustrated_pdf": {"sha256": PDF_SHA},
                "normalized_markdown": {"sha256": MD_SHA}}}
            assets = {"status": "reference_only", "illustrated_pdf": {"sha256": PDF_SHA},
                      "assets": [{"resource_id": "regional-map", "printed_page": 4,
                                  "pdf_page_index": 3, "xref": 31, "sha256": "d" * 64},
                                 {"resource_id": "village-map", "printed_page": 8,
                                  "pdf_page_index": 7, "xref": 65, "sha256": "e" * 64}]}

            def packet(value: dict = package) -> dict:
                return build_asset_review_packet(
                    run_id="public-asset-review", gold=gold, source_manifest=source,
                    asset_manifest=assets, package=value,
                    gold_sha256="1" * 64, source_manifest_sha256="2" * 64,
                    asset_manifest_sha256=ASSET_SHA)

            expected = packet()
            self.assertEqual(expected["status"], "unjudged")
            self.assertEqual(expected["score_basis"], "asset_recovery_only")
            self.assertEqual([item["id"] for item in expected["cases"]],
                             ["MAP-REGIONAL", "MAP-VILLAGE", "FIGURE-MISSING"])
            self.assertEqual([len(item["candidate_resources"]) for item in expected["cases"]],
                             [1, 1, 0])
            self.assertTrue(all(item["review"] is None and
                                item["semantic_competence"] == "not_assessed" and
                                item["task_competence"] == "not_assessed"
                                for item in expected["cases"]))
            with self.assertRaisesRegex(CompositionError, "partial gold adjudication"):
                validate_review_packet(expected, expected=expected, require_complete=True)
            edited = deepcopy(expected)
            for item, verdict in zip(edited["cases"], ("pass", "pass", "material_gap"), strict=True):
                item["review"] = {"verdict": verdict, "reviewer": "fixture-reviewer",
                                  "rationale": "Checked the cited public fixture source and package.",
                                  "resource_ids": [r["id"] for r in item["candidate_resources"]]}
            summary = validate_review_packet(edited, expected=expected, require_complete=True)
            self.assertEqual(summary["verdicts"], {"pass": 2, "material_gap": 1})
            changed_context = deepcopy(edited)
            changed_context["cases"][0]["candidate_resources"] = []
            with self.assertRaisesRegex(CompositionError, "context changed"):
                validate_review_packet(changed_context, expected=expected, require_complete=True)

            wrong_source = deepcopy(package)
            wrong_source["resources"]["village-map"]["origin"]["source_id"] = f"sha256:{MD_SHA}"
            with self.assertRaisesRegex(CompositionError, "asset source identity"):
                packet(wrong_source)
            wrong_locator = deepcopy(package)
            wrong_locator["resources"]["village-map"]["origin"]["locator"] = \
                "illustrated_pdf/page-9#xref=65"
            with self.assertRaisesRegex(CompositionError, "page/xref locator"):
                packet(wrong_locator)
            wrong_page_metadata = deepcopy(package)
            wrong_page_metadata["resources"]["village-map"]["origin"]["printed_page"] = 9
            with self.assertRaisesRegex(CompositionError, "page metadata"):
                packet(wrong_page_metadata)
            ref = {"package_id": package["package_id"], "revision": package["revision"]}
            path = store.path_for(**ref)
            tampered = json.loads(path.read_text())
            tampered["resources"]["text"]["text"] = "Changed after revision was saved"
            path.write_text(json.dumps(tampered))
            with self.assertRaisesRegex(CompositionError, "revision integrity mismatch"):
                store.load(ref)


if __name__ == "__main__":
    unittest.main()
