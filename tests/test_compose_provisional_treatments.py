"""Synthetic witnesses for disjoint provisional package composition."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor import CompositionError, JsonPackageStore, make_source_package
from compositor.benchmark_review import validate_review_packet
from compositor.compose_provisional_treatments import (
    build_combined_review_packet, compose_provisional_treatments,
)


def resource(rid: str) -> dict:
    return {"id": rid, "kind": "evidence_prose", "name": rid, "text": f"Invented {rid}.",
            "audience": "GM", "origin": {"type": "source",
                                      "source_id": "sha256:" + "a" * 64,
                                      "locator": f"fixture/{rid}", "page_index": 0}}


class ComposeProvisionalTreatmentsTest(unittest.TestCase):
    def test_disjoint_additive_composition_and_rejections(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            store = JsonPackageStore(root / "packages")
            base = make_source_package(store, package_id="fixture-base", title="Invented source",
                resources={rid: resource(rid) for rid in ("a", "b")},
                relationships=[{"id": "base-link", "source_id": "a", "target_id": "b",
                                "kind": "related"}])
            base_ref = {key: base[key] for key in ("package_id", "revision")}

            first = deepcopy(base)
            first.pop("revision")
            first["package_id"] = "fixture-identity"
            first["lineage"] = [base_ref]
            first["resources"]["identity"] = resource("identity")
            first["relationships"].append({"id": "identity-link", "source_id": "a",
                                           "target_id": "identity", "kind": "evidence_for_identity"})
            first["diagnostics"] = [{"kind": "interpretation_pending", "resource_ids": ["a"],
                                     "reason": "invented identity needs review"}]
            first["promotion_state"] = "provisional_pending_independent_review"
            first["review_authority"] = "agent"
            first["reviewed_source_decisions"] = [{"reviewer": "fixture agent",
                                                    "choice": "accept_identity_form"}]
            first = store.save(first)

            second = deepcopy(base)
            second.pop("revision")
            second["package_id"] = "fixture-statblock"
            second["lineage"] = [base_ref]
            second["diagnostics"] = [{"kind": "interpretation_pending", "resource_id": "b",
                                      "detail_kind": "statblock_modifier_inconsistency",
                                      "reason": "printed value conflicts"}]
            second["promotion_state"] = "provisional_pending_independent_review"
            second["review_authority"] = "agent"
            second["reviewed_statblock_conflicts"] = [{"reviewer": "fixture agent",
                                                        "choice": "record_source_inconsistency"}]
            second = store.save(second)

            combined = compose_provisional_treatments(base=base,
                treatments=[second, first], output_store=store, package_id="fixture-combined")
            ref = {key: combined[key] for key in ("package_id", "revision")}
            self.assertEqual(store.load(ref), combined)
            self.assertEqual(combined["composition_base_ref"], base_ref)
            self.assertEqual(combined["lineage"], [{key: first[key]
                                                     for key in ("package_id", "revision")},
                                                    {key: second[key]
                                                     for key in ("package_id", "revision")}])
            self.assertEqual({rid: combined["resources"][rid]
                              for rid in base["resources"]}, base["resources"])
            self.assertEqual(len(combined["resources"]), 3)
            self.assertEqual(len(combined["relationships"]), 2)
            self.assertEqual(len(combined["diagnostics"]), 2)
            self.assertEqual(combined["promotion_state"],
                             "provisional_pending_independent_review")
            self.assertEqual({item["ref"]["package_id"]
                              for item in combined["component_treatments"]},
                             {"fixture-identity", "fixture-statblock"})
            reversed_result = compose_provisional_treatments(base=base,
                treatments=[first, second], output_store=store, package_id="fixture-combined")
            self.assertEqual(reversed_result, combined)
            expected = {"review_package_ref": base_ref,
                        "source_pdf_sha256": "a" * 64,
                        "available_resource_ids": sorted(base["resources"]),
                        "cases": [{"id": "fixture-case", "evidence": {"pdf_page_1_based": 1},
                                   "candidate_text_resources": [],
                                   "candidate_asset_references": [],
                                   "candidate_resource_ids": [], "review": None}],
                        "integration_cases": [{"id": "fixture-integration",
                                               "execution_state": "unexecuted"}]}
            packet = build_combined_review_packet(expected=expected,
                                                  baseline=base, combined=combined)
            self.assertIsNone(packet["cases"][0]["review"])
            self.assertEqual(packet["integration_cases"], expected["integration_cases"])
            self.assertEqual(set(packet["cases"][0]["candidate_resource_ids"]),
                             set(combined["resources"]))
            reviewed = deepcopy(packet)
            reviewed["cases"][0]["review"] = {"verdict": "pass",
                "reviewer": "fixture agent", "rationale": "Both additive records remain available.",
                "resource_ids": ["a", "b"]}
            self.assertEqual(validate_review_packet(reviewed, expected=packet,
                                                    require_complete=True)["reviewed"], 1)

            tampered_review = deepcopy(first)
            tampered_review["reviewed_source_decisions"][0]["choice"] = "unresolved"
            with self.assertRaisesRegex(CompositionError, "revision integrity mismatch"):
                compose_provisional_treatments(base=base,
                    treatments=[tampered_review, second], output_store=store,
                    package_id="tampered-review")
            tampered_combined = deepcopy(combined)
            tampered_combined["resources"]["identity"]["text"] = "Altered without revision"
            with self.assertRaisesRegex(CompositionError, "revision integrity mismatch"):
                build_combined_review_packet(expected=expected, baseline=base,
                                             combined=tampered_combined)
            tampered_base = deepcopy(base)
            tampered_base["resources"]["a"]["text"] = "Altered baseline"
            with self.assertRaisesRegex(CompositionError, "revision integrity mismatch"):
                build_combined_review_packet(expected=expected, baseline=tampered_base,
                                             combined=combined)

            def repin(value: dict) -> dict:
                updated = deepcopy(value)
                updated.pop("revision")
                return store.save(updated)

            modified = deepcopy(first)
            modified["resources"]["a"]["text"] = "Rewritten source"
            with self.assertRaisesRegex(CompositionError, "changed or removed a base resource"):
                compose_provisional_treatments(base=base, treatments=[repin(modified), second],
                    output_store=store, package_id="modified")
            changed_relation = deepcopy(second)
            changed_relation["relationships"][0]["kind"] = "changed"
            with self.assertRaisesRegex(CompositionError, "changed or removed a base relationship"):
                compose_provisional_treatments(base=base,
                    treatments=[first, repin(changed_relation)], output_store=store,
                    package_id="changed-relation")
            overlapping = deepcopy(second)
            overlapping["diagnostics"][0]["resource_id"] = "a"
            with self.assertRaisesRegex(CompositionError, "collide or overlap"):
                compose_provisional_treatments(base=base, treatments=[first, repin(overlapping)],
                    output_store=store, package_id="overlap")
            linked_overlap = deepcopy(second)
            linked_overlap["diagnostics"][0]["relationship_id"] = "base-link"
            with self.assertRaisesRegex(CompositionError, "collide or overlap"):
                compose_provisional_treatments(base=base, treatments=[first, repin(linked_overlap)],
                    output_store=store, package_id="linked-overlap")
            foreign_relation = deepcopy(second)
            foreign_relation["diagnostics"][0]["relationship_id"] = "identity-link"
            with self.assertRaisesRegex(CompositionError, "unavailable relationship"):
                compose_provisional_treatments(base=base, treatments=[first, repin(foreign_relation)],
                    output_store=store, package_id="foreign-relation")
            collided = deepcopy(second)
            collided["resources"]["identity"] = resource("identity")
            with self.assertRaisesRegex(CompositionError, "collide or overlap"):
                compose_provisional_treatments(base=base, treatments=[first, repin(collided)],
                    output_store=store, package_id="collision")
            foreign_source = deepcopy(first)
            foreign_source["resources"]["identity"]["origin"]["source_id"] = "sha256:" + "b" * 64
            with self.assertRaisesRegex(CompositionError, "outside pinned source pages"):
                compose_provisional_treatments(base=base, treatments=[repin(foreign_source), second],
                    output_store=store, package_id="foreign-source")
            wrong_base = deepcopy(second)
            wrong_base["lineage"] = []
            with self.assertRaisesRegex(CompositionError, "different or ambiguous base"):
                compose_provisional_treatments(base=base, treatments=[first, repin(wrong_base)],
                    output_store=store, package_id="wrong-base")
            with self.assertRaisesRegex(CompositionError, "duplicate treatment revision"):
                compose_provisional_treatments(base=base, treatments=[first, first],
                    output_store=store, package_id="duplicate")


if __name__ == "__main__":
    unittest.main()
