# Mandate Campaign Framework (Experimental / Advanced-Operator)

A mandate-driven, phase-gated campaign runtime direction for OpenClaw operators who want durable state, explicit contracts, and inspectable progression.

## Current proof posture (2026-03-14)

Internal steering read:
- **Phase 1 done** (executable adapter path proven)
- **Phase 2 minimally proven** (seeded shadow proof is real)
- **Phase 3 in progress** (operator-loop hardening is underway)
- **6 canonical proof bundles now exist** in the active proving line

Hard boundary:
- this remains **experimental**
- this is for **advanced operators**
- this is **not** a stable general orchestration product

## What this public repo is

This repo is the public packaging/convergence surface for the framework direction.

It currently carries the kernel/runtime baseline and public docs needed to track proof posture without hype.

## What ships here today

- kernel contracts and docs (`kernel/`)
- runtime CLI surfaces (`tools/`):
  - `validate-mandate.py`
  - `init-campaign.py`
  - `advance-campaign.py`
  - `inspect-campaign.py`
- adapter docs/surfaces (`adapters/`)
- seeded campaign/examples (`campaigns/`, `examples/`)
- schema/phase semantics tests (`tests/`)
- topology/status/release notes for operator calibration

## What this is not

- not a beginner no-code builder
- not a polished end-user app
- not a claim that broad adapter/generic orchestration maturity is done

## Start here

- `STATUS.md`
- `TOPOLOGY.md`
- `RELEASES/v0.2.0-alpha1.md`
- `RELEASES/v0.1.0.md`
- `tools/README.md`

## Operator honesty

If you want magic autopilot, this is the wrong repo.
If you want explicit state/phase/operator boundaries and proof-driven iteration, this is the right direction.
