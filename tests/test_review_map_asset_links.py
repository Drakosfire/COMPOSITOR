"""Synthetic source and map bytes for attributed asset links."""

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
from compositor.review_map_asset_links import (
    apply_reviewed_map_asset_links, build_map_treatment_packet,
    prepare_map_asset_review,
)


def digest(value: dict) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode()).hexdigest()


@unittest.skipUnless(fitz is not None, "PyMuPDF required for PDF quote verification")
class ReviewMapAssetLinksTest(unittest.TestCase):
    def test_pinned_review_and_additive_package(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            pdf = root / "invented.pdf"
            document = fitz.open()
            page = document.new_page()
            page.insert_text((40, 60), "The round garden deck joins the enclosed hall.")
            page.insert_text((40, 80), "A distant tower hides beyond the river.")
            document.save(pdf)
            document.close()
            pdf_sha = sha256(pdf.read_bytes()).hexdigest()
            image = root / "invented.jpeg"
            image.write_bytes(b"invented private fixture image")
            image_sha = sha256(image.read_bytes()).hexdigest()
            source_id = f"sha256:{pdf_sha}"
            resources = {
                "map": {"id": "map", "kind": "asset_reference", "name": "Invented map",
                    "text": "Private GM image", "audience": "GM",
                    "origin": {"type": "source", "source_id": source_id,
                               "locator": "pdf/page-1#image", "pdf_page_index": 0,
                               "image_sha256": image_sha},
                    "asset": {"sha256": image_sha, "status": "reference_only",
                              "audience_review": "gm_only"}},
                "garden": {"id": "garden", "kind": "evidence_prose",
                    "name": "Invented garden", "text": "The round garden deck joins the enclosed hall.",
                    "audience": "GM", "origin": {"type": "source",
                    "source_id": source_id, "locator": "pdf/page-1#text", "page_index": 0}},
            }
            base = make_source_package(JsonPackageStore(root / "base"),
                package_id="invented-base", title="Invented fixture", resources=resources)
            context = prepare_map_asset_review(base=base, pdf_path=pdf,
                expected_pdf_sha256=pdf_sha, asset_paths={"map": image})
            self.assertEqual(context["assets"][0]["candidate_text_resource_ids"], ["garden"])
            decision = {"context_sha256": digest(context), "review_authority": "agent",
                "reviews": [{"asset_id": "map", "target_id": "garden", "place_label": "garden",
                    "choice": "link", "reviewer": "fixture reviewer",
                    "rationale": "The round planted deck is visible beside the hall.",
                    "visual_basis": "A circular deck with planted areas is visible.",
                    "source_quote": "The round garden deck joins the enclosed hall.",
                    "pdf_quote": "The round garden deck joins the enclosed hall."}]}
            store = JsonPackageStore(root / "treated")

            def apply(value: dict = decision, *, package_id: str = "treated") -> dict:
                return apply_reviewed_map_asset_links(base=base, context=context,
                    decisions=value, pdf_path=pdf, expected_pdf_sha256=pdf_sha,
                    asset_paths={"map": image}, output_store=store, package_id=package_id)

            treated = apply()
            self.assertEqual(store.load({key: treated[key]
                                         for key in ("package_id", "revision")}), treated)
            self.assertEqual(treated["resources"], base["resources"])
            self.assertEqual(treated["lineage"], [{key: base[key]
                                                    for key in ("package_id", "revision")}])
            self.assertEqual(treated["promotion_state"],
                             "provisional_pending_independent_review")
            relation = treated["relationships"][0]
            self.assertEqual((relation["source_id"], relation["target_id"]),
                             ("map", "garden"))
            self.assertEqual(relation["audience"], "GM")
            self.assertNotIn("geometry", relation)

            expected = {"review_package_ref": {key: base[key]
                                                for key in ("package_id", "revision")},
                "source_pdf_sha256": pdf_sha, "available_resource_ids": sorted(resources),
                "cases": [{"id": "fixture-map", "evidence": {"pdf_page_1_based": 1},
                           "candidate_text_resources": [], "candidate_asset_references": [],
                           "candidate_resource_ids": [], "review": None}],
                "integration_cases": [{"id": "fixture-integration",
                                       "execution_state": "unexecuted"}]}
            packet = build_map_treatment_packet(expected=expected, baseline=base,
                                                treated=treated)
            self.assertIsNone(packet["cases"][0]["review"])
            self.assertEqual(packet["cases"][0]["candidate_map_relationships"], [relation])
            reviewed = deepcopy(packet)
            reviewed["cases"][0]["review"] = {"verdict": "pass",
                "reviewer": "fixture reviewer", "rationale": "PDF and image checked.",
                "resource_ids": ["map", "garden"]}
            self.assertEqual(validate_review_packet(reviewed, expected=packet,
                                                    require_complete=True)["reviewed"], 1)

            tampered = deepcopy(base)
            tampered["resources"]["garden"]["text"] = "Changed"
            with self.assertRaisesRegex(CompositionError, "revision integrity"):
                prepare_map_asset_review(base=tampered, pdf_path=pdf,
                    expected_pdf_sha256=pdf_sha, asset_paths={"map": image})
            bad_target = deepcopy(decision)
            bad_target["reviews"][0]["target_id"] = "missing"
            with self.assertRaisesRegex(CompositionError, "target outside"):
                apply(bad_target, package_id="bad-target")
            bad_quote = deepcopy(decision)
            bad_quote["reviews"][0]["pdf_quote"] = "Invented scene detail"
            with self.assertRaisesRegex(CompositionError, "quote absent"):
                apply(bad_quote, package_id="bad-quote")
            unrelated = deepcopy(decision)
            unrelated["reviews"][0]["pdf_quote"] = "A distant tower hides beyond the river."
            with self.assertRaisesRegex(CompositionError, "quote absent"):
                apply(unrelated, package_id="unrelated-quote")
            unresolved = deepcopy(decision)
            unresolved["reviews"][0]["choice"] = "unresolved"
            result = apply(unresolved, package_id="unresolved")
            self.assertFalse(result["relationships"])
            self.assertEqual(result["diagnostics"][0]["detail_kind"],
                             "map_place_link_unresolved")
            image.write_bytes(b"mutated")
            with self.assertRaisesRegex(CompositionError, "image bytes mismatch"):
                apply(package_id="bad-image")


if __name__ == "__main__":
    unittest.main()
