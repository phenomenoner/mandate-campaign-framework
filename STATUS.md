# mandate-campaign-framework — STATUS

## Steering read (2026-03-14)

Current proof spine:
- **Phase 1 done**
- **Phase 2 minimally proven**
- **Phase 3 in progress**
- **6 canonical proof bundles now exist**

Release posture:
- still **experimental**
- still **advanced-operator**
- still **not stable** as a general orchestration product

## Canonical proof progression snapshot

The active proof line now has six canonical bundles covering:
1. seeded shadow proof + approve replay path
2. blocked `EXPLORE` resume recovery
3. blocked `EVALUATE` resume back-shift recovery
4. cycle-budget exhaustion stop visibility
5. operator-gate timeout visibility
6. operator-gate reject replay (`-> CLOSED`)

These bundles establish a minimal but real proof spine; they do **not** imply broad policy/recovery maturity.

## Public convergence note

This public repo is now doc-synced to the current proof posture.

Interpretation rule:
- treat this as an honest milestone marker, not a maturity claim
- avoid reading current proof slices as full generic orchestration coverage

## Next 3

1. Keep public docs/release notes aligned with proof progression without inflating maturity.
2. Continue Phase 3 operator-loop hardening (broader retry/timeout/recovery policy matrix).
3. Increase repeatability breadth beyond current six canonical bundles before any stable-positioning move.

## Design caution

- Do not mistake the framework direction for a finished autopilot.
- Do not collapse domain semantics into kernel contracts.
- Keep operator-gate and rollbackability first while hardening continues.
