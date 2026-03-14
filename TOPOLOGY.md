# mandate-campaign-framework — TOPOLOGY

## TL;DR

Three-layer shape:
- **kernel**: domain-free campaign contracts/state/phase model
- **adapters**: domain mappings (Steamer as reference proving ground)
- **runtime/tools**: bounded advance + inspect surfaces for operators

Current autonomy reality:
- operator-gated runtime direction
- proof-driven and intentionally narrow
- **not** stable general orchestration

## Topology sketch

```text
operator mandate
      |
      v
[MandateSpec] -> [CampaignState + phase machine] -> [dispatcher/runtime] -> [adapter worker path]
      |                                                        |                    |
      |                                                        v                    v
      |                                                 [receipt + artifacts] -> [inspect]
      |                                                                           |
      +-----------------------------> [operator gate / decisions] <---------------+
```

## Current proof topology (2026-03-14)

Steering position:
- Phase 1 done
- Phase 2 minimally proven
- Phase 3 in progress
- six canonical proof bundles exist in the active proving line

What that means:
- end-to-end direction is real enough to test
- operator-loop hardening has real slices
- recovery/policy breadth is still intentionally incomplete

## Public packaging topology

This repository is the public-facing convergence surface.

Use release/status docs as the maturity anchor:
- `RELEASES/v0.2.0-alpha1.md`
- `STATUS.md`

Do not treat this repo as a claim of stable orchestration maturity.
