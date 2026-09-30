"""Prepare private, offline Conks evidence without scoring or provider calls.

Run with the pinned RulesIngestion environment and blake3 available. All source
and output paths are explicit. This recipe is intentionally separate from the
later semantic first-result treatment.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys


OWNER_REF = "17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8"
PAGE_MARKER = re.compile(r"(?m)^<!-- page (\d+) -->\s*$")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")


def split_pages(markdown: str) -> dict[int, str]:
    markers = list(PAGE_MARKER.finditer(markdown))
    pages: dict[int, str] = {}
    for index, marker in enumerate(markers):
        printed_page = int(marker.group(1))
        if printed_page in pages:
            raise ValueError(f"duplicate printed page {printed_page}")
        end = markers[index + 1].start() if index + 1 < len(markers) else len(markdown)
        pages[printed_page] = markdown[marker.end():end].strip() + "\n"
    if sorted(pages) != list(range(2, 21)):
        raise ValueError("expected exactly printed pages 2-20 in supplied Markdown")
    return pages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--gold-freeze-record", type=Path, required=True)
    parser.add_argument("--owner-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    private_root = args.private_root.resolve()
    database = args.database.resolve()
    if not database.is_relative_to(private_root):
        raise ValueError("database must be inside private root")
    out = private_root / "runs" / args.run_id
    if out.exists():
        raise ValueError("run directory already exists; choose a new run id")
    owner = args.owner_root.resolve()
    actual_owner_ref = subprocess.check_output(["git", "-C", str(owner), "rev-parse", "HEAD"], text=True).strip()
    if actual_owner_ref != OWNER_REF:
        raise ValueError(f"RulesIngestion ref mismatch: {actual_owner_ref}")
    sys.path.insert(0, str(owner))
    from extraction.ast_parser import parse_markdown_to_ast
    from extraction.gates_a import run_stage_a_gates
    from extraction.gates_b import run_stage_b_gates
    from extraction.page_source import render_page
    from extraction.stage_b import run_stage_b
    import fitz

    from compositor import JsonPackageStore, SQLiteExperimentLedger, effective_content, load_evidence_draft

    source_manifest_path = args.source_manifest.resolve()
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("suite") != "of-conks-cons-v21" or not source_manifest.get("accepted"):
        raise ValueError("accepted Conks source manifest required")
    pdf_entry = source_manifest["source_files"]["printer_friendly_pdf"]
    markdown_entry = source_manifest["source_files"]["normalized_markdown"]
    pdf = Path(pdf_entry["path"])
    markdown_path = Path(markdown_entry["path"])
    if digest(pdf) != pdf_entry["sha256"] or digest(markdown_path) != markdown_entry["sha256"]:
        raise ValueError("source file revision mismatch")
    pages = split_pages(markdown_path.read_text(encoding="utf-8"))
    gold_record = json.loads(args.gold_freeze_record.read_text(encoding="utf-8"))
    if gold_record.get("status") != "frozen":
        raise ValueError("frozen gold record required")
    gold_path = args.gold_freeze_record.resolve().parent / "proposal.json"
    gold_sha = gold_record["files"]["proposal.json"]["sha256"]
    if digest(gold_path) != gold_sha:
        raise ValueError("frozen gold revision mismatch")

    with fitz.open(pdf) as document:
        if len(document) != 19:
            raise ValueError("printer-friendly PDF must have 19 physical pages")
        image_entries = sum(len(page.get_images(full=True)) for page in document)
    out.mkdir(parents=True)
    bundle = out / "evidence" / "supplied_markdown"
    bundle.mkdir(parents=True)
    page_entries = []
    gate_failures = 0
    for printed_page, raw in sorted(pages.items()):
        page_index = printed_page - 2
        page_dir = bundle / f"page-{page_index}"
        page_dir.mkdir()
        fingerprint = render_page(pdf, page_index, page_dir).fingerprint
        ast = parse_markdown_to_ast(raw, fingerprint)
        gates_a = run_stage_a_gates(raw, ast)
        result_b = run_stage_b(ast, content_version=f"supplied-markdown-rules-ingestion-{OWNER_REF[:12]}")
        result_b.gate_diagnostics = run_stage_b_gates(result_b.units, ast_dict=ast.to_dict(),
                                                      is_standalone=page_index == 0)
        gate_failures += sum(not gate.passed for gate in [*gates_a, *result_b.gate_diagnostics])
        (page_dir / "stageA.surface.md").write_text(raw, encoding="utf-8")
        write_json(page_dir / "stageA.surface.ast.json", ast.to_dict())
        write_json(page_dir / "stageA.gate_diagnostics.json", [gate.to_dict() for gate in gates_a])
        write_json(page_dir / "stageB.evidence_units.json", result_b.to_dict())
        names = ("stageA.surface.md", "stageA.surface.ast.json", "stageA.gate_diagnostics.json",
                 "stageB.evidence_units.json")
        page_entries.append({"page_index": page_index, "printed_page": printed_page,
                             "page_fingerprint": fingerprint,
                             "artifact_dir": page_dir.name,
                             "artifact_sha256": {name: digest(page_dir / name) for name in names}})
    manifest_path = bundle / "manifest.json"
    write_json(manifest_path, {
        "format_version": 1, "rules_ingestion_ref": OWNER_REF,
        "route": "supplied_markdown", "recovery_method": "provided_markdown_override",
        "source_pdf": str(pdf.resolve()), "source_pdf_sha256": pdf_entry["sha256"],
        "supplied_markdown": str(markdown_path.resolve()),
        "supplied_markdown_sha256": markdown_entry["sha256"],
        "expected_page_indices": list(range(19)), "pages": page_entries,
        "expected_assets": [], "embedded_image_entries": image_entries,
        "known_omissions": [{"kind": "asset_inventory_pending",
                             "reason": "PDF embedded images not yet classified or extracted"}],
        "provider_calls": 0,
    })
    package_store = JsonPackageStore(out / "packages")
    result = load_evidence_draft(package_store, bundle, project_root=private_root,
                                 package_id=f"conks-evidence-{args.run_id}",
                                 title="Of Conks & Cons evidence substrate",
                                 expected_rules_ingestion_ref=OWNER_REF,
                                 expected_manifest_sha256=digest(manifest_path))
    package = result.package
    content = effective_content(package_store, {"package_id": package["package_id"],
                                                "revision": package["revision"]})
    report_path = out / "offline-evidence-report.json"
    write_json(report_path, {
        "run_id": args.run_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "route": "supplied_markdown", "semantic_scoring": "not_run",
        "provider_calls": 0, "gold_sha256": gold_sha,
        "source_manifest_sha256": digest(source_manifest_path),
        "recipe_sha256": digest(Path(__file__)),
        "evidence_manifest_sha256": digest(manifest_path),
        "package_ref": {"package_id": package["package_id"], "revision": package["revision"]},
        "unit_count": len(content["resources"]), "gate_failures": gate_failures,
        "embedded_image_entries": image_entries,
        "issues": content["issues"], "readiness": content["readiness"],
    })
    with SQLiteExperimentLedger(database, private_root=private_root) as ledger:
        ledger.create_run(run_id=args.run_id, suite="of-conks-cons-v21",
                          source_manifest_sha256=digest(source_manifest_path),
                          frozen_gold_sha256=gold_sha, recipe_sha256=digest(Path(__file__)),
                          recovery_route="supplied_markdown", provider_exposure="none",
                          provider=None, model=None, call_cap=0, spend_cap_usd=0)
        ledger.record_artifact(run_id=args.run_id, role="evidence_manifest", name="primary", path=manifest_path)
        ledger.record_artifact(run_id=args.run_id, role="evidence_substrate", name="primary", path=report_path)
        ledger.record_artifact(run_id=args.run_id, role="evidence_package", name="primary",
                               path=package_store.path_for(package["package_id"], package["revision"]))
        ledger.close_run(args.run_id)
    print(json.dumps({"run_id": args.run_id, "units": len(content["resources"]),
                      "gate_failures": gate_failures, "issues": len(content["issues"]),
                      "provider_calls": 0}))


if __name__ == "__main__":
    main()
