"""Synthetic-only checks of LOCAL-INGEST-001 pins and failure accounting."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compositor.local_ingest_trial import load_plan, run_trial
from compositor.package import CompositionError

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "fixtures/public/local_ingest_001.json").read_text())


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class LocalIngestTrialTest(unittest.TestCase):
    def setup_plan(self, private: Path, *, failed: bool = False) -> Path:
        source = private / "source.txt"
        source.write_text(FIXTURE["source_text"])
        evidence = private / "stageB.evidence_units.json"
        evidence.write_text(json.dumps({"units": FIXTURE["units"]}, sort_keys=True) + "\n")
        model = private / "invented-model.gguf"
        model.write_bytes(b"synthetic model pin only")
        backend = private / "fake-cli"
        backend.write_text("#!/usr/bin/python3\n"
                           "import json, sys\n"
                           "prompt = open(sys.argv[sys.argv.index('-f') + 1]).read()\n"
                           "print(prompt)  # llama-cli may echo private prompt before completion\n"
                           "if 'FROZEN_CANDIDATE' in prompt:\n"
                           "    print(json.dumps({'outcome': 'resolved', 'source_unit_ids': []}))\n"
                           "elif 'keeper' in prompt and " + repr(failed) + ":\n"
                           "    print('synthetic backend failure', file=sys.stderr); sys.exit(17)\n"
                           "else:\n"
                           "    print(json.dumps({'candidates': [{'id': 'one'}], 'answer': 'synthetic', 'outcome': 'resolved'}))\n")
        backend.chmod(0o700)
        cases = []
        for item in FIXTURE["questions"]:
            cases.append({"id": item["id"], "track": "adventure", "question": item["question"],
                          "source": {"path": str(source), "sha256": digest(source),
                                     "document_id": "invented-mill", "audience": "GM", "edition": "synthetic"},
                          "evidence": [{"path": str(evidence), "sha256": digest(evidence),
                                        "unit_id": item["unit_id"]}]})
        manifest = {"format_version": 1, "experiment_id": "LOCAL-INGEST-001",
                    "backend": {"path": str(backend), "sha256": digest(backend)},
                    "model": {"path": str(model), "sha256": digest(model)},
                    "settings": {"context_tokens": 2048, "output_tokens": 32,
                                 "deadline_seconds": 5, "gpu_layers": 0, "seed": 42,
                                 "temperature": 0, "offline": True, "concurrency": 1, "retries": 0},
                    "reference_sha256": "a" * 64, "cases": cases}
        path = private / "manifest.json"
        path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
        return path

    def test_pins_gold_separation_and_candidate_freeze(self) -> None:
        with TemporaryDirectory() as temp:
            private = Path(temp)
            path = self.setup_plan(private)
            plan = load_plan(path, private_root=private)
            self.assertEqual(len(plan["cases"]), 2)
            self.assertNotIn("gold", json.dumps(plan))
            output = run_trial(path, private_root=private, run_dir=private / "runs" / "one")
            self.assertEqual(output["actual_calls"], 4)
            run = Path(output["run_dir"])
            freeze = json.loads((run / "candidate-freeze.json").read_text())
            self.assertEqual(set(freeze["cases"]), {"synthetic_lantern", "synthetic_keeper"})
            summary = json.loads((run / "summary.json").read_text())
            self.assertEqual(summary["case_count"], 2)
            self.assertEqual(summary["scheduled_calls"], 4)
            self.assertEqual(summary["provider_calls"], 0)
            first_call = json.loads(sorted((run / "calls").glob("*.json"))[0].read_text())
            self.assertIn("--offline", first_call["command"])
            self.assertIn("-f", first_call["command"])
            self.assertEqual((run / "prompts" / "01-synthetic_lantern-generate.txt").stat().st_mode & 0o777, 0o600)
            self.assertEqual(summary["decisions"]["synthetic_lantern"]["status"], "parsed")
            self.assertEqual(summary["decisions"]["synthetic_lantern"]["decision"]["source_unit_ids"], [])
            with self.assertRaises(FileExistsError):
                run_trial(path, private_root=private, run_dir=run)
            manifest = json.loads(path.read_text())
            manifest["cases"][0]["evidence"][0]["sha256"] = "0" * 64
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(CompositionError, "evidence revision mismatch"):
                load_plan(path, private_root=private)

    def test_backend_failure_keeps_denominator_and_raw_output(self) -> None:
        with TemporaryDirectory() as temp:
            private = Path(temp)
            path = self.setup_plan(private, failed=True)
            output = run_trial(path, private_root=private, run_dir=private / "runs" / "failed")
            run = Path(output["run_dir"])
            summary = json.loads((run / "summary.json").read_text())
            self.assertEqual(summary["case_count"], 2)
            self.assertEqual(summary["scheduled_calls"], 4)
            self.assertEqual(summary["actual_calls"], 2)
            self.assertEqual(summary["stop_reason"], "backend_failed")
            self.assertEqual(summary["decisions"]["synthetic_lantern"]["status"],
                             "skipped_after_backend_failure")
            self.assertEqual(summary["decisions"]["synthetic_keeper"]["status"],
                             "skipped_after_backend_failure")
            calls = list((run / "calls").glob("*.json"))
            self.assertEqual(len(calls), 2)
            self.assertTrue(any("synthetic backend failure" in p.read_text() for p in calls))

    def test_caps_and_private_root(self) -> None:
        with TemporaryDirectory() as temp:
            private = Path(temp)
            path = self.setup_plan(private)
            manifest = json.loads(path.read_text())
            manifest["settings"]["output_tokens"] = 1025
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(CompositionError, "output_tokens"):
                load_plan(path, private_root=private)
            manifest["settings"]["output_tokens"] = 32
            manifest.pop("reference_sha256")
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(CompositionError, "frozen reference digest"):
                load_plan(path, private_root=private)
            manifest["reference_sha256"] = "a" * 64
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(CompositionError, "run directory must be inside private root"):
                run_trial(path, private_root=private, run_dir=ROOT / "outside-private")


if __name__ == "__main__":
    unittest.main()
