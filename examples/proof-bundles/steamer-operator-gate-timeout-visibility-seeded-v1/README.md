# Steamer operator-gate timeout visibility proof bundle (v1)

Canonical bounded proof pack for operator-gate stall/timeout visibility in `inspect-campaign.py`.

## What this bundle proves

This pack captures one deterministic public-safe gate-stall slice:

1. seeded campaign init from `examples/steamer-vcp-mandate.yaml`
2. forced `GATE` fixture with candidate context (`status=ACTIVE`)
3. one runtime step to `OPERATOR_GATE` (`ESCALATE` path)
4. deterministic stale-gate fixture (`updated_at` + last receipt `created_at` set to an old timestamp)
5. inspect snapshots (`txt` + `json`) that surface:
   - operator-gate blocked state
   - timeout/staleness signal (`operator_gate_timeout_exceeded`)
   - timeout budget from mandate (`operator_gate_timeout_days`)

## Bundle layout

- `MANIFEST.json` — canonical pointers + expected invariants
- `outputs/000_init.txt` — init command output
- `outputs/001_force_gate_active_fixture.txt` — deterministic gate fixture mutation receipt
- `outputs/advance/001_gate_to_operator_gate_escalate.json` — runtime gate escalation output
- `outputs/002_force_operator_gate_stale_fixture.txt` — deterministic stale timestamp mutation receipt
- `outputs/inspect_operator_gate_stale.txt` / `outputs/inspect_operator_gate_stale.json` — inspect outputs with timeout signal
- `run/2026-03-tw-vcp-shadow-candidate/` — captured campaign directory snapshot

## Quick replay (safe)

```bash
cd .
bash examples/proof-bundles/steamer-operator-gate-timeout-visibility-seeded-v1/replay.sh
```

Optional output root:

```bash
bash examples/proof-bundles/steamer-operator-gate-timeout-visibility-seeded-v1/replay.sh /tmp/mcf-gate-timeout-proof-replay
```

## Expected end-state checks

- advance output has `phase_after=GATE`, `status_after=OPERATOR_GATE`, `result_type=ESCALATE`
- state wake reason is `steamer_shadow_review_gate`
- inspect exposes `operator_gate_visibility.stale=true`
- inspect exposes `operator_gate_visibility.signal=operator_gate_timeout_exceeded`
- inspect exposes `operator_gate_visibility.timeout_days=3`

See `MANIFEST.json` for exact file pointers.
