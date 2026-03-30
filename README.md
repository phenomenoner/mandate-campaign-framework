# Mandate Campaign Framework (Experimental / Advanced Operator)

A mandate-driven, file-backed, phase-gated campaign runtime for operators who want explicit state,
explicit receipts, and bounded advancement instead of hidden workflow magic.

## What is actually shipped here

- frozen-enough kernel contracts in `kernel/v0.1-freeze.md`
- runnable thin CLIs in `tools/`:
  - `validate-mandate.py`
  - `init-campaign.py`
  - `advance-campaign.py`
  - `inspect-campaign.py`
- adapter-aware runtime dispatch with explicit adapter identity
- executable reference adapter surfaces:
  - `adapters/steamer/`
  - `adapters/openclaw-mem/`
- one additional sketch adapter for genericity pressure-testing:
  - `adapters/content-production/`
- six seeded proof bundles with replay scripts under `examples/proof-bundles/`
- test coverage for runtime schema, adapter dispatch, recovery/gate semantics, and proof-bundle integrity

## Honest roadmap snapshot

- **Phase 0 done** — kernel/runtime proof exists
- **Phase 1 done** — executable adapter dispatch is real
- **Phase 2 done** — seeded Steamer shadow proof is real
- **Phase 3 done** — bounded operator-loop hardening slices are real
- **Phase 4 in progress** — repeatability breadth is still the main gate
- **Phase 5 minimally done** — a second executable adapter path exists without collapsing the kernel into Steamer nouns
- **Phase 6+ still open** — external usability, semantics freeze, RC discipline, and stable-release posture remain ahead

That is **not** the same thing as a stable general orchestration product.

## What Phase 3 means in practice

This repo now includes public-safe proof for narrow but real operator-loop slices:
- operator-gate escalation + replay (`approve_shadow_review`, `reject_shadow_review`)
- blocked queue-empty recovery via `--resume`
- cycle-budget exhaustion visibility
- stalled operator-gate timeout visibility in inspect output
- durable gate-replay and blocked-visibility close-out receipts

The scope is still intentionally tight. These are bounded operator mechanics, not a claim that every failure class is already productized.

## Current closure track

The next real push is now **repo-local and product-native**:
1. `RELEASES/phase-closure-proof-matrix.md` — one compare surface for Phases 4/5/6/7/8
2. `examples/operator-drills.md` — public-safe drills an advanced operator can actually run
3. `protocol/external-operator-usability-pack.md` — the minimum pack an outside operator should be able to follow
4. `protocol/semantics-freeze-checklist.md` — explicit freeze-now vs still-moving semantics

This is how the remaining phases move **without waiting on active Steamer, openclaw-mem, or other product-line work**.

## What is still not done

- broad repeatability across many domains and campaign shapes
- beginner-first onboarding
- stable compatibility promises
- broad adapter ecosystem claims
- autopilot / fully autonomous positioning

## Start here

1. `STATUS.md` — current posture and limits
2. `RELEASES/phase-closure-proof-matrix.md` — remaining-phase compare surface
3. `examples/operator-drills.md` — public-safe drills
4. `protocol/external-operator-usability-pack.md` — minimum operator pack
5. `protocol/semantics-freeze-checklist.md` — freeze checklist
6. `examples/proof-bundles/PROOF_INDEX.md` — canonical replay index
7. `tools/README.md` — CLI/runtime surface
8. `tests/` — current verifier surface

## Repository map

- `kernel/` — shared contracts and phase model
- `adapters/` — domain bindings
- `tools/` — bounded runtime CLIs
- `campaigns/` — seeded file-backed campaign example
- `examples/` — mandate examples, proof bundles, replay helpers, operator drills
- `protocol/` — thin operator packaging, usability, and semantics docs
- `RELEASES/` — release-facing proof and calibration surfaces
- `tests/` — runtime and proof verification

## Operator honesty

Use this repo if you want explicit state, durable receipts, and inspectable operator-gated progression.
Do not use this repo if you want a polished no-code builder or magic automation claims.
