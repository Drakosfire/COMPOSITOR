"""Private SQLite ledger for reproducible ingestion experiments.

The database records manifests, immutable artifact references, judgments, and
provider observations. Source bytes and prompts stay in the caller's private
artifact directory, not in receipt rows.
"""

from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
import re
import sqlite3
from typing import Any

from .package import CompositionError


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$")


def _digest(value: str, label: str) -> str:
    if not _HEX64.fullmatch(value):
        raise CompositionError(f"{label} must be a SHA-256 digest")
    return value


def _name(value: str, label: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise CompositionError(f"invalid {label}")
    return value


class SQLiteExperimentLedger:
    """One isolated persistent experiment namespace under a private root."""

    def __init__(self, path: Path, *, private_root: Path):
        self.private_root = Path(private_root).resolve()
        self.path = Path(path).resolve()
        if not self.path.is_relative_to(self.private_root):
            raise CompositionError("experiment database must be inside the private root")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._initialize()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> SQLiteExperimentLedger:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _initialize(self) -> None:
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            raise CompositionError(f"unsupported experiment schema version {version}")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                suite TEXT NOT NULL,
                source_manifest_sha256 TEXT NOT NULL,
                frozen_gold_sha256 TEXT NOT NULL,
                recipe_sha256 TEXT NOT NULL,
                recovery_route TEXT NOT NULL,
                provider_exposure TEXT NOT NULL,
                provider TEXT,
                model TEXT,
                call_cap INTEGER NOT NULL CHECK (call_cap >= 0),
                spend_cap_usd REAL NOT NULL CHECK (spend_cap_usd >= 0),
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                role TEXT NOT NULL,
                name TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, role, name)
            );
            CREATE TABLE IF NOT EXISTS calls (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                call_index INTEGER NOT NULL,
                reserved_usd REAL NOT NULL CHECK (reserved_usd > 0),
                actual_cost_usd REAL,
                provider TEXT,
                requested_model TEXT,
                resolved_model TEXT,
                response_model TEXT,
                request_id TEXT,
                response_id TEXT,
                input_tokens INTEGER,
                cached_input_tokens INTEGER,
                output_tokens INTEGER,
                pricing_source TEXT,
                state TEXT NOT NULL DEFAULT 'reserved',
                failure_code TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, call_index)
            );
            CREATE TABLE IF NOT EXISTS judgments (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                case_id TEXT NOT NULL,
                result_role TEXT NOT NULL,
                verdict TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                rationale TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, case_id, result_role, reviewer)
            );
            PRAGMA user_version = 1;
        """)

    def create_run(self, *, run_id: str, suite: str, source_manifest_sha256: str,
                   frozen_gold_sha256: str, recipe_sha256: str,
                   recovery_route: str, provider_exposure: str,
                   provider: str | None, model: str | None,
                   call_cap: int, spend_cap_usd: float) -> None:
        _name(run_id, "run id")
        _name(suite, "suite")
        for label, value in (("source manifest", source_manifest_sha256),
                             ("frozen gold", frozen_gold_sha256),
                             ("recipe", recipe_sha256)):
            _digest(value, label)
        if provider_exposure not in {"none", "approved_private_api"}:
            raise CompositionError("provider exposure decision required")
        if (not isinstance(call_cap, int) or call_cap < 0 or not isinstance(spend_cap_usd, (int, float))
                or not math.isfinite(spend_cap_usd) or spend_cap_usd < 0):
            raise CompositionError("finite nonnegative call and spend caps required")
        if provider_exposure == "none" and (provider or model or call_cap or spend_cap_usd):
            raise CompositionError("offline run cannot reserve provider budget")
        if provider_exposure != "none" and (not provider or not model or call_cap == 0 or spend_cap_usd == 0):
            raise CompositionError("live run needs provider, model, and positive caps")
        self.connection.execute("""
            INSERT INTO runs (run_id, suite, source_manifest_sha256, frozen_gold_sha256,
                              recipe_sha256, recovery_route, provider_exposure, provider,
                              model, call_cap, spend_cap_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, suite, source_manifest_sha256, frozen_gold_sha256, recipe_sha256,
              recovery_route, provider_exposure, provider, model, call_cap, spend_cap_usd))

    def record_artifact(self, *, run_id: str, role: str, name: str, path: Path) -> str:
        _name(role, "artifact role")
        _name(name, "artifact name")
        if role == "first_result" and name != "primary":
            raise CompositionError("first result must use the single primary slot")
        exact = Path(path).resolve()
        if not exact.is_relative_to(self.private_root) or not exact.is_file():
            raise CompositionError("artifact must be an existing file inside the private root")
        digest = sha256(exact.read_bytes()).hexdigest()
        self.connection.execute("""
            INSERT INTO artifacts (run_id, role, name, relative_path, sha256)
            VALUES (?, ?, ?, ?, ?)
        """, (run_id, role, name, str(exact.relative_to(self.private_root)), digest))
        return digest

    def verify_artifact(self, *, run_id: str, role: str, name: str) -> Path:
        row = self.connection.execute("""
            SELECT relative_path, sha256 FROM artifacts
            WHERE run_id = ? AND role = ? AND name = ?
        """, (run_id, role, name)).fetchone()
        if row is None:
            raise CompositionError("recorded artifact not found")
        path = (self.private_root / row["relative_path"]).resolve()
        if not path.is_relative_to(self.private_root) or not path.is_file():
            raise CompositionError("recorded artifact unavailable")
        if sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise CompositionError("recorded artifact integrity mismatch")
        return path

    def reserve_call(self, *, run_id: str, maximum_cost_usd: float) -> int:
        if not math.isfinite(maximum_cost_usd) or maximum_cost_usd <= 0:
            raise CompositionError("call needs a positive maximum cost")
        db = self.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            run = db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if run is None or run["status"] != "active":
                raise CompositionError("live run unavailable")
            if run["provider_exposure"] == "none":
                raise CompositionError("offline run cannot reserve a provider call")
            calls = db.execute("SELECT COUNT(*) FROM calls WHERE run_id = ?", (run_id,)).fetchone()[0]
            charged = db.execute("""
                SELECT COALESCE(SUM(CASE WHEN actual_cost_usd IS NULL
                    THEN reserved_usd ELSE actual_cost_usd END), 0)
                FROM calls WHERE run_id = ?
            """, (run_id,)).fetchone()[0]
            if calls >= run["call_cap"] or charged + maximum_cost_usd > run["spend_cap_usd"] + 1e-9:
                raise CompositionError("experiment call or spend cap reached")
            index = calls + 1
            db.execute("INSERT INTO calls (run_id, call_index, reserved_usd) VALUES (?, ?, ?)",
                       (run_id, index, maximum_cost_usd))
            db.execute("COMMIT")
            return index
        except BaseException:
            db.execute("ROLLBACK")
            raise

    def record_observation(self, *, run_id: str, call_index: int,
                           state: str, provider: str | None, requested_model: str | None,
                           resolved_model: str | None = None,
                           response_model: str | None = None,
                           request_id: str | None = None, response_id: str | None = None,
                           input_tokens: int | None = None,
                           cached_input_tokens: int | None = None,
                           output_tokens: int | None = None,
                           cost_usd: float | None = None,
                           pricing_source: str | None = None,
                           failure_code: str | None = None) -> None:
        if state not in {"completed", "refused", "failed", "incomplete"}:
            raise CompositionError("invalid provider observation state")
        if cost_usd is not None and (not math.isfinite(cost_usd) or cost_usd < 0):
            raise CompositionError("negative provider cost")
        db = self.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            row = db.execute("""
                SELECT calls.state, runs.provider, runs.model
                FROM calls JOIN runs USING (run_id)
                WHERE run_id = ? AND call_index = ?
            """, (run_id, call_index)).fetchone()
            if row is None or row["state"] != "reserved":
                raise CompositionError("pending call reservation not found")
            if provider != row["provider"] or requested_model != row["model"]:
                raise CompositionError("observation provider or model differs from run pin")
            db.execute("""
                UPDATE calls SET state = ?, provider = ?, requested_model = ?,
                    resolved_model = ?, response_model = ?, request_id = ?, response_id = ?,
                    input_tokens = ?, cached_input_tokens = ?, output_tokens = ?,
                    actual_cost_usd = ?, pricing_source = ?, failure_code = ?
                WHERE run_id = ? AND call_index = ?
            """, (state, provider, requested_model, resolved_model, response_model,
                  request_id, response_id, input_tokens, cached_input_tokens,
                  output_tokens, cost_usd, pricing_source, failure_code, run_id, call_index))
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise

    def record_judgment(self, *, run_id: str, case_id: str, result_role: str,
                        verdict: str, reviewer: str, rationale: str) -> None:
        if verdict not in {"pass", "material_gap", "critical_failure", "minor_gap", "unresolved"}:
            raise CompositionError("invalid judgment verdict")
        self.connection.execute("""
            INSERT INTO judgments (run_id, case_id, result_role, verdict, reviewer, rationale)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (run_id, case_id, result_role, verdict, reviewer, rationale))

    def close_run(self, run_id: str) -> None:
        db = self.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            pending = db.execute("SELECT COUNT(*) FROM calls WHERE run_id = ? AND state = 'reserved'",
                                 (run_id,)).fetchone()[0]
            if pending:
                raise CompositionError("cannot close run with pending provider receipts")
            changed = db.execute("UPDATE runs SET status = 'closed' WHERE run_id = ? AND status = 'active'",
                                 (run_id,)).rowcount
            if changed != 1:
                raise CompositionError("active run not found")
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise

    def summary(self, run_id: str) -> dict[str, Any]:
        run = self.connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if run is None:
            raise CompositionError("run not found")
        count, charged = self.connection.execute("""
            SELECT COUNT(*), COALESCE(SUM(CASE WHEN actual_cost_usd IS NULL
                THEN reserved_usd ELSE actual_cost_usd END), 0)
            FROM calls WHERE run_id = ?
        """, (run_id,)).fetchone()
        artifacts = self.connection.execute("SELECT role, COUNT(*) FROM artifacts WHERE run_id = ? GROUP BY role",
                                            (run_id,)).fetchall()
        return {"run_id": run_id, "suite": run["suite"], "status": run["status"],
                "call_count": count, "charged_or_reserved_usd": charged,
                "call_cap": run["call_cap"], "spend_cap_usd": run["spend_cap_usd"],
                "artifact_counts": {role: number for role, number in artifacts}}
