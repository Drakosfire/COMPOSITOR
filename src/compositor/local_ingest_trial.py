"""Bounded offline LOCAL-INGEST-001 pilot harness; no gold or provider adapter.

The input manifest and every evidence/model/backend byte are pinned before calls.
A schedule is written before execution, raw outputs are never overwritten, and
candidate outputs are frozen before the local typed-decision phase begins.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any

from .package import CompositionError

HEX64 = re.compile(r"^[0-9a-f]{64}$")
CASE_ID = re.compile(r"^[a-z][a-z0-9_-]{0,79}$")
OUTCOMES = ("resolved", "reference-only", "unsupported", "unresolved", "false_premise_rejected")
MAX_CASES = 4
MAX_CALLS = 8
MAX_EVIDENCE = 6
MAX_CONTEXT = 8192
MAX_OUTPUT = 1024
MAX_DEADLINE_SECONDS = 60


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _pinned_file(path: str, expected: str, label: str) -> Path:
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise CompositionError(f"{label} needs an absolute path")
    item = Path(path).resolve(strict=True)
    if not item.is_file() or not isinstance(expected, str) or not HEX64.fullmatch(expected):
        raise CompositionError(f"invalid {label} pin")
    if digest(item) != expected:
        raise CompositionError(f"{label} revision mismatch")
    return item


def _inside_private(path: Path, private_root: Path, label: str) -> Path:
    root = private_root.resolve(strict=True)
    item = path.resolve()
    if not item.is_relative_to(root):
        raise CompositionError(f"{label} must be inside private root")
    return item


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CompositionError("manifest must be a JSON object")
    return value


def _unit(artifact: Path, unit_id: str) -> dict[str, Any]:
    doc = _object(artifact)
    units = doc.get("units")
    if not isinstance(units, list):
        raise CompositionError("evidence artifact lacks units")
    found = [u for u in units if isinstance(u, dict) and u.get("unit_id") == unit_id]
    if len(found) != 1 or not isinstance(found[0].get("text"), str) or not found[0]["text"].strip():
        raise CompositionError("missing or ambiguous evidence unit")
    return found[0]


def load_plan(manifest_path: Path, *, private_root: Path) -> dict[str, Any]:
    """Validate all pins and build model inputs without reading reference/gold."""
    manifest_path = _inside_private(Path(manifest_path), private_root, "manifest")
    manifest = _object(manifest_path)
    if manifest.get("format_version") != 1 or manifest.get("experiment_id") != "LOCAL-INGEST-001":
        raise CompositionError("wrong experiment manifest")
    if any("gold" in key or "reference_path" in key for key in manifest):
        raise CompositionError("model manifest must not carry gold")
    reference_sha = manifest.get("reference_sha256")
    if not isinstance(reference_sha, str) or not HEX64.fullmatch(reference_sha):
        raise CompositionError("separate frozen reference digest required")
    backend, model = manifest.get("backend"), manifest.get("model")
    if not isinstance(backend, dict) or not isinstance(model, dict):
        raise CompositionError("backend and model pins required")
    backend_path = _pinned_file(backend.get("path"), backend.get("sha256"), "backend")
    model_path = _pinned_file(model.get("path"), model.get("sha256"), "model")
    settings = manifest.get("settings")
    if not isinstance(settings, dict):
        raise CompositionError("settings required")
    limits = (("context_tokens", 1, MAX_CONTEXT), ("output_tokens", 1, MAX_OUTPUT),
              ("deadline_seconds", 1, MAX_DEADLINE_SECONDS), ("gpu_layers", 0, 99))
    for key, low, high in limits:
        value = settings.get(key)
        if type(value) is not int or not low <= value <= high:
            raise CompositionError(f"invalid {key}")
    if settings.get("temperature") != 0 or type(settings.get("seed")) is not int:
        raise CompositionError("temperature zero and integer seed required")
    if settings.get("offline") is not True or settings.get("concurrency") != 1 or settings.get("retries") != 0:
        raise CompositionError("offline, single-concurrency, no-retry settings required")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_CASES:
        raise CompositionError("one to four cases required")
    if len(cases) * 2 > MAX_CALLS:
        raise CompositionError("local call cap exceeded")
    prepared = []
    seen = set()
    for case in cases:
        if not isinstance(case, dict):
            raise CompositionError("case must be an object")
        cid, question, track = case.get("id"), case.get("question"), case.get("track")
        if not isinstance(cid, str) or not CASE_ID.fullmatch(cid) or cid in seen:
            raise CompositionError("duplicate or invalid case id")
        seen.add(cid)
        if track not in {"rule", "adventure"} or not isinstance(question, str) or not question.strip():
            raise CompositionError("case needs track and question")
        source = case.get("source")
        if not isinstance(source, dict) or not isinstance(source.get("document_id"), str) or not source["document_id"].strip():
            raise CompositionError("case needs source identity")
        if source.get("audience") not in {"GM", "PLAYER", "ALL"} or not isinstance(source.get("edition"), str):
            raise CompositionError("case needs audience and edition")
        _pinned_file(source.get("path"), source.get("sha256"), "source")
        evidence = case.get("evidence")
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= MAX_EVIDENCE:
            raise CompositionError("one to six evidence units required")
        prepared_evidence = []
        seen_units = set()
        for item in evidence:
            if not isinstance(item, dict):
                raise CompositionError("evidence pin must be an object")
            artifact = _pinned_file(item.get("path"), item.get("sha256"), "evidence")
            unit_id = item.get("unit_id")
            if not isinstance(unit_id, str) or not HEX64.fullmatch(unit_id):
                raise CompositionError("unit id must be a SHA-256 identity")
            if unit_id in seen_units:
                raise CompositionError("duplicate evidence unit")
            seen_units.add(unit_id)
            unit = _unit(artifact, unit_id)
            prepared_evidence.append({"unit_id": unit_id, "artifact_sha256": item["sha256"],
                                      "text": unit["text"], "structural_path": unit.get("structural_path", []),
                                      "anomaly_flags": unit.get("anomaly_flags", [])})
        prepared.append({"id": cid, "track": track, "question": question,
                         "source_document_id": source["document_id"],
                         "source_sha256": source["sha256"], "audience": source["audience"],
                         "edition": source["edition"], "evidence": prepared_evidence})
    return {"manifest_sha256": digest(manifest_path), "backend_path": str(backend_path),
            "backend_sha256": backend["sha256"], "model_path": str(model_path),
            "model_sha256": model["sha256"], "settings": settings, "cases": prepared,
            "reference_sha256": reference_sha}


def _write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def _evidence_prompt(case: dict[str, Any]) -> str:
    lines = ["Use only the source units below. Preserve uncertainty and source identity.",
             "Document: " + case["source_document_id"] + "; edition: " + case["edition"] +
             "; audience: " + case["audience"] + "; source SHA-256: " + case["source_sha256"],
             "Return JSON with keys candidates (array), answer, source_unit_ids (array), outcome.",
             "Outcomes: " + ", ".join(OUTCOMES) + ".", "Question: " + case["question"]]
    for item in case["evidence"]:
        lines.append("SOURCE_UNIT " + item["unit_id"] + "\n" + item["text"])
    return "\n\n".join(lines)


def _decision_prompt(case: dict[str, Any], candidate: dict[str, Any]) -> str:
    return ("Make a typed decision using only these source units and candidate output. "
            "Return JSON with keys outcome, selected_candidate_ids, source_unit_ids, rationale. "
            "Allowed outcomes: " + ", ".join(OUTCOMES) + ".\n\n" +
            _evidence_prompt(case) + "\n\nFROZEN_CANDIDATE\n" +
            json.dumps(candidate, ensure_ascii=False, sort_keys=True))


def _parsed_object(raw: str, required_key: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    selected = None
    for match in re.finditer(r"\{", raw):
        try:
            value, _ = decoder.raw_decode(raw[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and required_key in value:
            selected = value
    return selected


def _call(plan: dict[str, Any], prompt: str, prompt_path: Path) -> dict[str, Any]:
    settings = plan["settings"]
    prompt_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(prompt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(prompt)
    command = [plan["backend_path"], "--offline", "-m", plan["model_path"],
               "-f", str(prompt_path), "-n", str(settings["output_tokens"]), "-c",
               str(settings["context_tokens"]), "-ngl", str(settings["gpu_layers"]),
               "-s", str(settings["seed"]), "--temp", "0", "--single-turn",
               "--simple-io", "--no-display-prompt"]
    environment = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "HF_HUB_OFFLINE": "1"}
    start = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=settings["deadline_seconds"], env=environment)
        return {"status": "completed" if result.returncode == 0 else "backend_failed",
                "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
                "wall_seconds": time.monotonic() - start, "prompt_sha256": sha256(prompt.encode()).hexdigest(),
                "command": command}
    except subprocess.TimeoutExpired as error:
        def decoded(value: str | bytes | None) -> str:
            return value.decode(errors="replace") if isinstance(value, bytes) else (value or "")
        return {"status": "timeout", "exit_code": None, "stdout": decoded(error.stdout),
                "stderr": decoded(error.stderr), "wall_seconds": time.monotonic() - start,
                "prompt_sha256": sha256(prompt.encode()).hexdigest(),
                "command": command}
    except OSError as error:
        return {"status": "backend_failed", "exit_code": None, "stdout": "", "stderr": str(error),
                "wall_seconds": time.monotonic() - start, "prompt_sha256": sha256(prompt.encode()).hexdigest(),
                "command": command}


def run_trial(manifest_path: Path, *, private_root: Path, run_dir: Path) -> dict[str, Any]:
    """Execute one bounded D/L run. Never opens the separate pilot reference packet."""
    plan = load_plan(manifest_path, private_root=private_root)
    run_dir = _inside_private(Path(run_dir), private_root, "run directory")
    run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    schedule = {"format_version": 1, "experiment_id": "LOCAL-INGEST-001",
                "manifest_sha256": plan["manifest_sha256"], "backend_sha256": plan["backend_sha256"],
                "model_sha256": plan["model_sha256"], "settings": plan["settings"],
                "reference_sha256_not_loaded": plan["reference_sha256"],
                "case_ids": [c["id"] for c in plan["cases"]], "scheduled_calls": len(plan["cases"]) * 2,
                "cases": plan["cases"], "provider_calls": 0}
    _write_new(run_dir / "schedule.json", schedule)
    calls = []
    candidates = {}
    stop_reason = None
    for case in plan["cases"]:
        if stop_reason:
            candidates[case["id"]] = {"status": "skipped_after_backend_failure"}
            continue
        result = _call(plan, _evidence_prompt(case), run_dir / "prompts" / f"{len(calls) + 1:02d}-{case['id']}-generate.txt")
        _write_new(run_dir / "calls" / f"{len(calls) + 1:02d}-{case['id']}-generate.json", result)
        calls.append({"case_id": case["id"], "phase": "generate", "status": result["status"]})
        candidate = _parsed_object(result["stdout"], "candidates") if result["status"] == "completed" else None
        candidates[case["id"]] = {"status": "parsed" if candidate is not None else
                                   ("invalid_output" if result["status"] == "completed" else result["status"]),
                                   "candidate": candidate}
        if result["status"] in {"backend_failed", "timeout"}:
            stop_reason = result["status"]
    _write_new(run_dir / "candidate-freeze.json", {"cases": candidates,
               "case_ids": schedule["case_ids"], "status": "frozen_before_decisions"})
    decisions = {}
    for case in plan["cases"]:
        candidate = candidates[case["id"]]
        if stop_reason or candidate.get("status") != "parsed":
            decisions[case["id"]] = {"status": "skipped_after_backend_failure" if stop_reason else
                                     "skipped_invalid_candidate"}
            continue
        result = _call(plan, _decision_prompt(case, candidate["candidate"]),
                       run_dir / "prompts" / f"{len(calls) + 1:02d}-{case['id']}-decide.txt")
        _write_new(run_dir / "calls" / f"{len(calls) + 1:02d}-{case['id']}-decide.json", result)
        calls.append({"case_id": case["id"], "phase": "decide", "status": result["status"]})
        value = _parsed_object(result["stdout"], "outcome") if result["status"] == "completed" else None
        if value is not None and value.get("outcome") not in OUTCOMES:
            value = None
        decisions[case["id"]] = {"status": "parsed" if value is not None else
                                  ("invalid_output" if result["status"] == "completed" else result["status"]),
                                  "decision": value}
        if result["status"] in {"backend_failed", "timeout"}:
            stop_reason = result["status"]
    summary = {"format_version": 1, "case_count": len(plan["cases"]), "scheduled_calls": len(plan["cases"]) * 2,
               "actual_calls": len(calls), "calls": calls, "candidates": candidates,
               "decisions": decisions, "stop_reason": stop_reason, "provider_calls": 0,
               "reference_sha256_not_loaded": plan["reference_sha256"]}
    _write_new(run_dir / "summary.json", summary)
    return {"run_dir": str(run_dir), "summary_sha256": digest(run_dir / "summary.json"),
            "case_count": summary["case_count"], "actual_calls": summary["actual_calls"],
            "stop_reason": stop_reason}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "run"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.command == "validate":
        plan = load_plan(args.manifest, private_root=args.private_root)
        print(json.dumps({"manifest_sha256": plan["manifest_sha256"],
                          "case_ids": [c["id"] for c in plan["cases"]],
                          "scheduled_calls": len(plan["cases"]) * 2}, sort_keys=True))
    else:
        if not args.execute or args.run_dir is None:
            parser.error("run requires --execute and --run-dir")
        print(json.dumps(run_trial(args.manifest, private_root=args.private_root,
                                   run_dir=args.run_dir), sort_keys=True))


if __name__ == "__main__":
    main()
