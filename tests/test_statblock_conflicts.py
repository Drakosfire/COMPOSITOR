"""Synthetic PDF evidence for source-scoped statblock conflict detection."""

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
from compositor.package import readiness
from compositor.benchmark_review import validate_review_packet
from compositor.statblock_conflicts import (
    apply_statblock_conflict_reviews, build_statblock_treatment_packet,
    scan_statblock_conflicts,
)


HEADERS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
GOOD = ("16 (+3)", "12 (+1)", "17 (+3)", "8 (-1)", "11 (+0)", "8 (-1)")
PRINTED_CONFLICT = GOOD[:-1] + ("8 (+1)",)


def table(cells: tuple[str, ...], *, span: bool = False) -> str:
    first = "".join(f"<td>{head}</td>" for head in HEADERS)
    if span:
        first = first.replace("<td>INT</td>", '<td rowspan="2">INT</td>')
    second = "".join(f"<td>{cell}</td>" for cell in cells)
    return f"<table><tr>{first}</tr><tr>{second}</tr></table>"


@unittest.skipUnless(fitz is not None, "PyMuPDF required for physical PDF cell verification")
class StatblockConflictsTest(unittest.TestCase):
    def test_scan_review_additive_revision_and_rejections(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            pdf = root / "invented.pdf"
            source_cells = [GOOD, PRINTED_CONFLICT, GOOD, GOOD, GOOD]
            document = fitz.open()
            for cells in source_cells:
                page = document.new_page(width=420, height=180)
                for index, (header, cell) in enumerate(zip(HEADERS, cells, strict=True)):
                    x = 42 + index * 60
                    page.insert_text((x, 50), header, fontsize=9)
                    page.insert_text((x - 4, 63), cell, fontsize=9)
            document.save(pdf)
            document.close()
            pdf_sha = sha256(pdf.read_bytes()).hexdigest()
            texts = [table(GOOD), table(PRINTED_CONFLICT),
                     table(GOOD[:3], span=True),
                     table(GOOD[:-1] + ("8 (+2)",)),
                     "<table><tr><td>Loot</td><td>Weight</td></tr><tr><td>1</td><td>2</td></tr></table>"]
            resources = {}
            for index, value in enumerate(texts):
                rid = f"table-{index}"
                resources[rid] = {"id": rid, "kind": "evidence_table", "name": rid,
                    "text": value, "audience": "GM",
                    "origin": {"type": "source", "source_id": f"sha256:{pdf_sha}",
                               "locator": f"pdf/page-{index + 1}#table", "page_index": index}}
            base = make_source_package(JsonPackageStore(root / "base"),
                package_id="invented-base", title="Invented statblocks", resources=resources)
            scan = scan_statblock_conflicts(package=base, pdf_path=pdf,
                                           expected_pdf_sha256=pdf_sha)
            self.assertEqual(scan["scanned_tables"], 5)
            self.assertEqual(scan["consistent_resource_ids"], ["table-0"])
            self.assertEqual([(item["resource_id"], item["reason"])
                              for item in scan["rejections"]],
                             [("table-2", "ambiguous_ability_table"),
                              ("table-3", "pdf_cell_mismatch_or_ambiguous"),
                              ("table-4", "non_statblock_table")])
            self.assertEqual(len(scan["candidates"]), 1)
            candidate = scan["candidates"][0]
            self.assertEqual(candidate["resource_id"], "table-1")
            self.assertEqual(candidate["mismatches"][0]["ability"], "CHA")
            self.assertEqual(candidate["mismatches"][0]["printed_score"], 8)
            self.assertEqual(candidate["mismatches"][0]["printed_modifier"], 1)
            self.assertEqual(candidate["mismatches"][0]["calculated_modifier"], -1)
            self.assertEqual(candidate["mismatches"][0]["pdf_cell"], "8(+1)")
            self.assertTrue(all(isinstance(x, float) for x in
                                candidate["mismatches"][0]["pdf_cell_bbox"]))
            scan_pin = sha256(json.dumps(scan, sort_keys=True, ensure_ascii=False,
                separators=(",", ":")).encode()).hexdigest()
            decisions = {"scan_context_sha256": scan_pin, "review_authority": "agent",
                         "reviews": [{"candidate_id": candidate["id"],
                                      "choice": "record_source_inconsistency",
                                      "reviewer": "fixture agent",
                                      "rationale": "Printed page repeats score eight with modifier plus one."}]}
            store = JsonPackageStore(root / "treated")

            def apply(value: dict = decisions, *, package_id: str = "treated") -> dict:
                return apply_statblock_conflict_reviews(base=base, scan=scan, decisions=value,
                    pdf_path=pdf, expected_pdf_sha256=pdf_sha,
                    output_store=store, package_id=package_id)

            treated = apply()
            self.assertEqual(store.load({key: treated[key] for key in ("package_id", "revision")}),
                             treated)
            self.assertEqual(treated["resources"], base["resources"])
            self.assertEqual(treated["review_authority"], "agent")
            self.assertEqual(treated["promotion_state"], "provisional_pending_independent_review")
            diagnostic = treated["diagnostics"][-1]
            self.assertEqual(diagnostic["kind"], "interpretation_pending")
            self.assertEqual(diagnostic["detail_kind"], "statblock_modifier_inconsistency")
            self.assertEqual(diagnostic["resource_id"], "table-1")
            self.assertEqual(diagnostic["mismatches"], candidate["mismatches"])
            self.assertEqual(readiness(treated["diagnostics"])["playing"], "limited")
            expected = {"review_package_ref": {key: base[key]
                                                for key in ("package_id", "revision")},
                        "source_pdf_sha256": pdf_sha,
                        "available_resource_ids": sorted(base["resources"]),
                        "cases": [{"id": "fixture-case", "evidence": {"pdf_page_1_based": 2},
                                   "candidate_text_resources": [],
                                   "candidate_asset_references": [],
                                   "candidate_resource_ids": [], "review": None}],
                        "integration_cases": [{"id": "fixture-integration",
                                               "execution_state": "unexecuted"}]}
            packet = build_statblock_treatment_packet(expected=expected,
                                                       baseline=base, treated=treated)
            self.assertEqual(packet["treatment_basis"],
                             "additive_reviewed_statblock_conflicts")
            self.assertIsNone(packet["cases"][0]["review"])
            self.assertEqual(packet["integration_cases"], expected["integration_cases"])
            reviewed = deepcopy(packet)
            reviewed["cases"][0]["review"] = {
                "verdict": "pass", "reviewer": "fixture agent",
                "rationale": "The printed cell and scoped diagnostic are retained.",
                "resource_ids": ["table-1"]}
            self.assertEqual(validate_review_packet(reviewed, expected=packet,
                                                    require_complete=True)["reviewed"], 1)
            changed = deepcopy(scan)
            changed["candidates"][0]["mismatches"][0]["printed_modifier"] = -1
            with self.assertRaisesRegex(CompositionError, "scan context changed"):
                apply_statblock_conflict_reviews(base=base, scan=changed, decisions=decisions,
                    pdf_path=pdf, expected_pdf_sha256=pdf_sha,
                    output_store=store, package_id="changed")
            no_reviewer = deepcopy(decisions)
            no_reviewer["reviews"][0]["reviewer"] = ""
            with self.assertRaisesRegex(CompositionError, "reviewer and rationale"):
                apply(no_reviewer, package_id="no-reviewer")
            pdf.write_bytes(b"changed")
            with self.assertRaisesRegex(CompositionError, "source PDF revision mismatch"):
                apply(decisions, package_id="changed-source")


if __name__ == "__main__":
    unittest.main()
