"""Generate project-authored Stage A/B artifacts with pinned RulesIngestion code.

Usage: PYTHONPATH=<blake3-dir> python scripts/build_public_evidence_fixture.py \
    --rules-ingestion-root /path/to/RulesIngestion
This is an offline fixture recipe. The PDF route uses Poppler text extraction,
while the Markdown route uses supplied text; neither route claims OCR recovery.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


PINNED_RULES_INGESTION_REF = "17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8"
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/public"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-ingestion-root", type=Path, required=True)
    args = parser.parse_args()
    owner = args.rules_ingestion_root.resolve()
    actual_ref = subprocess.check_output(["git", "-C", str(owner), "rev-parse", "HEAD"], text=True).strip()
    if actual_ref != PINNED_RULES_INGESTION_REF:
        raise SystemExit(f"RulesIngestion ref mismatch: {actual_ref}")
    sys.path.insert(0, str(owner))
    from extraction.ast_parser import parse_markdown_to_ast
    from extraction.gates_a import run_stage_a_gates
    from extraction.gates_b import run_stage_b_gates
    from extraction.page_source import render_page
    from extraction.stage_b import run_stage_b

    pdf = FIXTURE / "windmill-field-notes.pdf"
    markdown = FIXTURE / "windmill-field-notes.md"
    pdf_sha = sha256(pdf.read_bytes()).hexdigest()
    markdown_sha = sha256(markdown.read_bytes()).hexdigest()
    pdf_text = subprocess.check_output(["pdftotext", "-layout", str(pdf), "-"], text=True)
    pdf_text = pdf_text.rstrip("\f\n") + "\n"
    with TemporaryDirectory() as temp:
        fingerprint = render_page(pdf, 0, Path(temp)).fingerprint

    for route, raw in (("pdf_text", pdf_text), ("supplied_markdown", markdown.read_text(encoding="utf-8"))):
        page_dir = FIXTURE / "evidence" / route / "page-0"
        page_dir.mkdir(parents=True, exist_ok=True)
        ast = parse_markdown_to_ast(raw, fingerprint)
        stage_a_gates = run_stage_a_gates(raw, ast)
        stage_b = run_stage_b(ast, content_version=f"{route}-rules-ingestion-{PINNED_RULES_INGESTION_REF[:12]}")
        stage_b.gate_diagnostics = run_stage_b_gates(stage_b.units, ast_dict=ast.to_dict(), is_standalone=True)
        (page_dir / "stageA.surface.md").write_text(raw, encoding="utf-8")
        write_json(page_dir / "stageA.surface.ast.json", ast.to_dict())
        write_json(page_dir / "stageA.gate_diagnostics.json", [gate.to_dict() for gate in stage_a_gates])
        write_json(page_dir / "stageB.evidence_units.json", stage_b.to_dict())
        artifact_sha256 = {
            name: sha256((page_dir / name).read_bytes()).hexdigest()
            for name in ("stageA.surface.md", "stageA.surface.ast.json", "stageA.gate_diagnostics.json",
                         "stageB.evidence_units.json")
        }
        write_json(FIXTURE / "evidence" / route / "manifest.json", {
            "format_version": 1,
            "rules_ingestion_ref": PINNED_RULES_INGESTION_REF,
            "route": route,
            "source_pdf": "fixtures/public/windmill-field-notes.pdf",
            "source_pdf_sha256": pdf_sha,
            "supplied_markdown": "fixtures/public/windmill-field-notes.md" if route == "supplied_markdown" else None,
            "supplied_markdown_sha256": markdown_sha if route == "supplied_markdown" else None,
            "expected_page_indices": [0],
            "pages": [{"page_index": 0, "page_fingerprint": fingerprint,
                       "artifact_dir": "page-0", "artifact_sha256": artifact_sha256}],
            "expected_assets": [],
            "recovery_method": "poppler_pdftotext_layout" if route == "pdf_text" else "provided_markdown_override",
            "provider_calls": 0,
        })
        print(route, "units", len(stage_b.units), "A gates", len(stage_a_gates),
              "B gates", len(stage_b.gate_diagnostics))


if __name__ == "__main__":
    main()
