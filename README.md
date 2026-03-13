# Mandate Campaign Framework v0.1 (Experimental)

A **schema-strict, phase-gated runtime** for advanced OpenClaw campaigns.

This project helps operators run long-lived workflows with durable file-backed state, explicit contracts, bounded worker progression, and inspectable campaign flow.

## Who this is for

This is for:
- advanced OpenClaw operators
- workflow designers
- ops-heavy builders
- people who value predictability, state, governance, and inspectability

This is **not** for:
- beginners looking for a no-code builder
- users expecting a polished end-user app
- anyone assuming generic orchestration maturity has already been fully proven

## What ships

- core campaign kernel
- runtime CLI:
  - `validate-mandate.py`
  - `init-campaign.py`
  - `advance-campaign.py`
  - `inspect-campaign.py`
- strict schema enforcement for:
  - `CampaignState`
  - `WorkerStatePatch`
  - `ReceiptRecord`
- explicit phase transition semantics:
  - forward
  - retry
  - failure
  - back-transition
- one reference adapter (`steamer`)
- one second adapter sketch (`content-production`) for genericity pressure-testing
- one seeded example campaign
- tests for schema contracts and phase transition semantics

## What this is not

- not a no-code automation builder
- not a polished install-and-forget product
- not yet a production-proven domain-agnostic orchestration platform
- not a mature adapter/plugin ecosystem

## Why it matters

Most agent workflows are still fragile: state is implicit, retries are vague, and failures are hard to inspect. This framework takes the opposite posture:
- explicit state
- explicit contracts
- explicit transitions
- bounded progression
- durable artifacts
- operator visibility

## Operator reality

Right now, operators still own real responsibility:
- campaigns advance step-by-step via CLI
- worker dispatch is still intentionally thin
- adapter genericity is still being proved
- operator UX is still being hardened

## Honest beta posture

The runtime is real. The contracts are real. The phase semantics are real.

What is still being proven is the broader product surface:
- adapter-boundary maturity
- public ergonomics
- packaging polish

If you want magic, zero setup, or instant generic automation, this is the wrong repo.
If you want an inspectable runtime you can reason about, this is the right direction.

## Start here

- `TOPOLOGY.md`
- `STATUS.md`
- `kernel/`
- `tools/README.md`
- `TECH_NOTES/2026-03-13_public-launch-positioning.md`
- `RELEASES/v0.1.0.md`
- `ANNOUNCEMENTS/github-launch.md`
- `ANNOUNCEMENTS/openclaw-community.md`
