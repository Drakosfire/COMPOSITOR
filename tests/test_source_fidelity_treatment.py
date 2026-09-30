"""Synthetic replay of exact reviewed source-text corrections."""

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor.benchmark_review import validate_review_packet
from compositor.package import (CompositionError, JsonPackageStore,
                                effective_content, make_source_package)
from compositor.source_fidelity_treatment import (apply_reviewed_text_corrections,
                                                   build_correction_review_packet)


class SourceFidelityTreatmentTest(unittest.TestCase):
    def test_exact_correction_preserves_first_package_and_reopens_review(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "invented.pdf"
            source.write_bytes(b"invented source page for a synthetic OCR correction")
            source_sha = sha256(source.read_bytes()).hexdigest()
            source_store = JsonPackageStore(root / "first")
            output_store = JsonPackageStore(root / "treated")
            def item(rid: str, text: str) -> dict:
                return {"id": rid, "kind": "evidence_prose", "name": rid,
                        "text": text, "audience": "GM",
                        "origin": {"type": "source", "source_id": f"sha256:{source_sha}",
                                   "page_index": 2,
                                   "locator": f"synthetic/page-2#/units/{rid}"}}
            first = make_source_package(source_store, package_id="first", title="First",
                                        resources={"wrong": item("wrong", "Huqe creature"),
                                                   "stable": item("stable", "Unaffected fact")})
            first_ref = {"package_id": first["package_id"], "revision": first["revision"]}
            correction = {"resource_id": "wrong", "expected_text": "Huqe creature",
                          "replacement_text": "Huge creature", "page_index": 2,
                          "printed_page": 4, "locator": "synthetic/page-2#/units/wrong",
                          "rendered_page_sha256": "a" * 64, "reviewer": "source reviewer",
                          "rationale": "Rendered source spells the size word Huge."}
            treated = apply_reviewed_text_corrections(
                source_store=source_store, output_store=output_store,
                base_ref=first_ref, package_id="reviewed", title="Reviewed",
                source_path=source, source_sha256=source_sha,
                corrections=[correction])
            treated_ref = {"package_id": treated["package_id"],
                           "revision": treated["revision"]}
            self.assertEqual(source_store.load(first_ref), first)
            self.assertEqual(output_store.load(treated_ref), treated)
            self.assertEqual(effective_content(output_store, treated_ref)["resources"]["wrong"]["text"],
                             "Huge creature")
            self.assertEqual(treated["resources"]["stable"], first["resources"]["stable"])
            self.assertEqual(treated["lineage"], [first_ref])
            self.assertEqual(treated["resources"]["wrong"]["origin"]["derived_from"]["resource_id"],
                             "wrong")
            self.assertEqual(treated["resources"]["wrong"]["origin"]["source_review"]["source_pdf_sha256"],
                             source_sha)

            baseline_packet = {"package_ref": first_ref,
                               "available_resource_ids": sorted(first["resources"]),
                               "cases": [{"id": "C1", "task": "playing", "severity": "material",
                                          "candidate_resources": list(first["resources"].values()),
                                          "review": {"verdict": "material_gap",
                                                     "reviewer": "earlier reviewer",
                                                     "rationale": "The uncorrected OCR text is wrong.",
                                                     "resource_ids": ["wrong"]}}],
                               "context_sha256": "old"}
            packet = build_correction_review_packet(
                baseline_packet=baseline_packet, baseline=first, treated=treated,
                changed_resource_ids=["wrong"])
            self.assertIsNone(packet["cases"][0]["review"])
            self.assertEqual(packet["cases"][0]["candidate_resources"][0]["text"],
                             "Huge creature")
            self.assertEqual(validate_review_packet(packet, expected=packet,
                                                    require_complete=False)["unreviewed"], 1)
            self.assertNotEqual(packet["context_sha256"], "old")

    def test_mismatched_source_text_and_locator_fail_closed(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "invented.pdf"
            source.write_bytes(b"invented source")
            digest = sha256(source.read_bytes()).hexdigest()
            store = JsonPackageStore(root / "first")
            first = make_source_package(store, package_id="first", title="First", resources={
                "one": {"id": "one", "kind": "evidence_prose", "name": "One",
                        "text": "wrong", "audience": "GM",
                        "origin": {"type": "source", "source_id": f"sha256:{digest}",
                                   "page_index": 0, "locator": "page-0/one"}}})
            ref = {"package_id": first["package_id"], "revision": first["revision"]}
            valid = {"resource_id": "one", "expected_text": "wrong",
                     "replacement_text": "right", "page_index": 0,
                     "printed_page": 1, "locator": "page-0/one",
                     "rendered_page_sha256": "b" * 64, "reviewer": "reviewer",
                     "rationale": "The source image visibly has right."}
            for change, error in [({"expected_text": "different"}, "correction text"),
                                  ({"locator": "other"}, "source locator")]:
                with self.assertRaisesRegex(CompositionError, error):
                    apply_reviewed_text_corrections(
                        source_store=store, output_store=JsonPackageStore(root / error),
                        base_ref=ref, package_id="treated", title="Treated",
                        source_path=source, source_sha256=digest,
                        corrections=[{**valid, **change}])
            with self.assertRaisesRegex(CompositionError, "source revision"):
                apply_reviewed_text_corrections(
                    source_store=store, output_store=JsonPackageStore(root / "bad-source"),
                    base_ref=ref, package_id="treated", title="Treated",
                    source_path=source, source_sha256="0" * 64,
                    corrections=[valid])


if __name__ == "__main__":
    unittest.main()
