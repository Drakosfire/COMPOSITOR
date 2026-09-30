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


if __name__ == "__main__":
    unittest.main()
