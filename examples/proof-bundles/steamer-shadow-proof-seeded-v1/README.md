# Steamer seeded shadow-proof bundle (v1)

Canonical bounded proof pack for the current Steamer shadow-proof path.

## What this bundle proves

This pack captures one full low-risk seeded flow:

1. seeded campaign init from `examples/steamer-vcp-mandate.yaml`
2. bounded `advance-campaign.py` steps through INTAKE/EXPLORE/EVALUATE/SYNTHESIZE/GATE
3. explicit operator-gate escalation
4. explicit operator replay (`approve_shadow_review`)
5. final inspect snapshot at `phase=DELIVER`

The run is deterministic in flow shape and candidate ordering (timestamps are naturally runtime-generated).

## Bundle layout

- `MANIFEST.json` — canonical pointers + expected invariants
- `outputs/000_init.txt` — init command output
- `outputs/advance/*.json` — 8 bounded advance step outputs (including gate replay)
- `outputs/inspect.txt` / `outputs/inspect.json` — final operator inspect outputs
- `run/2026-03-tw-vcp-shadow-candidate/` — captured campaign directory:
  - `MANDATE.yaml`
  - `CAMPAIGN_STATE.json`
  - `receipts/*.json`
  - `artifacts/steamer/idea-scout/*.md`
  - `artifacts/steamer/gate-replay/*.json`
  - `artifacts/steamer/shadow-proof/*.json`

## Quick replay (safe)

```bash
cd .
bash examples/proof-bundles/steamer-shadow-proof-seeded-v1/replay.sh
```

Optional output root:

```bash
bash examples/proof-bundles/steamer-shadow-proof-seeded-v1/replay.sh /tmp/mcf-proof-replay
```

## Expected end-state checks

- final state: `phase=DELIVER`, `status=ACTIVE`
- gate replay receipt/event: `008_steamer_operator_gate_decision_replayed`
- replay decision: `approve_shadow_review`
- inspect drift status: `clean`

See `MANIFEST.json` for exact file pointers.
