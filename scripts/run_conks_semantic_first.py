"""Bounded private first semantic treatment of pinned Conks page evidence.

Run with a Python environment containing GenerationEngine's OpenAI extra.
The script records raw provider output before assembling or scoring a package.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from compositor.experiment_ledger import SQLiteExperimentLedger
from compositor.package import JsonPackageStore
from compositor.semantic_first import (PAGE_SCHEMA, SYSTEM_PROMPT, assemble_first_result,
                                       digest, page_prompt, read_page_evidence)
from scripts.prepare_conks_offline_evidence import run_output_dir


MODEL = "gpt-5.6-luna"
CALL_CAP = 19
PROVIDER_ATTEMPT_CEILING = 2 * CALL_CAP  # GE ref permits one conformance retry; transport retries disabled.
MAX_OUTPUT_TOKENS = 8192
RESERVATION_USD = 0.05
SPEND_CAP_USD = CALL_CAP * RESERVATION_USD
PRICE_SOURCE = "https://developers.openai.com/api/docs/models/gpt-5.6-luna (checked 2026-09-30)"


def _json(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"expected JSON object: {path.name}")
    return result


def _write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def _env_key(path: Path) -> str:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("OPENAI_API_KEY="):
            value = line.split("=", 1)[1].strip().strip('"\'')
            if value:
                return value
    raise ValueError("OPENAI_API_KEY missing from private env file")


def _ge_ref(root: Path) -> str:
    status = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True)
    if status.strip():
        raise ValueError("GenerationEngine checkout must be clean for a pinned run")
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def _recipe_digest(ge_ref: str) -> str:
    files = [Path(__file__), Path(__file__).parents[1] / "src/compositor/semantic_first.py"]
    pins = {"files": {path.name: digest(path) for path in files}, "ge_ref": ge_ref,
            "model": MODEL, "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_transport_retries": 0, "reasoning_effort": "low",
            "provider_attempt_ceiling": PROVIDER_ATTEMPT_CEILING,
            "temperature": None, "system_prompt": SYSTEM_PROMPT, "schema": PAGE_SCHEMA,
            "reservation_usd": RESERVATION_USD, "price_source": PRICE_SOURCE}
    return sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()


def preflight(args: argparse.Namespace) -> tuple[Path, list[dict[str, Any]], dict[str, Any],
                                                 list[dict[str, Any]], str]:
    private_root = args.private_root.resolve()
    out = run_output_dir(private_root, args.run_id)
    database = args.database.resolve()
    if not database.is_relative_to(private_root):
        raise ValueError("database must be inside private root")
    if out.exists():
        raise ValueError("run output already exists")
    if not args.substrate_dir.resolve().is_relative_to(private_root):
        raise ValueError("substrate must be inside private root")
    for label, path in (("source manifest", args.source_manifest), ("frozen gold", args.gold)):
        if not path.resolve().is_relative_to(private_root):
            raise ValueError(f"{label} must be inside private root")
    source_manifest = _json(args.source_manifest)
    gold = _json(args.gold)
    if source_manifest.get("status") != "source_identity_accepted_for_frozen_gold":
        raise ValueError("source manifest is not accepted")
    if gold.get("status") != "frozen" or gold.get("suite") != source_manifest.get("suite"):
        raise ValueError("gold/source suite mismatch or gold not frozen")
    substrate = _json(args.substrate_dir / "offline-evidence-report.json")
    if substrate.get("source_manifest_sha256") != digest(args.source_manifest):
        raise ValueError("source manifest differs from substrate pin")
    if substrate.get("gold_sha256") != digest(args.gold):
        raise ValueError("frozen gold differs from substrate pin")
    evidence_dir = args.substrate_dir / "evidence/supplied_markdown"
    if substrate.get("evidence_manifest_sha256") != digest(evidence_dir / "manifest.json"):
        raise ValueError("evidence manifest differs from substrate pin")
    pages = read_page_evidence(evidence_dir)
    base_package = JsonPackageStore(args.substrate_dir / "packages").load(substrate["package_ref"])
    ge_ref = _ge_ref(args.generation_engine_root.resolve())
    if ge_ref != args.expected_ge_ref:
        raise ValueError("GenerationEngine ref differs from pinned expected ref")
    return out, pages, substrate, base_package.get("diagnostics", []), ge_ref


async def _run(args: argparse.Namespace) -> None:
    out, pages, substrate, diagnostics, ge_ref = preflight(args)
    recipe_sha = _recipe_digest(ge_ref)
    if args.preflight:
        print(json.dumps({"preflight": "passed", "pages": len(pages), "model": MODEL,
                          "logical_call_cap": CALL_CAP,
                          "provider_attempt_ceiling": PROVIDER_ATTEMPT_CEILING,
                          "spend_cap_usd": SPEND_CAP_USD,
                          "max_output_tokens": MAX_OUTPUT_TOKENS, "ge_ref": ge_ref,
                          "recipe_sha256": recipe_sha}, sort_keys=True))
        return
    os.environ["OPENAI_API_KEY"] = _env_key(args.env_file)
    sys.path.insert(0, str(args.generation_engine_root.resolve() / "src"))
    import generationengine
    from generationengine import GenerationClient, TextRequest
    from generationengine.types import GenerationEngineError
    if not Path(generationengine.__file__).resolve().is_relative_to(
            args.generation_engine_root.resolve() / "src"):
        raise ValueError("runtime GenerationEngine differs from pinned checkout")

    client = GenerationClient.from_env()
    outputs: list[dict[str, Any]] = []
    with SQLiteExperimentLedger(args.database, private_root=args.private_root) as ledger:
        ledger.create_run(run_id=args.run_id, suite="of-conks-cons-v21",
                          source_manifest_sha256=digest(args.source_manifest),
                          frozen_gold_sha256=digest(args.gold), recipe_sha256=recipe_sha,
                          recovery_route="supplied_markdown_stageA_v1",
                          provider_exposure="approved_private_api", provider="openai", model=MODEL,
                          call_cap=CALL_CAP, spend_cap_usd=SPEND_CAP_USD)
        out.mkdir(parents=True)
        (out / "calls").mkdir()
        for page in pages:
            index = page["page_index"]
            prompt = page_prompt(page)
            _write_new(out / "calls" / f"page-{index:02d}-prompt.json",
                       {"system": SYSTEM_PROMPT, "user": prompt, "schema": PAGE_SCHEMA})
            call_index = ledger.reserve_call(run_id=args.run_id, maximum_cost_usd=RESERVATION_USD)
            request = TextRequest(user_prompt=prompt, system_prompt=SYSTEM_PROMPT,
                                  model=MODEL, temperature=None, reasoning_effort="low",
                                  max_transport_retries=0, max_output_tokens=MAX_OUTPUT_TOKENS,
                                  json_schema=PAGE_SCHEMA, schema_name="AdventurePage",
                                  deadline_ms=120000)
            try:
                result = await client.generate_structured(request)
                observation = result.observation
                output = {"page_index": index, "printed_page": page["printed_page"],
                          "state": "completed", "parsed": result.parsed, "text": result.text,
                          "observation": observation.model_dump(mode="json")}
            except GenerationEngineError as exc:
                observation = exc.observation
                output = {"page_index": index, "printed_page": page["printed_page"],
                          "state": observation.state.value, "parsed": None, "text": None,
                          "failure": {"code": exc.failure.code.value, "message": exc.failure.message},
                          "observation": observation.model_dump(mode="json")}
            _write_new(out / "calls" / f"page-{index:02d}-response.json", output)
            ledger.record_observation(run_id=args.run_id, call_index=call_index,
                                      state=observation.state.value, provider="openai",
                                      requested_model=MODEL, resolved_model=observation.resolved_model,
                                      response_model=observation.response_model,
                                      request_id=observation.provider_request_id,
                                      response_id=observation.provider_response_id,
                                      input_tokens=observation.input_tokens,
                                      cached_input_tokens=observation.cached_input_tokens,
                                      output_tokens=observation.output_tokens,
                                      cost_usd=None, pricing_source=PRICE_SOURCE,
                                      failure_code=(observation.failure_code.value
                                                    if observation.failure_code else None))
            outputs.append(output)
            print(f"page {page['printed_page']}: {output['state']}; "
                  f"input={observation.input_tokens} output={observation.output_tokens}", flush=True)
        first_path = out / "first-result.json"
        _write_new(first_path, {"format_version": 1, "recipe_sha256": recipe_sha,
                                "substrate_run_id": substrate["run_id"], "pages": outputs})
        ledger.record_artifact(run_id=args.run_id, role="first_result", name="primary", path=first_path)
        call_files = sorted((out / "calls").glob("*.json"))
        if len(call_files) != 2 * len(pages):
            raise ValueError("call prompt/response file count changed")
        call_manifest_path = out / "call-manifest.json"
        _write_new(call_manifest_path, {"files": {path.name: digest(path) for path in call_files},
                                        "expected_file_count": 2 * len(pages)})
        ledger.record_artifact(run_id=args.run_id, role="call_manifest", name="primary",
                               path=call_manifest_path)
        package, counts = assemble_first_result(pages=pages, outputs=outputs,
                                                 source_id="of-conks-cons-v21-supplied-markdown",
                                                 store=JsonPackageStore(out / "packages"),
                                                 package_id=f"conks-semantic-{args.run_id}",
                                                 inherited_diagnostics=diagnostics)
        package_path = JsonPackageStore(out / "packages").path_for(package["package_id"],
                                                                    package["revision"])
        ledger.record_artifact(run_id=args.run_id, role="assembled_package", name="primary",
                               path=package_path)
        observed_input = sum((o["observation"].get("input_tokens") or 0) for o in outputs)
        observed_cached = sum((o["observation"].get("cached_input_tokens") or 0) for o in outputs)
        observed_output = sum((o["observation"].get("output_tokens") or 0) for o in outputs)
        observed_attempts = sum((o["observation"].get("provider_attempt_count") or 0)
                                for o in outputs)
        observed_repairs = sum((o["observation"].get("conformance_retry_count") or 0)
                               for o in outputs)
        estimate = ((observed_input - observed_cached) * 0.20 + observed_cached * 0.02
                    + observed_output * 1.20) / 1_000_000
        report = {"run_id": args.run_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                  "source_manifest_sha256": digest(args.source_manifest),
                  "frozen_gold_sha256": digest(args.gold), "substrate_run_id": substrate["run_id"],
                  "substrate_evidence_manifest_sha256": substrate["evidence_manifest_sha256"],
                  "generation_engine_ref": ge_ref, "recipe_sha256": recipe_sha,
                  "call_manifest_sha256": digest(call_manifest_path),
                  "provider_exposure": "approved_private_api", "provider": "openai", "model": MODEL,
                  "call_cap": CALL_CAP, "spend_cap_usd": SPEND_CAP_USD,
                  "provider_attempt_ceiling": PROVIDER_ATTEMPT_CEILING,
                  "observed_provider_attempts": observed_attempts,
                  "observed_conformance_retries": observed_repairs,
                  "max_output_tokens_per_call": MAX_OUTPUT_TOKENS, "price_source": PRICE_SOURCE,
                  "observed_tokens": {"input": observed_input, "cached_input": observed_cached,
                                      "output": observed_output},
                  "list_price_estimate_usd": round(estimate, 6),
                  "list_price_estimate_is_not_invoice": True,
                  "counts": counts, "package_ref": {"package_id": package["package_id"],
                                                   "revision": package["revision"]},
                  "gold_scoring": "not_scored", "repairs": 0}
        report_path = out / "first-semantic-report.json"
        _write_new(report_path, report)
        ledger.record_artifact(run_id=args.run_id, role="run_report", name="primary", path=report_path)
        ledger.close_run(args.run_id)
        print(json.dumps({"ledger": ledger.summary(args.run_id), "counts": counts,
                          "list_price_estimate_usd": report["list_price_estimate_usd"]},
                         sort_keys=True))
    await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--substrate-dir", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--generation-engine-root", type=Path, required=True)
    parser.add_argument("--expected-ge-ref", required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--preflight", action="store_true")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
