"""Prepare or finalize a private, source-verified Conks asset recovery review."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compositor import JsonPackageStore  # noqa: E402
from compositor.asset_benchmark import build_asset_review_packet  # noqa: E402
from compositor.asset_inventory import project_asset_references  # noqa: E402
from compositor.benchmark_review import validate_review_packet  # noqa: E402
from compositor.experiment_ledger import SQLiteExperimentLedger  # noqa: E402
from compositor.package import CompositionError  # noqa: E402


RUN_ID = "conks-asset-recovery-v4-004"
SOURCE_SHA = "eebebb2f802ce31ba5a0be763db37a1dcac6e4d94e02c79b746caac5ee933b2a"
GOLD_SHA = "0f0b570000e68d11534a4f38eec0e19b92112e1c6fa22ff3709f5ab09f5ce01b"
ASSET_SHA = "8c76c676572da58421a502c7215cca10cfda7a5231e96515dc3286153c30ad2e"
PACKAGE_ID = "conks-evidence-conks-md-substrate-001-illustrated-assets-conks-illustrated-assets-002"
PACKAGE_REV = "a2052f59793b1da38c0663fb62b140b0fefcf0a423199c8acddf2599c926d7b9"


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _recipe_sha256() -> str:
    """Pin this driver and every local module that decides the adjudication."""
    paths = [Path(__file__), *(ROOT / "src/compositor" / name for name in (
        "asset_benchmark.py", "asset_inventory.py", "benchmark_review.py",
        "experiment_ledger.py", "package.py"))]
    digest = sha256()
    for path in paths:
        digest.update(str(path.resolve().relative_to(ROOT)).encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CompositionError("asset review input must be an object")
    return value


def _encoded(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def _write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        try:
            stream.write(_encoded(value))
        except BaseException:
            path.unlink(missing_ok=True)
            raise


def _expected(private_root: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    root = private_root.resolve()
    gold_dir = root / "gold/conks-v4"
    source_path = gold_dir / "source_manifest.json"
    gold_path = gold_dir / "proposal.json"
    freeze_path = gold_dir / "freeze-record.json"
    asset_dir = root / "runs/conks-illustrated-assets-002"
    asset_path = asset_dir / "asset-manifest.json"
    package_store = JsonPackageStore(asset_dir / "packages")
    package_ref = {"package_id": PACKAGE_ID, "revision": PACKAGE_REV}
    package_path = package_store.path_for(**package_ref)
    for path, expected in ((source_path, SOURCE_SHA), (gold_path, GOLD_SHA), (asset_path, ASSET_SHA)):
        if _digest(path) != expected:
            raise CompositionError(f"private pin mismatch: {path.name}")
    freeze = _read_json(freeze_path)
    if (freeze.get("status") != "frozen" or freeze.get("proposal_version") != 4
            or freeze.get("files", {}).get("proposal.json", {}).get("sha256") != GOLD_SHA
            or freeze.get("files", {}).get("source_manifest.json", {}).get("sha256") != SOURCE_SHA):
        raise CompositionError("Conks v4 freeze record differs from run pins")
    source = _read_json(source_path)
    gold = _read_json(gold_path)
    asset = _read_json(asset_path)
    package = package_store.load(package_ref)
    # Independent image-to-PDF recheck, including the package's exact revision.
    with TemporaryDirectory(prefix="compositor-asset-review-") as temp:
        repro = project_asset_references(
            base_store=JsonPackageStore(root / "runs/conks-md-substrate-001/packages"),
            base_ref=asset["base_package_ref"], output_store=JsonPackageStore(Path(temp)),
            package_id=PACKAGE_ID, manifest_path=asset_path,
            expected_manifest_sha256=ASSET_SHA, private_root=root)
        if repro["revision"] != PACKAGE_REV or repro != package:
            raise CompositionError("asset package differs from independent PDF replay")
    packet = build_asset_review_packet(
        run_id=RUN_ID, gold=gold, source_manifest=source,
        asset_manifest=asset, package=package, gold_sha256=GOLD_SHA,
        source_manifest_sha256=SOURCE_SHA, asset_manifest_sha256=ASSET_SHA)
    return packet, {"source": source_path, "gold": gold_path,
                    "asset": asset_path, "package": package_path}


def review(mode: str, private_root: Path) -> dict[str, Any]:
    root = private_root.resolve()
    if not root.is_dir():
        raise CompositionError("private root missing")
    packet, paths = _expected(root)
    review_dir = root / "reviews" / RUN_ID
    context_path = review_dir / "review-context.json"
    draft_path = review_dir / "review-draft.json"
    final_path = review_dir / "adjudication.json"
    database = root / "experiments.sqlite3"
    if mode == "prepare":
        if context_path.exists() or draft_path.exists():
            raise CompositionError("asset review packet already prepared")
        with SQLiteExperimentLedger(database, private_root=root) as ledger:
            if ledger.connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (RUN_ID,)).fetchone():
                raise CompositionError("asset review run already exists")
            db = ledger.connection
            created: list[Path] = []
            committed = False
            db.execute("BEGIN IMMEDIATE")
            try:
                _write_new(context_path, packet)
                created.append(context_path)
                _write_new(draft_path, packet)
                created.append(draft_path)
                ledger.create_run(run_id=RUN_ID, suite="of-conks-cons-v21",
                                  source_manifest_sha256=SOURCE_SHA, frozen_gold_sha256=GOLD_SHA,
                                  recipe_sha256=_recipe_sha256(),
                                  recovery_route="supplied_markdown_plus_illustrated_assets",
                                  provider_exposure="none", provider=None, model=None,
                                  call_cap=0, spend_cap_usd=0)
                for role, path in (("source_manifest", paths["source"]),
                                   ("frozen_gold", paths["gold"]),
                                   ("asset_manifest", paths["asset"]),
                                   ("asset_package", paths["package"]),
                                   ("asset_review_context", context_path)):
                    ledger.record_artifact(run_id=RUN_ID, role=role, name="primary", path=path)
                if db.execute("UPDATE runs SET status = 'closed' WHERE run_id = ? AND status = 'active'",
                              (RUN_ID,)).rowcount != 1:
                    raise CompositionError("asset review run did not close")
                db.execute("COMMIT")
                committed = True
            except BaseException:
                if not committed:
                    if db.in_transaction:
                        db.execute("ROLLBACK")
                    for path in reversed(created):
                        path.unlink(missing_ok=True)
                raise
            summary = ledger.summary(RUN_ID)
        return {"mode": mode, "packet_status": packet["status"],
                "cases": [item["id"] for item in packet["cases"]],
                "observed_recovery": {item["id"]: item["observed_recovery"] for item in packet["cases"]},
                "semantic_competence": "not_assessed", "task_competence": "not_assessed",
                "ledger": summary, "draft_path": str(draft_path)}
    if mode != "finalize":
        raise CompositionError("mode must be prepare or finalize")
    if _read_json(context_path) != packet:
        raise CompositionError("immutable asset review context changed")
    edited = _read_json(draft_path)
    summary = validate_review_packet(edited, expected=packet, require_complete=True)
    final = {"format_version": 1, "status": "complete_reviewed",
             "score_basis": "asset_recovery_only", "packet": edited,
             "summary": summary, "semantic_competence": "not_assessed",
             "task_competence": "not_assessed"}
    with SQLiteExperimentLedger(database, private_root=root) as ledger:
        row = ledger.connection.execute("SELECT * FROM runs WHERE run_id = ?", (RUN_ID,)).fetchone()
        if (row is None or row["status"] != "closed" or row["frozen_gold_sha256"] != GOLD_SHA
                or row["recipe_sha256"] != _recipe_sha256()):
            raise CompositionError("closed pinned asset review run required")
        ledger.verify_artifact(run_id=RUN_ID, role="asset_review_context", name="primary")
        ledger.verify_artifact(run_id=RUN_ID, role="asset_package", name="primary")
        already_finalized = final_path.exists()
        if already_finalized:
            if final_path.read_text(encoding="utf-8") != _encoded(final):
                raise CompositionError("existing asset adjudication differs")
        else:
            _write_new(final_path, final)
        db = ledger.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            for case in edited["cases"]:
                judgement = case["review"]
                existing = db.execute("""SELECT verdict, rationale FROM judgments
                    WHERE run_id = ? AND case_id = ? AND result_role = 'asset_recovery_package'
                      AND reviewer = ?""", (RUN_ID, case["id"], judgement["reviewer"])).fetchone()
                if existing is None:
                    ledger.record_judgment(run_id=RUN_ID, case_id=case["id"],
                                           result_role="asset_recovery_package",
                                           verdict=judgement["verdict"],
                                           reviewer=judgement["reviewer"],
                                           rationale=judgement["rationale"])
                elif (existing["verdict"], existing["rationale"]) != \
                        (judgement["verdict"], judgement["rationale"]):
                    raise CompositionError(f"conflicting asset judgment for {case['id']}")
            recorded = db.execute("""SELECT 1 FROM artifacts WHERE run_id = ?
                AND role = 'asset_adjudication' AND name = 'primary'""", (RUN_ID,)).fetchone()
            if recorded is None:
                ledger.record_artifact(run_id=RUN_ID, role="asset_adjudication",
                                       name="primary", path=final_path)
            elif ledger.verify_artifact(run_id=RUN_ID, role="asset_adjudication",
                                        name="primary") != final_path:
                raise CompositionError("recorded asset adjudication path differs")
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
    return {"mode": mode, "summary": summary, "artifact_path": str(final_path),
            "already_finalized": already_finalized}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "finalize"])
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(review(args.mode, args.private_root), sort_keys=True))


if __name__ == "__main__":
    main()
