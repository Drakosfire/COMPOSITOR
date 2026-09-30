# Private experiment ledger — implementation record

Status: **PR candidate for PRIME review**. This is a bounded preparation slice for [adventure competence](../Handoffs/HANDOFF-03-adventure-competence.md), anchored on PRIME's COMPOSITOR PR #3 merge `5da0c99751cb65a98af87fb66be4060755c0604c`. It supplies persistent experimental records without claiming an adventure benchmark run.

## Scope

- Write paths: COMPOSITOR `src/compositor/`, `tests/`, `README.md`, and this record. No other repository or shared database is changed.
- Backend: Python standard-library SQLite in an operator-selected path beneath ignored `.local/private/`. The path is explicit; the library does not read credentials or `.env` and tests use temporary directories. No real source, gold, prompt, response, or run data is committed.
- Runtime/provider: tests only; zero provider calls and zero paid spend. A live run record must pin exact source manifest, frozen gold, and recipe SHA-256; recovery route; provider exposure decision; model; finite call and dollar caps. Reserving a call is atomic and refuses the next call once either cap is reached. An unknown observed cost conservatively retains the full reservation. GenerationEngine remains the owner of actual provider execution and observation truth; this ledger records its receipt fields without prompt or response bodies.

## Witness

`SQLiteExperimentLedger` creates an isolated schema with runs, artifact references, calls, and judgments. A first result occupies one immutable `first_result/primary` slot per run; later repairs use separate artifact roles. File bytes remain in the private root, with SHA-256 checked when reopened. A database outside the private root or an artifact outside it is rejected. The ledger persists across reopen, rejects duplicate first results, rejects a receipt with a provider/model different from its run pin, and will not close a run with an outstanding reservation.

Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`: 16 tests pass, including three focused ledger witnesses. Run `python3 -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/compositor-build .` to check package assembly. No actual Conks/Sheep score or provider receipt has been written yet.

## Next dependency

The first real run needs the operator's selected database backend/path, the exact two source manifests, both frozen gold suites, a pinned interpretation recipe, handling decisions, and finite provider limits. *Of Conks & Cons* gold is frozen privately; *A Wild Sheep Chase* selected local PDF and processed Markdown paths remain missing. This ledger makes the recorded run reproducible and budgeted but does not itself interpret evidence or prove a useful Composition. PRIME owns review and merge.
