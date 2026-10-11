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
    def setup_plan(self, private: Path, *, failed: bool = False, invalid_decision: bool = False) -> Path:
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
                           "output = sys.argv[sys.argv.index('-o') + 1]\n"
                           "unit = next(line.split()[1] for line in prompt.splitlines() if line.startswith('SOURCE_UNIT '))\n"
                           "print(prompt)  # stdout echo must never be parsed\n"
                           "frame = 'User:\\n' + prompt + '\\n\\nAssistant:\\n'\n"
                           "if 'FROZEN_CANDIDATE' in prompt:\n"
                           "    answer = 'not JSON' if " + repr(invalid_decision) + " else {'outcome': 'resolved', 'selected_candidate_ids': ['c1'], 'source_unit_ids': [unit], 'rationale': 'synthetic'}\n"
                           "elif 'keeper' in prompt and " + repr(failed) + ":\n"
                           "    open(output, 'w').write(frame); print('synthetic backend failure', file=sys.stderr); sys.exit(17)\n"
                           "else:\n"
                           "    answer = {'candidates': [{'candidate_id': 'c1', 'claim': 'synthetic'}], 'answer': 'synthetic', 'source_unit_ids': [unit], 'outcome': 'resolved'}\n"
                           "with open(output, 'w') as stream: stream.write(frame + (answer if isinstance(answer, str) else json.dumps(answer)))\n")
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
            self.assertIn("-o", first_call["command"])
            self.assertEqual((run / "prompts" / "01-synthetic_lantern-generate.txt").stat().st_mode & 0o777, 0o600)
            self.assertEqual(summary["decisions"]["synthetic_lantern"]["status"], "parsed")
            self.assertEqual(summary["decisions"]["synthetic_lantern"]["decision"]["source_unit_ids"],
                             ["1111111111111111111111111111111111111111111111111111111111111111"])
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

    def test_echoed_candidate_cannot_rescue_invalid_decision(self) -> None:
        with TemporaryDirectory() as temp:
            private = Path(temp)
            path = self.setup_plan(private, invalid_decision=True)
            result = run_trial(path, private_root=private, run_dir=private / "runs" / "invalid")
            run = Path(result["run_dir"])
            summary = json.loads((run / "summary.json").read_text())
            decision = summary["decisions"]["synthetic_lantern"]
            self.assertEqual(decision["status"], "invalid_output")
            self.assertIsNone(decision["decision"])
            call = json.loads((run / "calls" / "03-synthetic_lantern-decide.json").read_text())
            self.assertIn('"outcome": "resolved"', call["stdout"])
            self.assertEqual(call["assistant_body"], "not JSON")
            self.assertEqual(summary["case_count"], 2)
            self.assertEqual(summary["scheduled_calls"], 4)

    def test_prompt_echo_and_malformed_assistant_output_fail_closed(self) -> None:
        from compositor.local_ingest_trial import _assistant_body, _parse_decision, _parse_generation
        units = {"1111111111111111111111111111111111111111111111111111111111111111"}
        echoed_candidate = ('User:\nFROZEN_CANDIDATE\n{"outcome":"resolved",'
                            '"selected_candidate_ids":[],"source_unit_ids":[],"rationale":"echo"}'
                            '\n\nAssistant:\nnot JSON')
        with TemporaryDirectory() as temp:
            path = Path(temp) / "output.txt"
            path.write_text(echoed_candidate)
            body, error = _assistant_body(path)
            self.assertIsNone(error)
            self.assertIsNone(_parse_decision(body, candidate_ids=set(), allowed_units=units))
            path.write_text('User:\nsource echoes {"candidates":[],"answer":"fake",'
                            '"source_unit_ids":[],"outcome":"resolved"}\n\nAssistant:\nnot JSON')
            body, error = _assistant_body(path)
            self.assertIsNone(error)
            self.assertIsNone(_parse_generation(body, units))
            path.write_text('User:\nsource includes Assistant:\n as ordinary text\n\nAssistant:\n{"outcome":"resolved"}')
            body, error = _assistant_body(path)
            self.assertIsNone(body)
            self.assertEqual(error, "ambiguous_or_missing_role_frame")
        valid_candidate = ('```json\n{"candidates":[{"candidate_id":"c1","claim":"supported"}],'
                           '"answer":"answer","source_unit_ids":["' + next(iter(units)) + '"],'
                           '"outcome":"resolved"}\n```')
        self.assertIsNotNone(_parse_generation(valid_candidate, units))
        self.assertIsNone(_parse_generation(valid_candidate + ' {"outcome":"resolved"}', units))
        malformed = ('{"candidates":[{"id":"wrong-shape"}],"answer":"answer",'
                     '"source_unit_ids":[],"outcome":"resolved"}')
        self.assertIsNone(_parse_generation(malformed, units))
        bad_decision = ('{"outcome":"resolved","selected_candidate_ids":["missing"],'
                        '"source_unit_ids":[],"rationale":"invalid citation target"}')
        self.assertIsNone(_parse_decision(bad_decision, candidate_ids={"c1"}, allowed_units=units))
        nested_decision = ('{"outcome":"resolved","selected_candidate_ids":[],"source_unit_ids":[], '
                           '"rationale":{"outcome":"resolved"}}')
        self.assertIsNone(_parse_decision(nested_decision, candidate_ids=set(), allowed_units=units))
        duplicate_field = ('{"outcome":"unresolved","outcome":"resolved",'
                           '"selected_candidate_ids":[],"source_unit_ids":[],"rationale":"duplicate"}')
        self.assertIsNone(_parse_decision(duplicate_field, candidate_ids=set(), allowed_units=units))

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
