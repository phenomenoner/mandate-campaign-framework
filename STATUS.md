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
- **Phase 4 in progress** — repeatability breadth still not strong enough to call this broadly battle-tested
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

## Public proof entrypoints

- `examples/README.md`
- `examples/proof-bundles/PROOF_INDEX.md`
- `examples/proof-bundles/replay-all.sh`
- `examples/operator-gate-reject-demo.sh`
- `tests/`

## Next 3

1. Broaden repeatability beyond the current seeded Steamer proof spine.
2. Add stronger public-safe second-adapter proof, not just runtime presence.
3. Improve external operator bootstrap/docs without inflating maturity language.

## Design caution

- Do not mistake explicit operator mechanics for finished product maturity.
- Do not collapse domain nouns back into the kernel.
- Do not present seeded proof bundles as broad production evidence.
