# openclaw-mem Adapter

`openclaw-mem` is a **native-first dev-decision adapter** for the mandate-campaign framework.

## Why this adapter exists
Phase 1 surfaced a real gap: SL-M1 had a mandate template but no executable adapter surface.
This adapter closes that gap with a minimal, truthful runtime path for shadow-lane dry-runs.

## Scope posture
This adapter is intentionally small.
It packages bounded memory-lane engineering decisions; it does **not** take over the native `openclaw-mem` pipeline.

## Domain nouns that stay in the adapter
- harvest / triage
- retrieval miss cluster
- regression cluster
- root-cause candidate
- dev-decision packet
- bench/repro pointer

## Adapter responsibilities
- map mem failure/regression signals into bounded campaign work items
- package one reviewable next-step proposal (do / don't do / need more evidence)
- keep topology/cron/model-routing changes explicitly operator-gated

## Current execution truth
- Runtime path is now **bounded mem-semantic**, not generic linear fallback.
- `INTAKE -> DELIVER` now materializes a real dev-decision packet spine:
  - source-signal intake inventory
  - failure-cluster brief
  - root-cause candidate pack
  - next-experiment proposal
  - operator-gate packet
  - delivered dev-decision packet + packet-quality assessment
- Kernel stays generic; mem nouns remain inside this adapter; no unattended topology/cron/model mutations are introduced.
