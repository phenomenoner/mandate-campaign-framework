# mandate-campaign-framework — STATUS

## Release posture

- **experimental**
- **advanced-operator**
- **not stable** as a general orchestration product

## What is concretely real in this repo

- kernel `v0.1` contract frame
- file-backed runtime flow (`validate -> init -> advance -> inspect`)
- adapter-aware dispatch with explicit runtime adapter identity
- executable `steamer` adapter surface
- executable `openclaw-mem` adapter surface
- `content-production` sketch adapter for genericity pressure-testing
- six canonical seeded proof bundles with replay helpers
- runtime/proof tests checked into `tests/`

## Honest roadmap snapshot

- **Phase 0 done** — kernel proof
- **Phase 1 done** — executable adapter path
- **Phase 2 done** — Steamer shadow proof
- **Phase 3 done** — narrow operator-loop hardening slices are real
- **Phase 4 in progress** — repeatability breadth still is not strong enough to call this broadly battle-tested
- **Phase 5 minimally done** — second executable adapter path exists and keeps shared contracts generic
- **Phase 6+ not claimed** — public usability, semantics freeze, RC discipline, and stable release posture remain ahead

## Phase 3 closure basis

Public-safe proof now covers:
1. operator-gate escalation and replay approve path
2. blocked `EXPLORE` resume recovery
3. blocked `EVALUATE` resume back-shift recovery
4. cycle-budget exhaustion stop visibility
5. operator-gate timeout visibility in inspect output
6. operator-gate reject replay to `CLOSED`

These are real slices, but still bounded slices.

## Why Phase 4 stays open

What is still missing for an honest repeatability claim:
- broader non-seeded evidence breadth
- lower interpretation load per run
- more public-safe proof outside the Steamer-heavy bundle set
- stronger evidence that failures are turning into known classes instead of fresh one-offs

## Current forcing move for the remaining phases

The next forcing move is **not** “wait for more work in another repo.”
It is the repo-local closure pack now checked in here:
- `RELEASES/phase-closure-proof-matrix.md`
- `examples/operator-drills.md`
- `protocol/external-operator-usability-pack.md`
- `protocol/semantics-freeze-checklist.md`

Those four surfaces are the current bridge from:
- Phase 4 repeatability truth
- to Phase 6 external advanced-operator usability
- to Phase 7 semantics freeze
- to Phase 8 RC assembly

## Public proof / closure entrypoints

- `examples/README.md`
- `examples/operator-drills.md`
- `examples/proof-bundles/PROOF_INDEX.md`
- `examples/proof-bundles/replay-all.sh`
- `RELEASES/phase-closure-proof-matrix.md`
- `protocol/external-operator-usability-pack.md`
- `protocol/semantics-freeze-checklist.md`
- `tests/`

## Next 3

1. Re-run the operator drills from a fresh checkout or clean temp output root and keep the resulting receipts easy to compare.
2. Add at least one stronger public-safe second-adapter drill so Phase 4/5 evidence is less Steamer-concentrated.
3. Keep the semantics-freeze delta list explicit until compatibility promises become honest.

## Design caution

- Do not mistake explicit operator mechanics for finished product maturity.
- Do not collapse domain nouns back into the kernel.
- Do not present seeded proof bundles as broad production evidence.
- Do not pretend a thin skill or docs pack means the framework is already stable.
