"""Synthetic PDF and asset replay for the unjudged package review packet."""

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
from compositor.asset_inventory import project_asset_references
from compositor.benchmark_review import validate_review_packet
from compositor.package_review_packet import build_package_review_packet


def save(path: Path, value: dict) -> str:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(fitz is not None, "PyMuPDF required for PDF review packet")
class PackageReviewPacketTest(unittest.TestCase):
    def test_pinned_source_package_and_asset_review_context(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            pdf = root / "source.pdf"
            pixels = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10), False)
            pixels.clear_with(255)
            document = fitz.open()
            page = document.new_page(width=100, height=100)
            page.insert_image(fitz.Rect(10, 20, 40, 50), stream=pixels.tobytes("jpg"))
            document.save(pdf)
            document.close()
            pdf_sha = sha256(pdf.read_bytes()).hexdigest()
            with fitz.open(pdf) as document:
                occurrence = document[0].get_image_info(xrefs=True)[0]
                extracted = document.extract_image(occurrence["xref"])
            image = root / "figure.jpeg"
            image.write_bytes(extracted["image"])
            base_store = JsonPackageStore(root / "base")
            base = make_source_package(base_store, package_id="synthetic-base",
                title="Synthetic source", resources={"note": {
                    "id": "note", "kind": "note", "name": "Synthetic note",
                    "text": "An invented fact for the fixture.", "audience": "GM",
                    "origin": {"type": "source", "source_id": f"sha256:{pdf_sha}",
                               "page_index": 0, "locator": "synthetic/page-0"}}})
            base_ref = {"package_id": base["package_id"], "revision": base["revision"]}
            asset_manifest_path = root / "asset-manifest.json"
            asset_manifest = {"format_version": 1, "status": "reference_only",
                "base_package_ref": base_ref,
                "illustrated_pdf": {"path": str(pdf), "sha256": pdf_sha},
                "assets": [{"resource_id": "figure", "name": "Synthetic figure",
                            "audience": "GM", "audience_review": "gm_only",
                            "mime_type": "image/jpeg", "status": "reference_only",
                            "printed_page": 1, "pdf_page_index": 0,
                            "xref": occurrence["xref"], "private_file": "figure.jpeg",
                            "sha256": sha256(image.read_bytes()).hexdigest(),
                            "width": extracted["width"], "height": extracted["height"],
                            "bbox_pdf_points": list(occurrence["bbox"])}]}
            asset_sha = save(asset_manifest_path, asset_manifest)
            asset_store = JsonPackageStore(root / "assets")
            derived = project_asset_references(
                base_store=base_store, base_ref=base_ref, output_store=asset_store,
                package_id="synthetic-assets", manifest_path=asset_manifest_path,
                expected_manifest_sha256=asset_sha, private_root=root)
            asset_ref = {"package_id": derived["package_id"], "revision": derived["revision"]}

            suite = "synthetic-pdf"
            owner_ref = "a" * 40
            owner_receipt = "b" * 64
            source_path = root / "source-manifest.json"
            source_sha = save(source_path, {"suite": suite, "pdf": {
                "path": str(pdf), "sha256": pdf_sha, "pages": 1}})
            first_path = root / "first-result.json"
            first_sha = save(first_path, {"suite": suite,
                "status": "first_result_frozen_unscored", "gold_consulted": False,
                "source_manifest_sha256": source_sha, "source_pdf_sha256": pdf_sha,
                "owner_ref": owner_ref, "owner_receipt_sha256": owner_receipt,
                "page_indices": [0], "provider_calls": 0,
                "provider_spend_usd": 0, "local_model_invocations": 1,
                "model": "synthetic-local", "dpi": 100, "prompt": "fixture prompt"})
            evidence_path = root / "evidence-manifest.json"
            evidence_sha = save(evidence_path, {
                "source_manifest_sha256": source_sha, "source_pdf_sha256": pdf_sha,
                "rules_ingestion_ref": owner_ref,
                "owner_output_receipt_sha256": owner_receipt,
                "expected_page_indices": [0],
                "owner_recipe": {"model_id": "synthetic-local", "dpi": 100,
                                 "prompt": "fixture prompt"},
                "provider_usage": {"calls": 0, "spend_usd": 0,
                                   "local_model_invocations": 1}})
            assembly_path = root / "assembly-manifest.json"
            assembly_sha = save(assembly_path, {
                "first_result_sha256": first_sha,
                "evidence_manifest_sha256": evidence_sha,
                "package_ref": base_ref, "resource_count": 1,
                "provider_calls": 0})
            gold_path = root / "proposal.json"
            gold_sha = save(gold_path, {"suite": suite, "status": "frozen",
                "source_manifest_sha256": source_sha, "source_pdf_sha256": pdf_sha,
                "case_count": 2, "cases": [
                    {"id": "S-1", "denominator_group": "source_fidelity",
                     "category": "asset", "task": "Planning", "severity": "material",
                     "audience": "GM", "expectation_origin": "source",
                     "expectation": "The image remains available as a private reference.",
                     "acceptable_alternatives": [], "forbidden_outcomes": [],
                     "rationale": "Invented fixture case.", "query_scope": "source",
                     "evidence": {"pdf_page_1_based": 1, "locator": "page 1"}},
                    {"id": "I-1", "denominator_group": "integration_contract",
                     "category": "scope", "task": "Playing", "severity": "critical",
                     "audience": "PLAYER", "expectation_origin": "evaluator",
                     "expectation": "The owner scope should be checked later.",
                     "acceptable_alternatives": [], "forbidden_outcomes": [],
                     "rationale": "Invented fixture contract.", "query_scope": "active",
                     "evidence": {"pdf_page_1_based": 1, "locator": "page 1"}},
                ]})
            freeze_path = root / "freeze.json"
            freeze_sha = save(freeze_path, {"suite": suite, "status": "frozen",
                "source_manifest_sha256": source_sha, "source_pdf_sha256": pdf_sha,
                "case_count": 2, "denominators": {
                    "source_fidelity": 1, "integration_contract": 1},
                "files": {"proposal.json": {"sha256": gold_sha}}})
            kwargs = dict(first_result_path=first_path, first_result_sha256=first_sha,
                source_manifest_path=source_path, source_manifest_sha256=source_sha,
                evidence_manifest_path=evidence_path, evidence_manifest_sha256=evidence_sha,
                assembly_manifest_path=assembly_path, assembly_manifest_sha256=assembly_sha,
                base_store=base_store, base_ref=base_ref,
                gold_path=gold_path, gold_sha256=gold_sha,
                freeze_record_path=freeze_path, freeze_record_sha256=freeze_sha,
                asset_store=asset_store, asset_ref=asset_ref,
                asset_manifest_path=asset_manifest_path,
                asset_manifest_sha256=asset_sha, private_root=root)
            packet = build_package_review_packet(**kwargs)
            base_only = {key: value for key, value in kwargs.items() if key not in {
                "asset_store", "asset_ref", "asset_manifest_path",
                "asset_manifest_sha256", "private_root"}}
            base_packet = build_package_review_packet(**base_only)
            self.assertEqual(base_packet["review_package_ref"], base_ref)
            self.assertEqual(base_packet["cases"][0]["candidate_asset_references"], [])
            self.assertEqual(packet["denominators"], {
                "source_fidelity": 1, "integration_contract": 1})
            self.assertEqual([r["id"] for r in packet["cases"][0]["candidate_text_resources"]],
                             ["note"])
            self.assertEqual([r["id"] for r in packet["cases"][0]["candidate_asset_references"]],
                             ["figure"])
            self.assertIsNone(packet["cases"][0]["review"])
            self.assertEqual(packet["integration_cases"][0]["execution_state"], "unexecuted")
            edited = deepcopy(packet)
            edited["cases"][0]["review"] = {"verdict": "unresolved", "reviewer": "fixture",
                "rationale": "A source reference cannot prove consumer task success.",
                "resource_ids": ["note", "figure"]}
            self.assertEqual(validate_review_packet(edited, expected=packet,
                                                    require_complete=True)["reviewed"], 1)
            edited["integration_cases"][0]["execution_state"] = "passed"
            with self.assertRaisesRegex(CompositionError, "pins or resource index changed"):
                validate_review_packet(edited, expected=packet, require_complete=True)

            image.write_bytes(b"changed bytes")
            with self.assertRaisesRegex(CompositionError, "asset byte revision mismatch"):
                build_package_review_packet(**kwargs)
            image.write_bytes(extracted["image"])
            changed = deepcopy(asset_manifest)
            changed["assets"][0]["xref"] += 1
            save(asset_manifest_path, changed)
            with self.assertRaisesRegex(CompositionError, "asset manifest revision mismatch"):
                build_package_review_packet(**kwargs)
            save(asset_manifest_path, asset_manifest)
            kwargs["assembly_manifest_sha256"] = "0" * 64
            with self.assertRaisesRegex(CompositionError, "assembly manifest revision mismatch"):
                build_package_review_packet(**kwargs)


if __name__ == "__main__":
    unittest.main()
