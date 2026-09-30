"""Prepare or finalize a private, source-pinned gold review packet.

No provider calls occur here. A draft packet is mutable for reviewer input;
finalization writes a new immutable artifact and persistent ledger judgments.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from compositor.benchmark_review import build_review_packet, validate_review_packet
from compositor.experiment_ledger import SQLiteExperimentLedger
from compositor.package import CompositionError, JsonPackageStore


RUN_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$")


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CompositionError("review input must be a JSON object")
    return value


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def _expected_packet(ledger: SQLiteExperimentLedger, *, run_id: str,
                     gold_path: Path) -> dict[str, Any]:
    row = ledger.connection.execute(
        "SELECT suite, status, frozen_gold_sha256 FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None or row["status"] != "closed":
        raise CompositionError("review requires a closed experiment run")
    gold_sha = _digest(gold_path)
    gold = _json(gold_path)
    if gold_sha != row["frozen_gold_sha256"] or gold.get("suite") != row["suite"]:
        raise CompositionError("gold differs from frozen run pin")
    ledger.verify_artifact(run_id=run_id, role="first_result", name="primary")
    package_path = ledger.verify_artifact(run_id=run_id, role="assembled_package", name="primary")
    report_path = ledger.verify_artifact(run_id=run_id, role="run_report", name="primary")
    report = _json(report_path)
    if report.get("run_id") != run_id or not isinstance(report.get("supplied_markdown_sha256"), str):
        raise CompositionError("run report lacks exact semantic source identity")
    ref = _json(package_path)
    store = JsonPackageStore(package_path.parent.parent)
    package = store.load({"package_id": ref["package_id"], "revision": ref["revision"]})
    return build_review_packet(run_id=run_id, gold=gold, package=package,
                               gold_sha256=gold_sha,
                               source_sha256=report["supplied_markdown_sha256"])


def review_benchmark(*, mode: str, private_root: Path, database: Path,
                     run_id: str, gold_path: Path) -> dict[str, Any]:
    root = private_root.resolve()
    if not RUN_ID.fullmatch(run_id):
        raise CompositionError("invalid review run ID")
    if not database.resolve().is_relative_to(root) or not gold_path.resolve().is_relative_to(root):
        raise CompositionError("review database and gold must be inside private root")
    if not database.is_file() or not gold_path.is_file():
        raise CompositionError("review database and frozen gold must already exist")
    review_dir = (root / "reviews" / run_id).resolve()
    if not review_dir.is_relative_to(root):
        raise CompositionError("review directory escapes private root")
    draft_path = review_dir / "review-draft.json"
    final_path = review_dir / "adjudication.json"
    with SQLiteExperimentLedger(database, private_root=root) as ledger:
        expected = _expected_packet(ledger, run_id=run_id, gold_path=gold_path)
        if mode == "prepare":
            _write_new(draft_path, expected)
            return {"mode": "prepare", "run_id": run_id, "cases": len(expected["cases"]),
                    "draft_path": str(draft_path), "verdicts": "none"}
        if mode != "finalize":
            raise CompositionError("mode must be prepare or finalize")
        edited = _json(draft_path)
        summary = validate_review_packet(edited, expected=expected, require_complete=True)
        if final_path.exists():
            raise CompositionError("adjudication artifact already exists")
        artifact = {"format_version": 1, "packet": edited, "summary": summary,
                    "status": "complete_reviewed", "score_basis": "assembled_first_package"}
        _write_new(final_path, artifact)
        db = ledger.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            for case in edited["cases"]:
                review = case["review"]
                ledger.record_judgment(run_id=run_id, case_id=case["id"],
                                       result_role="assembled_package", verdict=review["verdict"],
                                       reviewer=review["reviewer"], rationale=review["rationale"])
            ledger.record_artifact(run_id=run_id, role="gold_adjudication", name="primary",
                                   path=final_path)
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        return {"mode": "finalize", "run_id": run_id, "summary": summary,
                "artifact_path": str(final_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "finalize"])
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--gold", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(review_benchmark(mode=args.mode, private_root=args.private_root,
                                      database=args.database, run_id=args.run_id,
                                      gold_path=args.gold), sort_keys=True))


if __name__ == "__main__":
    main()
