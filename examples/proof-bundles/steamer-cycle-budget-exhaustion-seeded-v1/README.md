# Steamer cycle-budget exhaustion proof bundle (v1)

Canonical bounded proof pack for the cycle-budget stop behavior under adapter-aware runtime dispatch.

## What this bundle proves

This pack captures one deterministic public-safe budget-stop slice:

1. seeded campaign init from `examples/steamer-vcp-mandate.yaml`
2. forced `EXPLORE` fixture with candidate context intact and `cycle_budget=0`
3. one `advance-campaign.py` step that blocks with event `cycle_budget_exhausted`
4. wake reason `cycle_budget_exhausted` and `status=BLOCKED` in state/output
5. blocked-state inspect snapshots (`txt` + `json`) showing the same stop reason

The behavior is runtime-real (adapter dispatch path), not a doc-only claim.

## Bundle layout

- `MANIFEST.json` — canonical pointers + expected invariants
- `outputs/000_init.txt` — init command output
- `outputs/001_force_explore_cycle_budget_zero.txt` — deterministic fixture mutation receipt
- `outputs/advance/001_explore_to_blocked_cycle_budget.json` — blocked budget-stop step output
- `outputs/inspect_blocked.txt` / `outputs/inspect_blocked.json` — blocked-state inspect output
- `run/2026-03-tw-vcp-shadow-candidate/` — captured campaign directory:
  - `MANDATE.yaml`
  - `CAMPAIGN_STATE.json`
  - `receipts/000..001_*.json`

## Quick replay (safe)

```bash
cd .
bash examples/proof-bundles/steamer-cycle-budget-exhaustion-seeded-v1/replay.sh
```

Optional output root:

```bash
bash examples/proof-bundles/steamer-cycle-budget-exhaustion-seeded-v1/replay.sh /tmp/mcf-cycle-budget-proof-replay
```

## Expected end-state checks

- blocked step emits `receipt_id=001_cycle_budget_exhausted`
- blocked step `result_type=BLOCK`
- blocked wake reason is `cycle_budget_exhausted`
- blocked state remains `phase=EXPLORE`, `status=BLOCKED`, `cycle_budget=0`
- blocked inspect reports `drift=clean`

See `MANIFEST.json` for exact file pointers.
