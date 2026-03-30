# Public-safe operator drills

These drills are the shortest honest way to touch the current product surface without pretending the repo is already stable.

## Prerequisite

Use a Python environment with `PyYAML` available.
The simplest project-root form is:

```bash
uv run --with pyyaml <command>
```

## Drill 1 — validate the seeded mandate

```bash
uv run --with pyyaml python3 tools/validate-mandate.py examples/steamer-vcp-mandate.yaml
```

Success signal:
- command exits `0`
- output confirms the mandate is valid

## Drill 2 — initialize and inspect a fresh campaign

```bash
OUT_DIR="$(mktemp -d)"
uv run --with pyyaml python3 tools/init-campaign.py examples/steamer-vcp-mandate.yaml "$OUT_DIR"
uv run --with pyyaml python3 tools/inspect-campaign.py "$OUT_DIR/2026-03-tw-vcp-shadow-candidate"
```

Success signal:
- campaign directory exists
- `CAMPAIGN_STATE.json` and `receipts/000_campaign_created.json` exist
- inspect output is readable without raw-log spelunking

## Drill 3 — replay one canonical seeded proof bundle

```bash
uv run --with pyyaml bash examples/proof-bundles/steamer-shadow-proof-seeded-v1/replay.sh
```

Success signal:
- replay completes cleanly
- end state reaches the documented terminal state for the bundle
- inspect output and receipts match `examples/proof-bundles/PROOF_INDEX.md`

## Drill 4 — run the shortest negative decision-path demo

```bash
uv run --with pyyaml bash examples/operator-gate-reject-demo.sh
```

Success signal:
- pre-replay gate evidence is visible
- the replay decision is explicit (`reject_shadow_review`)
- the final state is truthfully `CLOSED/CLOSED`

## Optional full sweep

```bash
uv run --with pyyaml bash examples/proof-bundles/replay-all.sh /tmp/mcf-proof-replays
```

Use this when you want one compare folder for all six current bundles.

## Interpretation rule

Green drills mean:
- the bounded product surface is real
- the docs/runtime/proof surfaces still line up

Green drills do **not** mean:
- Phase 4 repeatability is fully closed
- the product is stable
- every failure class is already productized
