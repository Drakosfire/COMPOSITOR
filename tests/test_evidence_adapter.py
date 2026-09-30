"""Offline RulesIngestion artifact-to-Composition witnesses on original material."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from compositor import (CompositionError, JsonPackageStore, derive, effective_content,
                        load_evidence_draft, save_derived)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "fixtures/public/evidence"
OWNER_REF = "17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8"
MANIFEST_HASH = {
    "pdf_text": "9bc94fa932d204dff275e6a528e7e19843873110a0783c4a1c70a2738eb1f18a",
    "supplied_markdown": "289df4b50cb59b88ef3a72846f282b33bd2c52a960e931e953694aa2f310f712",
    "rules_ingestion_ab": "f332b191ca6da05730ffbc966a98b593d450246cf03b889063c1861c41b28f6d",
}
PHRASES = (
    "A letter invites the party to inspect a noisy windmill.",
    "A gust moves a token one space.",
    "The watcher can move a token one space with Wind Step.",
    "The miller concealed a cracked gear beneath the floor.",
)


def ref(package: dict) -> dict[str, str]:
    return {"package_id": package["package_id"], "revision": package["revision"]}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class EvidenceAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = JsonPackageStore(Path(self.temp.name) / "packages")

    def test_both_routes_preserve_evidence_and_reopen_unit_locator(self) -> None:
        counts = {}
        for route in ("pdf_text", "supplied_markdown"):
            result = load_evidence_draft(
                self.store, EVIDENCE / route, project_root=ROOT,
                package_id=f"field-notes-{route}", title="North Mill Field Notes",
                expected_rules_ingestion_ref=OWNER_REF,
                expected_manifest_sha256=MANIFEST_HASH[route],
            )
            content = effective_content(self.store, ref(result.package))
            self.assertEqual(content["issues"], [])
            self.assertEqual(result.report["provider_calls"], 0)
            self.assertTrue(all(gate["passed"] for gate in result.report["gate_report"]))
            pdf_sha = digest(ROOT / "fixtures/public/windmill-field-notes.pdf")
            markdown_sha = digest(ROOT / "fixtures/public/windmill-field-notes.md")
            direct_sha = pdf_sha if route == "pdf_text" else markdown_sha
            self.assertEqual(result.report["direct_source_sha256"], direct_sha)
            self.assertEqual(result.report["source_pdf_sha256"], pdf_sha)
            self.assertEqual(result.report["supplied_markdown_sha256"],
                             markdown_sha if route == "supplied_markdown" else None)
            text = "\n".join(resource["text"] for resource in content["resources"].values())
            for phrase in PHRASES:
                self.assertIn(phrase, text)
            for resource in content["resources"].values():
                origin = resource["origin"]
                self.assertEqual(origin["source_id"], f"sha256:{direct_sha}")
                self.assertEqual(origin.get("associated_pdf_sha256"),
                                 pdf_sha if route == "supplied_markdown" else None)
                locator, pointer = origin["locator"].split("#")
                artifact = json.loads((EVIDENCE / locator).read_text(encoding="utf-8"))
                index = int(pointer.removeprefix("/units/"))
                self.assertEqual(artifact["units"][index]["text"], resource["text"])
                self.assertEqual(artifact["units"][index]["page_fingerprint"], origin["page_fingerprint"])
            counts[route] = len(content["resources"])
        self.assertEqual(counts, {"pdf_text": 6, "supplied_markdown": 4})

    def test_missing_page_asset_and_failed_gate_remain_visible_after_derived_reload(self) -> None:
        copied = Path(self.temp.name) / "bundle"
        shutil.copytree(EVIDENCE / "supplied_markdown", copied)
        manifest_path = copied / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["expected_page_indices"] = [0, 1]
        manifest["expected_assets"] = ["fixtures/public/absent-map.png"]
        manifest["known_omissions"] = [{"kind": "asset_inventory_pending",
                                        "reason": "Synthetic inventory witness"}]
        manifest_path.write_text(json.dumps(manifest))
        units_path = copied / "page-0/stageB.evidence_units.json"
        units = json.loads(units_path.read_text())
        units["gate_diagnostics"][0]["passed"] = False
        units_path.write_text(json.dumps(units))
        manifest["pages"][0]["artifact_sha256"]["stageB.evidence_units.json"] = digest(units_path)
        manifest_path.write_text(json.dumps(manifest))
        result = load_evidence_draft(
            self.store, copied, project_root=ROOT, package_id="incomplete", title="Incomplete",
            expected_rules_ingestion_ref=OWNER_REF,
            expected_manifest_sha256=digest(manifest_path),
        )
        content = effective_content(self.store, ref(result.package))
        self.assertEqual({issue["kind"] for issue in content["issues"]},
                         {"missing_page", "missing_asset", "gate_failure",
                          "asset_inventory_pending"})
        self.assertEqual(len(content["resources"]), 4)
        self.assertEqual(content["readiness"]["worldbuilding"], "limited")
        draft = derive(self.store, ref(result.package), package_id="incomplete-adapted", title="Adapted")
        saved = save_derived(self.store, draft, form="snapshot")
        reloaded = effective_content(self.store, ref(saved))
        self.assertEqual(reloaded["issues"], content["issues"])
        self.assertEqual(reloaded["resources"], content["resources"])

    def test_source_revision_mismatch_fails_before_assembly(self) -> None:
        copied = Path(self.temp.name) / "bundle"
        shutil.copytree(EVIDENCE / "pdf_text", copied)
        manifest_path = copied / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["source_pdf_sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(CompositionError, "source revision mismatch"):
            load_evidence_draft(self.store, copied, project_root=ROOT,
                                package_id="wrong-revision", title="Wrong",
                                expected_rules_ingestion_ref=OWNER_REF,
                                expected_manifest_sha256=digest(manifest_path))

    def test_rules_ingestion_contract_revision_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(CompositionError, "contract revision mismatch"):
            load_evidence_draft(self.store, EVIDENCE / "pdf_text", project_root=ROOT,
                                package_id="wrong-owner", title="Wrong",
                                expected_rules_ingestion_ref="0" * 40,
                                expected_manifest_sha256=MANIFEST_HASH["pdf_text"])

    def test_evidence_artifact_revision_mismatch_fails_closed(self) -> None:
        copied = Path(self.temp.name) / "bundle"
        shutil.copytree(EVIDENCE / "pdf_text", copied)
        surface = copied / "page-0/stageA.surface.md"
        surface.write_text(surface.read_text() + "Unreviewed addition\n")
        with self.assertRaisesRegex(CompositionError, "artifact revision mismatch"):
            load_evidence_draft(self.store, copied, project_root=ROOT,
                                package_id="changed-evidence", title="Changed",
                                expected_rules_ingestion_ref=OWNER_REF,
                                expected_manifest_sha256=MANIFEST_HASH["pdf_text"])

    def test_owner_ab_import_preserves_envelope_and_unknown_usage(self) -> None:
        bundle = EVIDENCE / "rules_ingestion_ab"
        result = load_evidence_draft(
            self.store, bundle, project_root=ROOT, package_id="owner-ab",
            title="North Mill Field Notes", expected_rules_ingestion_ref=OWNER_REF,
            expected_manifest_sha256=MANIFEST_HASH["rules_ingestion_ab"],
        )
        content = effective_content(self.store, ref(result.package))
        self.assertEqual(content["issues"], [])
        self.assertIsNone(result.report["provider_calls"])
        self.assertEqual(result.report["provider_usage"]["status"], "unknown")
        self.assertEqual(result.report["owner_recipe"]["stage"], "mark3_ab")
        self.assertEqual(result.report["direct_source_sha256"],
                         digest(ROOT / "fixtures/public/windmill-field-notes.pdf"))
        for resource in content["resources"].values():
            origin = resource["origin"]
            self.assertEqual(origin["source_id"],
                             f"sha256:{result.report['direct_source_sha256']}")
            artifact_rel, pointer = origin["locator"].split("#")
            units = json.loads((EVIDENCE / artifact_rel).read_text())["units"]
            self.assertEqual(units[int(pointer.removeprefix("/units/"))]["text"],
                             resource["text"])
        reopened = self.store.load(ref(result.package))
        self.assertEqual(reopened, result.package)

    def test_owner_ab_rejects_identity_and_unknown_usage_substitution(self) -> None:
        bundle = Path(self.temp.name) / "owner-ab"
        shutil.copytree(EVIDENCE / "rules_ingestion_ab", bundle)
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["provider_usage"]["calls"] = 0
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(CompositionError, "unknown usage"):
            load_evidence_draft(self.store, bundle, project_root=ROOT,
                                package_id="bad-usage", title="Bad",
                                expected_rules_ingestion_ref=OWNER_REF,
                                expected_manifest_sha256=digest(manifest_path))
        manifest["provider_usage"]["calls"] = None
        manifest["owner_recipe"]["model_id"] = "substituted-model"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(CompositionError, "owner Stage A/B identity mismatch"):
            load_evidence_draft(self.store, bundle, project_root=ROOT,
                                package_id="bad-model", title="Bad",
                                expected_rules_ingestion_ref=OWNER_REF,
                                expected_manifest_sha256=digest(manifest_path))
        manifest["owner_recipe"]["model_id"] = "fixture/synthetic-mark3-envelope"
        manifest["provider_usage"].update(status="known", provider="example",
                                          calls=1, spend_usd=0.01)
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(CompositionError, "provider usage receipt required"):
            load_evidence_draft(self.store, bundle, project_root=ROOT,
                                package_id="missing-receipt", title="Bad",
                                expected_rules_ingestion_ref=OWNER_REF,
                                expected_manifest_sha256=digest(manifest_path))
        receipt_path = bundle / "usage-receipt.json"
        receipt_path.write_text('{"synthetic_fixture": true}')
        manifest["provider_usage"]["receipt"] = {
            "path": receipt_path.name, "sha256": digest(receipt_path)}
        manifest_path.write_text(json.dumps(manifest))
        known = load_evidence_draft(self.store, bundle, project_root=ROOT,
                                    package_id="known-usage", title="Known",
                                    expected_rules_ingestion_ref=OWNER_REF,
                                    expected_manifest_sha256=digest(manifest_path))
        self.assertEqual(known.report["provider_calls"], 1)
        receipt_path.write_text('{"synthetic_fixture": false}')
        with self.assertRaisesRegex(CompositionError, "receipt revision mismatch"):
            load_evidence_draft(self.store, bundle, project_root=ROOT,
                                package_id="changed-receipt", title="Bad",
                                expected_rules_ingestion_ref=OWNER_REF,
                                expected_manifest_sha256=digest(manifest_path))

    def test_owner_ab_missing_and_failed_gate_stay_visible(self) -> None:
        bundle = Path(self.temp.name) / "owner-ab"
        shutil.copytree(EVIDENCE / "rules_ingestion_ab", bundle)
        page_dir = bundle / "page-0"
        (page_dir / "stageA.page.json").unlink()
        manifest_path = bundle / "manifest.json"
        missing = load_evidence_draft(self.store, bundle, project_root=ROOT,
                                      package_id="missing-envelope", title="Missing",
                                      expected_rules_ingestion_ref=OWNER_REF,
                                      expected_manifest_sha256=digest(manifest_path))
        self.assertIn("missing_artifact",
                      {item["kind"] for item in missing.report["diagnostics"]})
        self.assertEqual(missing.report["unit_count"], 0)
        shutil.copyfile(EVIDENCE / "rules_ingestion_ab/page-0/stageA.page.json",
                        page_dir / "stageA.page.json")
        gates_path = page_dir / "stageA.gate_diagnostics.json"
        gates = json.loads(gates_path.read_text())
        gates[0]["passed"] = False
        gates_path.write_text(json.dumps(gates))
        manifest = json.loads(manifest_path.read_text())
        manifest["pages"][0]["artifact_sha256"]["stageA.gate_diagnostics.json"] = digest(gates_path)
        manifest_path.write_text(json.dumps(manifest))
        failed = load_evidence_draft(self.store, bundle, project_root=ROOT,
                                     package_id="failed-gate", title="Failed",
                                     expected_rules_ingestion_ref=OWNER_REF,
                                     expected_manifest_sha256=digest(manifest_path))
        self.assertIn("gate_failure",
                      {item["kind"] for item in failed.report["diagnostics"]})


if __name__ == "__main__":
    unittest.main()
