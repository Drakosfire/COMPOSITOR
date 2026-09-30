"""Prepare and finalize a private review of an owner A/B first result.

Preparation leaves all verdicts blank. Finalization rebuilds the packet from
the pinned first result and frozen gold before accepting human judgments.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from compositor.benchmark_review import validate_review_packet
from compositor.experiment_ledger import SQLiteExperimentLedger
from compositor.owner_evidence_first import build_owner_review_packet
from compositor.package import CompositionError


RUN_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CompositionError("review input must be a JSON object")
    return value


def encoded(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encoded(value))


def review_owner_first(*, mode: str, private_root: Path, database: Path,
                       run_id: str, gold_path: Path,
                       freeze_record_path: Path) -> dict[str, Any]:
    root = private_root.resolve()
    if not RUN_ID.fullmatch(run_id):
        raise CompositionError("invalid review run ID")
    for path in (database, gold_path, freeze_record_path):
        if not path.resolve().is_relative_to(root) or not path.is_file():
            raise CompositionError("review inputs must exist inside private root")
    review_dir = root / "reviews" / run_id / "owner-evidence"
    draft_path = review_dir / "review-draft.json"
    final_path = review_dir / "adjudication.json"
    with SQLiteExperimentLedger(database, private_root=root) as ledger:
        run = ledger.connection.execute(
            "SELECT suite, status, source_manifest_sha256, frozen_gold_sha256 "
            "FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if run is None or run["status"] != "closed":
            raise CompositionError("review requires a closed owner experiment run")
        first_path = ledger.verify_artifact(run_id=run_id, role="first_result",
                                            name="primary")
        first_sha = digest(first_path)
        gold_sha = digest(gold_path)
        if gold_sha != run["frozen_gold_sha256"]:
            raise CompositionError("gold differs from frozen run pin")
        expected = build_owner_review_packet(
            first_result_path=first_path, first_result_sha256=first_sha,
            gold_path=gold_path, gold_sha256=gold_sha,
            freeze_record_path=freeze_record_path,
            freeze_record_sha256=digest(freeze_record_path),
        )
        if (expected["suite"] != run["suite"] or
                expected["source_manifest_sha256"] != run["source_manifest_sha256"]):
            raise CompositionError("owner first result differs from run identity")
        if mode == "prepare":
            write_new(draft_path, expected)
            return {"mode": mode, "run_id": run_id, "cases": len(expected["cases"]),
                    "draft_path": str(draft_path), "verdicts": "none"}
        if mode != "finalize":
            raise CompositionError("mode must be prepare or finalize")
        edited = read_json(draft_path)
        summary = validate_review_packet(edited, expected=expected, require_complete=True)
        artifact = {"format_version": 1, "packet": edited, "summary": summary,
                    "status": "complete_reviewed",
                    "score_basis": "owner_ab_first_source_package"}
        if final_path.exists():
            if final_path.read_text(encoding="utf-8") != encoded(artifact):
                raise CompositionError("existing owner adjudication has different bytes")
        else:
            write_new(final_path, artifact)
        recorded = ledger.connection.execute(
            "SELECT 1 FROM artifacts WHERE run_id = ? "
            "AND role = 'owner_gold_adjudication' AND name = 'primary'",
            (run_id,)).fetchone()
        if recorded is not None:
            if ledger.verify_artifact(run_id=run_id, role="owner_gold_adjudication",
                                      name="primary") != final_path:
                raise CompositionError("recorded owner adjudication path differs")
            return {"mode": mode, "run_id": run_id, "summary": summary,
                    "artifact_path": str(final_path), "already_finalized": True}
        db = ledger.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            for case in edited["cases"]:
                review = case["review"]
                ledger.record_judgment(
                    run_id=run_id, case_id=case["id"],
                    result_role="owner_first_package", verdict=review["verdict"],
                    reviewer=review["reviewer"], rationale=review["rationale"])
            ledger.record_artifact(run_id=run_id, role="owner_gold_adjudication",
                                   name="primary", path=final_path)
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        return {"mode": mode, "run_id": run_id, "summary": summary,
                "artifact_path": str(final_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "finalize"))
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--freeze-record", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(review_owner_first(
        mode=args.mode, private_root=args.private_root, database=args.database,
        run_id=args.run_id, gold_path=args.gold,
        freeze_record_path=args.freeze_record), sort_keys=True))


if __name__ == "__main__":
    main()
