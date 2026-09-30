"""Synthetic contract checks for the caller-owned Composition active set."""

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from compositor.package import CompositionError, JsonPackageStore, make_source_package
from compositor.read_projection import project_query


def resource(text: str, audience: str, source_id: str) -> dict:
    return {"id": "shared-id", "kind": "note", "name": "Shared Name",
            "text": text, "audience": audience,
            "origin": {"type": "source", "source_id": source_id,
                       "locator": "invented:line-1"}}


class ReadProjectionTest(unittest.TestCase):
    def test_exact_selected_refs_namespaces_audience_and_changed_input_set(self) -> None:
        with TemporaryDirectory() as temp:
            store = JsonPackageStore(Path(temp))
            a = make_source_package(store, package_id="adventure-a", title="A",
                                    resources={"shared-id": resource(
                                        "Visible clue", "PLAYER", "sha256:invented-a")})
            b = make_source_package(store, package_id="adventure-b", title="B",
                                    resources={"shared-id": resource(
                                        "GM-only answer token", "GM", "sha256:invented-b")},
                                    diagnostics=[{"kind": "missing_artifact",
                                                  "resource_id": "shared-id",
                                                  "reason": "GM-only diagnostic token"}])
            a_ref = {"package_id": a["package_id"], "revision": a["revision"]}
            b_ref = {"package_id": b["package_id"], "revision": b["revision"]}

            combined = project_query(store, [b_ref, a_ref], "Shared Name", audience="GM")
            self.assertEqual([x["resource_ref"] for x in combined["hits"]], [
                {**a_ref, "resource_id": "shared-id"},
                {**b_ref, "resource_id": "shared-id"}])
            self.assertEqual([x["resource"]["origin"]["source_id"]
                              for x in combined["hits"]],
                             ["sha256:invented-a", "sha256:invented-b"])
            self.assertEqual(combined["packages"][1]["readiness"]["playing"], "limited")

            player = project_query(store, [b_ref, a_ref], "Shared Name", audience="PLAYER")
            self.assertEqual([x["resource_ref"] for x in player["hits"]],
                             [{**a_ref, "resource_id": "shared-id"}])
            self.assertNotIn("GM-only", json.dumps(player))
            self.assertEqual([x["resource_ref"] for x in project_query(
                store, [b_ref], "Shared Name", audience="GM")["hits"]],
                [{**b_ref, "resource_id": "shared-id"}])
            self.assertEqual(project_query(store, [], "Shared Name", audience="GM"),
                             {"hits": [], "packages": [], "diagnostics": []})
            self.assertEqual([x["resource_ref"] for x in project_query(
                store, [a_ref], "Shared Name", audience="GM")["hits"]],
                [{**a_ref, "resource_id": "shared-id"}])

    def test_missing_revision_is_visible_without_substituting_other_content(self) -> None:
        with TemporaryDirectory() as temp:
            store = JsonPackageStore(Path(temp))
            package = make_source_package(store, package_id="available", title="Available",
                                          resources={"shared-id": resource(
                                              "Visible clue", "PLAYER", "sha256:invented")})
            make_source_package(store, package_id="missing", title="Other revision",
                                resources={"shared-id": resource(
                                    "Substitute clue", "PLAYER", "sha256:other")})
            good = {"package_id": package["package_id"], "revision": package["revision"]}
            missing = {"package_id": "missing", "revision": "0" * 64}
            result = project_query(store, [missing, good], "Shared Name", audience="PLAYER")
            self.assertEqual([h["resource_ref"] for h in result["hits"]],
                             [{**good, "resource_id": "shared-id"}])
            self.assertEqual(result["diagnostics"], [{"kind": "missing_revision", "ref": missing}])
            self.assertEqual(result["packages"][1],
                             {"ref": missing, "state": "missing", "readiness": None})

    def test_invalid_or_ambiguous_selection_fails(self) -> None:
        with TemporaryDirectory() as temp:
            store = JsonPackageStore(Path(temp))
            ref = {"package_id": "example", "revision": "0" * 64}
            for refs in ([ref, ref], [ref, {"package_id": "example", "revision": "1" * 64}]):
                with self.assertRaisesRegex(CompositionError, "duplicate package identity"):
                    project_query(store, refs, "clue", audience="GM")
            for refs in ([{"package_id": "example"}], "example"):
                with self.assertRaises(CompositionError):
                    project_query(store, refs, "clue", audience="GM")
            with self.assertRaisesRegex(CompositionError, "audience"):
                project_query(store, [], "clue", audience="PUBLIC")
            with self.assertRaisesRegex(CompositionError, "query text"):
                project_query(store, [], "  ", audience="GM")


if __name__ == "__main__":
    unittest.main()
