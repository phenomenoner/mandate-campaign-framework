# External advanced-operator usability pack

This is the minimum pack an outside advanced operator should be able to follow **without internal governance context**.

## Minimum prerequisites

- Python available
- `PyYAML` available (`uv run --with pyyaml ...` is the easiest path)
- comfort with CLI-driven, file-backed workflows
- expectation set correctly: this repo is **experimental / advanced-operator**, not beginner-first

## First 30 minutes path

1. Read `STATUS.md`
2. Read `examples/operator-drills.md`
3. Run Drill 1 and Drill 2
4. Replay one canonical bundle from `examples/proof-bundles/PROOF_INDEX.md`
5. Read `protocol/semantics-freeze-checklist.md` before promising yourself any compatibility story

## The operator should be able to do all of these

- validate a mandate without guesswork
- initialize a seeded campaign and inspect its state
- understand the difference between:
  - ordinary active progression
  - `BLOCKED`
  - `OPERATOR_GATE`
  - replay decisions
  - blocked-visibility close-out
- run at least one canonical proof bundle without hidden manual patching
- find the known limits quickly

## Public-safe support surfaces

- `tools/README.md`
- `examples/operator-drills.md`
- `examples/proof-bundles/PROOF_INDEX.md`
- `RELEASES/phase-closure-proof-matrix.md`
- `protocol/semantics-freeze-checklist.md`

## What this pack still does not promise

- broad no-code usability
- low-skill onboarding
- stable compatibility guarantees
- wide adapter maturity
- autonomous operation without operator review
