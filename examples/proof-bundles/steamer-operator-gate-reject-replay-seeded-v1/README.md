# Steamer operator-gate reject replay proof bundle (v1)

Canonical bounded proof pack for the `reject_shadow_review` replay path.

## What this bundle proves

This pack captures one deterministic public-safe negative gate decision flow:

1. seeded campaign init from `examples/steamer-vcp-mandate.yaml`
2. bounded `advance-campaign.py` steps through `INTAKE -> ... -> GATE -> OPERATOR_GATE`
3. explicit pre-replay operator-gate evidence (`inspect` + raw `CAMPAIGN_STATE.json` snapshot)
4. explicit negative operator replay invocation (`--replay-decision reject_shadow_review --replay-note ...`)
5. durable replay receipt + gate replay artifact (`artifacts/steamer/gate-replay/*.json`)
6. post-replay closed-state evidence (`phase=CLOSED`, `status=CLOSED`) via `inspect` + state snapshot

The run is deterministic in flow shape and candidate ordering (timestamps are runtime-generated).

## Bundle layout

- `MANIFEST.json` — canonical pointers + expected invariants
- `outputs/000_init.txt` — init command output
- `outputs/advance/*.json` — bounded advance/replay outputs
- `outputs/inspect_pre_replay.txt` / `outputs/inspect_pre_replay.json` — operator-gate state before replay
- `outputs/state_pre_replay.json` — raw campaign state before replay
- `outputs/state_post_replay.json` — raw campaign state after replay
- `outputs/inspect_post_replay.txt` / `outputs/inspect_post_replay.json` — post-replay closed inspect outputs
- `run/2026-03-tw-vcp-shadow-candidate/` — captured campaign directory snapshot

## Quick replay (safe)

```bash
cd .
bash examples/proof-bundles/steamer-operator-gate-reject-replay-seeded-v1/replay.sh
```

Optional output root:

```bash
bash examples/proof-bundles/steamer-operator-gate-reject-replay-seeded-v1/replay.sh /tmp/mcf-gate-reject-proof-replay
```

## Expected end-state checks

- pre-replay inspect/state: `phase=GATE`, `status=OPERATOR_GATE`
- replay output has `replay_decision=reject_shadow_review`, `replay_applied=true`
- replay receipt event: `008_steamer_operator_gate_decision_replayed`
- replay artifact records `operator_decision=reject_shadow_review`
- post-replay inspect/state: `phase=CLOSED`, `status=CLOSED`, drift `clean`

See `MANIFEST.json` for exact file pointers.
