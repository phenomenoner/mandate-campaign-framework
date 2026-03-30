# Steamer resume-recovery proof bundle (v1)

Canonical bounded proof pack for the existing Steamer blocked-`EXPLORE` recovery path (`advance-campaign.py --resume`).

## What this bundle proves

This pack captures one deterministic public-safe recovery slice:

1. seeded campaign init from `examples/steamer-vcp-mandate.yaml`
2. forced queue-empty `EXPLORE` setup (deterministic fixture mutation; no secret/private data)
3. blocked `EXPLORE` step with wake reason `steamer_no_candidate_available`
4. explicit `--resume` invocation
5. recovery receipt `steamer_resume_retry_idea_scout`
6. post-resume inspect snapshot at `phase=EVALUATE`, `status=ACTIVE`

The flow shape, candidate reseeding order, and receipt events are deterministic (timestamps are runtime-generated).

## Bundle layout

- `MANIFEST.json` — canonical pointers + expected invariants
- `outputs/000_init.txt` — init command output
- `outputs/001_force_explore_queue_empty.txt` — deterministic fixture mutation receipt
- `outputs/advance/001_explore_to_blocked_no_candidate.json` — blocked step output
- `outputs/inspect_blocked.txt` / `outputs/inspect_blocked.json` — blocked-state inspect output
- `outputs/advance/002_blocked_resume_to_evaluate.json` — resume invocation + recovery step output
- `outputs/inspect_post_resume.txt` / `outputs/inspect_post_resume.json` — post-resume inspect output
- `run/2026-03-tw-vcp-shadow-candidate/` — captured campaign directory:
  - `MANDATE.yaml`
  - `CAMPAIGN_STATE.json`
  - `receipts/000..002_*.json`
  - `artifacts/steamer/candidate-queue.json`
  - `artifacts/steamer/idea-scout/*.md`
  - `artifacts/steamer/shadow-proof/*.json`

## Quick replay (safe)

```bash
cd .
bash examples/proof-bundles/steamer-resume-recovery-seeded-v1/replay.sh
```

Optional output root:

```bash
bash examples/proof-bundles/steamer-resume-recovery-seeded-v1/replay.sh /tmp/mcf-resume-proof-replay
```

## Expected end-state checks

- blocked step emits `receipt_id=001_steamer_no_candidate_available`
- blocked wake reason is `steamer_no_candidate_available`
- resume step has `resume_requested=true`, `resume_applied=true`
- recovery receipt/event is `002_steamer_resume_retry_idea_scout`
- post-resume state is `phase=EVALUATE`, `status=ACTIVE`
- post-resume inspect drift status is `clean`

See `MANIFEST.json` for exact file pointers.
