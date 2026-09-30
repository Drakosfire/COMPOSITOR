"""Contract witnesses for the first public, project-authored Composition cycle."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor import (
    CompositionError, JsonPackageStore, accept_impact, assess_rule_use, derive, edit_resource,
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
        unspecified = {key: value for key, value in binding.items() if key != "ruleset"}
        self.assertEqual(resolve_rule(self.store, linked_content, unspecified, audience="PLAYER")["reason"],
                         "external rule edition unspecified")
        self.assertEqual(resolve_rule(self.store, linked_content,
                                      {**binding, "ruleset": ""}, audience="PLAYER")["reason"],
                         "external rule edition unspecified")
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
        self.assertEqual(resolve_rule(self.store, bundled_content, unspecified, audience="PLAYER")["reason"],
                         "external rule edition unspecified")
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

    def test_unversioned_external_rule_binding_stays_visible_but_unresolved(self) -> None:
        rules = make_source_package(
            self.store, package_id=FIXTURE["rules_package_id"], title="Windmill rules",
            resources={"calm": FIXTURE["external_rule"]},
        )
        draft = derive(self.store, ref(self.source), package_id="unversioned-rule",
                       title="Unversioned rule draft")
        select_dependency(self.store, draft, ref(rules), mode="linked")
        watcher = deepcopy(draft.resources["watcher"])
        watcher["rule_refs"].append({**ref(rules), "resource_id": "calm"})
        edit_resource(draft, watcher)
        saved = save_derived(self.store, draft, form="snapshot")
        content = effective_content(self.store, ref(saved))
        self.assertIn("external rule edition unspecified",
                      {issue.get("reason") for issue in content["issues"]})
        self.assertEqual(content["readiness"]["playing"], "limited")
        self.assertTrue(query(content, "Mill Watcher", audience="GM"))

        watcher["rule_refs"][-1]["ruleset"] = "windmill-v1"
        edit_resource(draft, watcher)
        corrected = save_derived(self.store, draft, form="snapshot")
        self.assertNotIn("unresolved_rule",
                         {issue["kind"] for issue in effective_content(self.store, ref(corrected))["issues"]})

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

    def test_dangling_relationship_survives_source_and_derived_reload_as_issue(self) -> None:
        relationship = {"id": "points", "source_id": "hook", "target_id": "missing",
                        "kind": "introduces"}
        broken = make_source_package(
            self.store, package_id="dangling", title="Dangling",
            resources={"hook": FIXTURE["source_resources"]["hook"]},
            relationships=[relationship],
        )
        source_content = effective_content(self.store, ref(broken))
        issue = {"kind": "unresolved_relationship", "relationship_id": "points",
                 "missing_endpoints": ["target_id"]}
        self.assertEqual(source_content["issues"], [issue])
        self.assertEqual(source_content["readiness"]["worldbuilding"], "limited")
        self.assertEqual(len(query(source_content, "invites", audience="PLAYER")), 1)

        draft = derive(self.store, ref(broken), package_id="dangling-adapted", title="Adapted")
        saved = save_derived(self.store, draft, form="delta")
        reloaded = effective_content(self.store, ref(saved))
        self.assertEqual(reloaded["issues"], [issue])
        self.assertEqual(reloaded["resources"]["hook"], FIXTURE["source_resources"]["hook"])

    def test_integrity_and_identity_fail_closed(self) -> None:
        path = self.store.path_for(**ref(self.source))
        corrupt = deepcopy(self.source)
        corrupt["resources"]["hook"]["text"] = "Different source text"
        path.write_text(json.dumps(corrupt))
        with self.assertRaisesRegex(CompositionError, "integrity mismatch"):
            self.store.load(ref(self.source))
        with self.assertRaisesRegex(CompositionError, "invalid package id"):
            self.store.path_for("../escape", "0" * 64)

    def test_rule_use_readiness_traces_exact_linked_and_bundled_issues(self) -> None:
        calm = deepcopy(FIXTURE["external_rule"])
        calm["review_coverage"] = ["playing"]
        other = deepcopy(calm)
        other["id"] = "other"
        other["name"] = "Other rule"
        other["origin"] = {"type": "authored", "reason": "Unrelated synthetic rule"}
        rules = make_source_package(
            self.store, package_id="scoped-rules", title="Scoped rules",
            resources={"calm": calm, "other": other},
            diagnostics=[{"kind": "interpretation_pending", "resource_id": "calm"},
                         {"kind": "interpretation_pending", "resource_id": "other"}],
        )
        exact = ref(rules)
        watcher = deepcopy(FIXTURE["source_resources"]["watcher"])
        watcher["review_coverage"] = ["playing"]
        binding = {**exact, "resource_id": "calm", "ruleset": "windmill-v1"}
        watcher["rule_refs"] = [binding]
        for mode in ("linked", "bundled"):
            draft = derive(self.store, ref(self.source), package_id=f"scoped-{mode}",
                           title=f"Scoped {mode}")
            edit_resource(draft, watcher)
            select_dependency(self.store, draft, exact, mode=mode,
                              resource_ids=["calm"] if mode == "bundled" else None,
                              permission_basis="project-authored fixture" if mode == "bundled" else None)
            for form in ("delta", "snapshot"):
                saved = save_derived(self.store, draft, form=form)
                content = effective_content(self.store, ref(saved))
                assessed = assess_rule_use(self.store, content, binding, source_id="watcher",
                                           audience="GM", workflow="playing")
                self.assertEqual(assessed["resolution"]["state"], "resolved")
                self.assertEqual(assessed["use_readiness"], "limited")
                inherited = [e for e in assessed["evidence"] if e.get("issue", {}).get("resource_id") == "calm"]
                self.assertEqual(len(inherited), 1)
                self.assertEqual(inherited[0]["path"][-1]["mode"], mode)
                self.assertTrue(inherited[0]["issue_id"])
                self.assertFalse(any(e.get("issue", {}).get("resource_id") == "other"
                                     for e in assessed["evidence"]))
                if mode == "bundled":
                    bundled_content = content
        self.store.path_for(**exact).unlink()
        portable = assess_rule_use(self.store, bundled_content, binding, source_id="watcher",
                                   audience="GM", workflow="playing")
        self.assertEqual(portable["use_readiness"], "limited")
        legacy = deepcopy(bundled_content)
        legacy["dependencies"][0].pop("review_scope_complete")
        self.assertEqual(assess_rule_use(self.store, legacy, binding, source_id="watcher",
                                         audience="GM", workflow="playing")["use_readiness"], "unknown")

    def test_rule_use_readiness_requires_scoped_review_coverage(self) -> None:
        calm = deepcopy(FIXTURE["external_rule"])
        calm["review_coverage"] = ["playing"]
        rules = make_source_package(self.store, package_id="review-rules", title="Review rules",
                                    resources={"calm": calm})
        binding = {**ref(rules), "resource_id": "calm", "ruleset": "windmill-v1"}
        watcher = deepcopy(FIXTURE["source_resources"]["watcher"])
        watcher["rule_refs"] = [binding]
        watcher["review_coverage"] = ["playing"]
        consumer = make_source_package(
            self.store, package_id="review-consumer", title="Review consumer",
            resources={"watcher": watcher},
            dependencies=[{**ref(rules), "mode": "linked"}],
        )
        content = effective_content(self.store, ref(consumer))
        assess = lambda: assess_rule_use(self.store, content, binding, source_id="watcher",
                                          audience="GM", workflow="playing")
        self.assertEqual(assess()["use_readiness"], "usable")
        unrelated = make_source_package(
            self.store, package_id="unrelated-rules", title="Unrelated diagnostic",
            resources={"calm": calm, "other": {**deepcopy(calm), "id": "other"}},
            diagnostics=[{"kind": "interpretation_pending", "resource_id": "other"}],
        )
        unrelated_binding = {**ref(unrelated), "resource_id": "calm", "ruleset": "windmill-v1"}
        watcher["rule_refs"] = [unrelated_binding]
        unrelated_consumer = make_source_package(
            self.store, package_id="unrelated-consumer", title="Unrelated consumer",
            resources={"watcher": watcher}, dependencies=[{**ref(unrelated), "mode": "linked"}],
        )
        self.assertEqual(assess_rule_use(
            self.store, effective_content(self.store, ref(unrelated_consumer)),
            unrelated_binding, source_id="watcher", audience="GM",
            workflow="playing")["use_readiness"], "usable")
        self.assertEqual(assess_rule_use(self.store, content, binding, source_id="watcher",
                                         audience="GM", workflow="planning")["use_readiness"], "unknown")
        unscoped = make_source_package(
            self.store, package_id="unscoped-rules", title="Unscoped rules",
            resources={"calm": calm}, diagnostics=[{"kind": "interpretation_pending"}],
        )
        unscoped_binding = {**ref(unscoped), "resource_id": "calm", "ruleset": "windmill-v1"}
        watcher["rule_refs"] = [unscoped_binding]
        unscoped_consumer = make_source_package(
            self.store, package_id="unscoped-consumer", title="Unscoped consumer",
            resources={"watcher": watcher}, dependencies=[{**ref(unscoped), "mode": "linked"}],
        )
        uncertain = assess_rule_use(self.store, effective_content(self.store, ref(unscoped_consumer)),
                                    unscoped_binding, source_id="watcher", audience="GM",
                                    workflow="playing")
        self.assertEqual(uncertain["use_readiness"], "unknown")
        self.assertTrue(any(e["reason"] == "unscoped interpretation_pending"
                            for e in uncertain["evidence"]))
        global_rules = make_source_package(
            self.store, package_id="global-rules", title="Global diagnostic",
            resources={"calm": calm},
            diagnostics=[{"kind": "interpretation_pending", "scope": "global"}],
        )
        global_binding = {**ref(global_rules), "resource_id": "calm", "ruleset": "windmill-v1"}
        watcher["rule_refs"] = [global_binding]
        global_consumer = make_source_package(
            self.store, package_id="global-consumer", title="Global consumer",
            resources={"watcher": watcher}, dependencies=[{**ref(global_rules), "mode": "linked"}],
        )
        self.assertEqual(assess_rule_use(
            self.store, effective_content(self.store, ref(global_consumer)), global_binding,
            source_id="watcher", audience="GM", workflow="playing")["use_readiness"], "limited")
        self.store.path_for(**ref(rules)).unlink()
        self.assertEqual(assess()["use_readiness"], "unavailable")

    def test_rule_use_readiness_denial_edition_and_local_cycle(self) -> None:
        calm = deepcopy(FIXTURE["external_rule"])
        calm["review_coverage"] = ["playing"]
        calm["audience"] = "GM"
        rules = make_source_package(self.store, package_id="restricted-rules",
                                    title="Restricted rules", resources={"calm": calm})
        binding = {**ref(rules), "resource_id": "calm", "ruleset": "windmill-v1"}
        watcher = deepcopy(FIXTURE["source_resources"]["watcher"])
        watcher["review_coverage"] = ["playing"]
        watcher["rule_refs"] = [binding, {**binding, "ruleset": "other-edition"}]
        consumer = make_source_package(self.store, package_id="restricted-consumer",
                                       title="Restricted consumer", resources={"watcher": watcher},
                                       dependencies=[{**ref(rules), "mode": "linked"}])
        content = effective_content(self.store, ref(consumer))
        denied = assess_rule_use(self.store, content, binding, source_id="watcher",
                                 audience="PLAYER", workflow="playing")
        self.assertEqual((denied["resolution"]["state"], denied["use_readiness"]),
                         ("unsupported", "unavailable"))
        wrong = assess_rule_use(self.store, content, watcher["rule_refs"][1],
                                source_id="watcher", audience="GM", workflow="playing")
        self.assertEqual((wrong["resolution"]["state"], wrong["use_readiness"]),
                         ("unresolved", "unavailable"))

        first = deepcopy(FIXTURE["source_resources"]["wind"])
        first["review_coverage"] = ["playing"]
        first["rule_refs"] = [{"resource_id": "second", "ruleset": "windmill-v1"}]
        second = deepcopy(first)
        second["id"] = "second"
        second["rule_refs"] = [{"resource_id": "wind", "ruleset": "windmill-v1"}]
        second["origin"] = {"type": "authored", "reason": "Synthetic cyclic rule"}
        citer = deepcopy(FIXTURE["source_resources"]["watcher"])
        citer["review_coverage"] = ["playing"]
        citer["rule_refs"] = [{"resource_id": "wind", "ruleset": "windmill-v1"}]
        cycle = make_source_package(self.store, package_id="cyclic-rules", title="Cyclic rules",
                                    resources={"watcher": citer, "wind": first, "second": second})
        assessed = assess_rule_use(self.store, effective_content(self.store, ref(cycle)),
                                   citer["rule_refs"][0], source_id="watcher", audience="GM",
                                   workflow="playing")
        self.assertEqual(assessed["use_readiness"], "unknown")
        self.assertTrue(any(e["reason"] == "cyclic rule use" for e in assessed["evidence"]))

    def test_unscoped_issue_stays_unknown_when_bundled_and_reloaded(self) -> None:
        calm = deepcopy(FIXTURE["external_rule"])
        calm["review_coverage"] = ["playing"]
        rules = make_source_package(
            self.store, package_id="unscoped-copy-rules", title="Unscoped copy rules",
            resources={"calm": calm}, diagnostics=[{"kind": "interpretation_pending"}],
        )
        binding = {**ref(rules), "resource_id": "calm", "ruleset": "windmill-v1"}
        watcher = deepcopy(FIXTURE["source_resources"]["watcher"])
        watcher["rule_refs"] = [binding]
        watcher["review_coverage"] = ["playing"]
        saved_refs = []
        for mode in ("linked", "bundled"):
            draft = derive(self.store, ref(self.source), package_id=f"copy-{mode}",
                           title=f"Copy {mode}")
            edit_resource(draft, watcher)
            select_dependency(self.store, draft, ref(rules), mode=mode,
                              resource_ids=["calm"] if mode == "bundled" else None,
                              permission_basis="project-authored fixture" if mode == "bundled" else None)
            for form in ("delta", "snapshot"):
                saved = save_derived(self.store, draft, form=form)
                saved_refs.append((mode, ref(saved)))
                content = effective_content(self.store, ref(saved))
                assessed = assess_rule_use(self.store, content, binding, source_id="watcher",
                                           audience="GM", workflow="playing")
                self.assertEqual(assessed["use_readiness"], "unknown")
                self.assertTrue(any(e["reason"] == "unscoped interpretation_pending"
                                    for e in assessed["evidence"]))
                if mode == "bundled":
                    self.assertNotIn("resource_ids", content["dependencies"][0]["review_issues"][0])
        self.store.path_for(**ref(rules)).unlink()
        for mode, saved_ref in saved_refs:
            content = effective_content(self.store, saved_ref)
            assessed = assess_rule_use(self.store, content, binding, source_id="watcher",
                                       audience="GM", workflow="playing")
            self.assertEqual(assessed["use_readiness"],
                             "unknown" if mode == "bundled" else "unavailable")


if __name__ == "__main__":
    unittest.main()
