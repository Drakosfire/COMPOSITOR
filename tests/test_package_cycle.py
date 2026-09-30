"""Contract witnesses for the first public, project-authored Composition cycle."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor import (
    CompositionError, JsonPackageStore, accept_impact, derive, edit_resource,
    effective_content, make_source_package, query, resolve_rule,
    save_derived, select_dependency,
)


FIXTURE = json.loads((Path(__file__).parents[1] / "fixtures/public/package-cycle.json").read_text())


def ref(package: dict) -> dict[str, str]:
    return {"package_id": package["package_id"], "revision": package["revision"]}


class PackageCycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = JsonPackageStore(Path(self.temp.name))
        self.source = make_source_package(
            self.store, package_id=FIXTURE["source_package_id"], title="Windmill adventure",
            resources=FIXTURE["source_resources"],
            relationships=FIXTURE["source_relationships"],
        )

    def test_draft_rule_edit_review_both_save_forms_and_reload(self) -> None:
        draft = derive(self.store, ref(self.source), package_id="eldyrwild-windmill", title="Eldyrwild windmill")
        proposals = edit_resource(draft, FIXTURE["amended_rule"],
                                  candidates={"watcher": FIXTURE["reviewed_watcher"]})
        self.assertEqual(len(proposals), 1)
        self.assertEqual(draft.resources["watcher"], FIXTURE["source_resources"]["watcher"])
        self.assertEqual(proposals[0]["status"], "pending")
        pending = save_derived(self.store, draft, form="delta")
        pending_content = effective_content(self.store, ref(pending))
        self.assertIn("pending_impact", {issue["kind"] for issue in pending_content["issues"]})
        self.assertEqual(pending_content["readiness"]["playing"], "limited")
        self.assertEqual(len(query(pending_content, "Wind step", audience="PLAYER")), 1)
        self.assertEqual(len(query(pending_content, "Wind step", audience="GM")), 2)
        self.assertEqual(query(pending_content, "Hidden gear", audience="PLAYER"), [])
        self.assertEqual(
            pending_content["resources"]["wind"]["origin"]["derived_from"]["revision"],
            self.source["revision"],
        )
        source_origin = self.source["resources"]["watcher"]["origin"]
        self.assertEqual(source_origin["source_id"], "public-windmill-v1")
        fixture_path, pointer = source_origin["locator"].split("#")
        located = json.loads((Path(__file__).parents[1] / fixture_path).read_text())
        for part in pointer.strip("/").split("/"):
            located = located[part]
        self.assertEqual(located, FIXTURE["source_resources"]["watcher"])

        accept_impact(draft, proposals[0]["id"])
        delta = save_derived(self.store, draft, form="delta")
        snapshot = save_derived(self.store, draft, form="snapshot")
        effective_delta = effective_content(self.store, ref(delta))
        effective_snapshot = effective_content(self.store, ref(snapshot))
        self.assertEqual(effective_delta["resources"], effective_snapshot["resources"])
        self.assertEqual(effective_delta["relationships"], FIXTURE["source_relationships"])
        self.assertEqual(effective_delta["relationships"], effective_snapshot["relationships"])
        self.assertEqual(effective_delta["lineage"], effective_snapshot["lineage"])
        self.assertEqual(effective_delta["proposals"], effective_snapshot["proposals"])
        self.assertEqual(effective_delta["issues"], [])
        self.assertEqual(self.store.load(ref(self.source)), self.source)
        self.assertEqual(effective_delta["resources"]["watcher"]["text"], FIXTURE["reviewed_watcher"]["text"])
        self.assertNotIn("base", snapshot)
        self.assertNotIn("resources", delta)

    def test_link_or_bundle_exact_rule_and_visible_missing_states(self) -> None:
        rules = make_source_package(
            self.store, package_id=FIXTURE["rules_package_id"], title="Windmill rules",
            resources={"calm": FIXTURE["external_rule"]},
        )
        draft = derive(self.store, ref(self.source), package_id="rules-choice", title="Rules choice")
        select_dependency(self.store, draft, ref(rules), mode="linked")
        linked = save_derived(self.store, draft, form="snapshot")
        linked_content = effective_content(self.store, ref(linked))
        binding = {**ref(rules), "resource_id": "calm", "ruleset": "windmill-v1"}
        self.assertEqual(resolve_rule(self.store, linked_content, binding, audience="PLAYER")["state"], "resolved")
        wrong_edition = {**binding, "ruleset": "windmill-v2"}
        self.assertEqual(resolve_rule(self.store, linked_content, wrong_edition, audience="PLAYER")["reason"], "ruleset or edition mismatch")
        wrong_revision = {**binding, "revision": "0" * 64}
        self.assertEqual(resolve_rule(self.store, linked_content, wrong_revision, audience="PLAYER")["reason"], "undeclared exact dependency")
        with self.assertRaisesRegex(CompositionError, "permission basis"):
            select_dependency(self.store, draft, ref(rules), mode="bundled", resource_ids=["calm"])
        select_dependency(self.store, draft, ref(rules), mode="bundled", resource_ids=["calm"],
                          permission_basis="project-authored engineering fixture")
        bundled = save_derived(self.store, draft, form="snapshot")
        self.store.path_for(**ref(rules)).unlink()
        bundled_content = effective_content(self.store, ref(bundled))
        self.assertEqual(resolve_rule(self.store, bundled_content, binding, audience="PLAYER")["state"], "resolved")
        unavailable = effective_content(self.store, ref(linked))
        self.assertIn("missing_dependency", {issue["kind"] for issue in unavailable["issues"]})
        self.assertEqual(resolve_rule(self.store, unavailable, binding, audience="PLAYER")["reason"], "linked dependency unavailable")

    def test_missing_base_does_not_hide_saved_draft_content(self) -> None:
        draft = derive(self.store, ref(self.source), package_id="partial", title="Partial")
        edit_resource(draft, FIXTURE["amended_rule"])
        delta = save_derived(self.store, draft, form="delta")
        snapshot = save_derived(self.store, draft, form="snapshot")
        self.store.path_for(**ref(self.source)).unlink()
        partial = effective_content(self.store, ref(delta))
        self.assertIn("missing_base", {issue["kind"] for issue in partial["issues"]})
        self.assertIn("wind", partial["resources"])
        independent = effective_content(self.store, ref(snapshot))
        self.assertEqual(independent["resources"]["hook"], FIXTURE["source_resources"]["hook"])
        self.assertFalse(any(issue["kind"] == "missing_base" for issue in independent["issues"]))

    def test_new_edit_preserves_superseded_impact_history(self) -> None:
        draft = derive(self.store, ref(self.source), package_id="iterated", title="Iterated")
        first = edit_resource(draft, FIXTURE["amended_rule"])[0]
        later_rule = deepcopy(FIXTURE["amended_rule"])
        later_rule["text"] += " A later clarification."
        second = edit_resource(draft, later_rule)[0]
        self.assertNotEqual(first["id"], second["id"])
        saved = save_derived(self.store, draft, form="delta")
        content = effective_content(self.store, ref(saved))
        self.assertEqual(
            [(p["id"], p["status"]) for p in content["proposals"]],
            [(first["id"], "superseded"), (second["id"], "pending")],
        )
        self.assertEqual(
            [i["proposal_id"] for i in content["issues"] if i["kind"] == "pending_impact"],
            [second["id"]],
        )
        with self.assertRaisesRegex(CompositionError, "pending impact proposal not found"):
            accept_impact(draft, first["id"], replacement=FIXTURE["reviewed_watcher"])

    def test_unresolved_local_rule_is_visible_and_limits_readiness(self) -> None:
        creature = deepcopy(FIXTURE["source_resources"]["watcher"])
        creature["rule_refs"] = [{"resource_id": "missing", "ruleset": "windmill-v1"}]
        broken = make_source_package(self.store, package_id="unresolved", title="Unresolved",
                                     resources={"watcher": creature})
        content = effective_content(self.store, ref(broken))
        self.assertEqual(len(content["resources"]), 1)
        self.assertEqual(content["issues"], [{
            "kind": "unresolved_rule", "source_id": "watcher",
            "binding": {"resource_id": "missing", "ruleset": "windmill-v1"},
            "reason": "bound rule missing",
        }])
        self.assertEqual(content["readiness"], {
            "worldbuilding": "limited", "planning": "limited", "playing": "limited",
        })

    def test_relationship_only_rule_dependent_requires_impact_review(self) -> None:
        watcher = deepcopy(FIXTURE["source_resources"]["watcher"])
        watcher.pop("rule_refs")
        related = make_source_package(
            self.store, package_id="relation-only", title="Relation only",
            resources={"wind": FIXTURE["source_resources"]["wind"], "watcher": watcher},
            relationships=[FIXTURE["source_relationships"][0]],
        )
        draft = derive(self.store, ref(related), package_id="relation-edit", title="Relation edit")
        proposals = edit_resource(draft, FIXTURE["amended_rule"])
        self.assertEqual([p["target_id"] for p in proposals], ["watcher"])
        pending = save_derived(self.store, draft, form="delta")
        content = effective_content(self.store, ref(pending))
        self.assertIn("pending_impact", {issue["kind"] for issue in content["issues"]})
        self.assertEqual(content["resources"]["watcher"], watcher)

    def test_integrity_and_identity_fail_closed(self) -> None:
        path = self.store.path_for(**ref(self.source))
        corrupt = deepcopy(self.source)
        corrupt["resources"]["hook"]["text"] = "Different source text"
        path.write_text(json.dumps(corrupt))
        with self.assertRaisesRegex(CompositionError, "integrity mismatch"):
            self.store.load(ref(self.source))
        with self.assertRaisesRegex(CompositionError, "invalid package id"):
            self.store.path_for("../escape", "0" * 64)


if __name__ == "__main__":
    unittest.main()
