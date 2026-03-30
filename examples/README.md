# examples

This directory is the public-safe example surface for `mandate-campaign-framework`.

## Included here

### Example mandates / packets
- `steamer-vcp-mandate.yaml` — seeded Steamer example mandate
- `content-launch-mandate.yaml` — content-production example mandate sketch
- `example-gate-packet.md` — example operator-gate packet shape
- `example-delivery-packet.md` — example delivery packet shape
- `shadow-proof-demo.md` — walk-through of the seeded shadow proof line

### Replay helpers
- `operator-gate-reject-demo.sh` — one-shot seeded reject-replay demo

### Canonical proof bundles
- `proof-bundles/PROOF_INDEX.md` — human-readable bundle index
- `proof-bundles/INDEX.json` — machine-readable bundle manifest
- `proof-bundles/replay-all.sh` — replay all six canonical bundles into a temp/output directory

## Suggested order

1. Read `proof-bundles/PROOF_INDEX.md`
2. Replay one bundle that matches the operator mechanic you care about
3. Use `operator-gate-reject-demo.sh` if you want the shortest negative decision-path demo
4. Inspect `tools/README.md` if you want the CLI contract surface behind the examples

## Calibration

These examples are seeded and bounded on purpose.
They prove that the runtime surfaces are real; they do not prove broad product maturity.
