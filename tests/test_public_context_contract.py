"""Public fixture witness for exact selection and provisional owner inputs."""

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor import (CompositionError, JsonPackageStore, load_evidence_draft,
                        make_source_package)
from compositor.owner_input_proposal import propose_owner_inputs
from compositor.workspace_selection import WorkspaceSelection


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "fixtures/public/evidence/supplied_markdown"
MANIFEST_SHA = "289df4b50cb59b88ef3a72846f282b33bd2c52a960e931e953694aa2f310f712"
OWNER_REF = "17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8"


class PublicContextContractTest(unittest.TestCase):
    def test_select_scope_unload_and_owner_proposal_without_world_write(self) -> None:
        with TemporaryDirectory() as temp:
            store = JsonPackageStore(Path(temp) / "packages")
            evidence = load_evidence_draft(
                store, EVIDENCE, project_root=ROOT, package_id="windmill-evidence",
                title="North Mill Field Notes", expected_rules_ingestion_ref=OWNER_REF,
                expected_manifest_sha256=MANIFEST_SHA)
            first = {"package_id": evidence.package["package_id"],
                     "revision": evidence.package["revision"]}
            second_package = make_source_package(store, package_id="windmill-authored",
                                                 title="Second Windmill", resources={
                "same-name": {"id": "same-name", "kind": "procedure", "name": "Wind Step",
                              "text": "A separate author imagines Wind Step.", "audience": "PLAYER",
                              "origin": {"type": "authored", "reason": "public scope witness"}},
                "secret": {"id": "secret", "kind": "note", "name": "Hidden Wind Step",
                           "text": "GM-only second-package note.", "audience": "GM",
                           "origin": {"type": "authored", "reason": "audience witness"}},
            })
            second = {"package_id": second_package["package_id"],
                      "revision": second_package["revision"]}
            world_state = {"revision": "unchanged", "published_items": []}
            workspace = WorkspaceSelection(store)
            workspace.select(first)
            workspace.select(second)
            with self.assertRaisesRegex(CompositionError, "unload active package revision"):
                workspace.select({"package_id": first["package_id"], "revision": "0" * 64})
            self.assertEqual(len(workspace.query("Wind Step", audience="GM")), 4)
            self.assertEqual({hit["package_id"] for hit in workspace.query("Wind Step", audience="GM")
                              if hit["resource"]["name"].endswith("Wind Step")},
                             {"windmill-evidence", "windmill-authored"})
            self.assertEqual({hit["package_id"] for hit in workspace.query(
                "Wind Step", audience="GM", package_ids=["windmill-evidence"])},
                {"windmill-evidence"})
            self.assertEqual({hit["package_id"] for hit in workspace.query(
                "Wind Step", audience="PLAYER")}, {"windmill-authored"})
            self.assertEqual([hit["resource"]["id"] for hit in workspace.query(
                "GM-only", audience="PLAYER")], [])
            with self.assertRaisesRegex(CompositionError, "inactive"):
                workspace.query("Wind Step", audience="GM", package_ids=["not-selected"])

            resource_id = next(rid for rid, resource in evidence.package["resources"].items()
                               if resource["name"].endswith("Mill Watcher"))
            source_body = (ROOT / "fixtures/public/windmill-field-notes.md").read_bytes()
            excerpt = "The watcher can move a token one space with Wind Step."
            proposal = propose_owner_inputs(store, package_ref=first, resource_id=resource_id,
                                            source_body=source_body, evidence_excerpt=excerpt)
            self.assertEqual(proposal["package_ref"], first)
            self.assertEqual(proposal["package_issues"], [])
            self.assertEqual(proposal["source"]["content_sha256"], sha256(source_body).hexdigest())
            span = proposal["dungeonmind_native_text_admission"]["spans"][0]
            self.assertEqual(source_body[span["start_byte"]:span["end_byte"]], excerpt.encode())
            self.assertIsNone(proposal["dungeonmind_native_text_admission"]["returned_evidence_ref_id"])
            self.assertIsNone(proposal["worldkeeper_prepare_prerequisites"]["space_id"])
            with self.assertRaisesRegex(CompositionError, "source body differs"):
                propose_owner_inputs(store, package_ref=first, resource_id=resource_id,
                                     source_body=source_body + b"x", evidence_excerpt=excerpt)

            workspace.unload(first)
            self.assertEqual({hit["package_id"] for hit in workspace.query(
                "Wind Step", audience="GM")}, {"windmill-authored"})
            with self.assertRaisesRegex(CompositionError, "not selected"):
                workspace.unload(first)
            workspace.select(first)
            self.assertIn("windmill-evidence", {hit["package_id"] for hit in workspace.query(
                "Wind Step", audience="GM")})
            self.assertEqual(world_state, {"revision": "unchanged", "published_items": []})
            workspace.unload(first)
            workspace.unload(second)
            with self.assertRaisesRegex(CompositionError, "no active package"):
                workspace.query("Wind Step", audience="GM")


if __name__ == "__main__":
    unittest.main()
