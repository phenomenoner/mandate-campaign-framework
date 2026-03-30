# Shadow-proof demo (P1.4 slice)

Goal: run one small, honest Steamer shadow path where bounded steps now persist:

Operator compare/replay entrypoint: `examples/proof-bundles/PROOF_INDEX.md`.

- work-item receipt context (`id`, `reason`, `decision`),
- one tiny domain artifact (`artifacts/steamer/idea-scout/<candidate>.md`),
- inspectable operator gate decision replay receipts (`artifacts/steamer/gate-replay/*.json`) for both bounded outcomes (`approve_shadow_review` and `reject_shadow_review`).

Canonical captured bundles (seeded, public-safe):
- shadow-proof + operator-gate replay path:
  - `examples/proof-bundles/steamer-shadow-proof-seeded-v1/`
  - replay script: `examples/proof-bundles/steamer-shadow-proof-seeded-v1/replay.sh`
- blocked `EXPLORE` -> `--resume` recovery path:
  - `examples/proof-bundles/steamer-resume-recovery-seeded-v1/`
  - replay script: `examples/proof-bundles/steamer-resume-recovery-seeded-v1/replay.sh`
- blocked `EVALUATE` -> `--resume` back-shift recovery path:
  - `examples/proof-bundles/steamer-resume-evaluate-recovery-seeded-v1/`
  - replay script: `examples/proof-bundles/steamer-resume-evaluate-recovery-seeded-v1/replay.sh`
- cycle-budget exhaustion stop path:
  - `examples/proof-bundles/steamer-cycle-budget-exhaustion-seeded-v1/`
  - replay script: `examples/proof-bundles/steamer-cycle-budget-exhaustion-seeded-v1/replay.sh`
- operator-gate stalled-timeout visibility path:
  - `examples/proof-bundles/steamer-operator-gate-timeout-visibility-seeded-v1/`
  - replay script: `examples/proof-bundles/steamer-operator-gate-timeout-visibility-seeded-v1/replay.sh`
- operator-gate negative replay path (`reject_shadow_review -> CLOSED`):
  - `examples/proof-bundles/steamer-operator-gate-reject-replay-seeded-v1/`
  - replay script: `examples/proof-bundles/steamer-operator-gate-reject-replay-seeded-v1/replay.sh`

## 1) Create an isolated temp campaign

```bash
cd .
TMP=$(mktemp -d)
python3 tools/init-campaign.py examples/steamer-vcp-mandate.yaml --campaigns-dir "$TMP"
CAMPAIGN_DIR="$TMP/2026-03-tw-vcp-shadow-candidate"
```

## 2) Advance to EXPLORE completion (materialize one domain artifact)

```bash
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json   # INTAKE -> EXPLORE
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json   # EXPLORE -> EVALUATE
```

What to look for in second JSON output:
- `acted_item_id`
- `acted_item_decision=idea_scout_completed`
- `materialized_artifacts` includes `artifacts/steamer/idea-scout/<candidate>.md`

Inspect the tiny domain artifact:

```bash
cat "$CAMPAIGN_DIR"/artifacts/steamer/idea-scout/*.md
```

## 3) Advance until operator gate, then replay one bounded decision

```bash
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json   # EVALUATE -> SYNTHESIZE (or back-transition once)
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json   # SYNTHESIZE -> GATE
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json   # GATE -> OPERATOR_GATE (ESCALATE)
```

### 3a) Positive replay path (`OPERATOR_GATE -> DELIVER`)

```bash
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json \
  --replay-decision approve_shadow_review \
  --replay-note "shadow evidence accepted"
```

What to verify in the replay output:
- `status_before=OPERATOR_GATE`
- `phase_after=DELIVER`
- `replay_decision=approve_shadow_review`
- `replay_applied=true`

### 3b) Negative replay path (`OPERATOR_GATE -> CLOSED`)

For canonical evidence, replay:

```bash
bash examples/proof-bundles/steamer-operator-gate-reject-replay-seeded-v1/replay.sh
# optional output root:
# bash examples/proof-bundles/steamer-operator-gate-reject-replay-seeded-v1/replay.sh /tmp/mcf-gate-reject-proof
```

(Quick standalone shortcut still exists at `examples/operator-gate-reject-demo.sh`.)

What to verify in `outputs/advance/008_operator_gate_replay_reject_to_closed.json`:
- `status_before=OPERATOR_GATE`
- `phase_after=CLOSED`
- `status_after=CLOSED`
- `replay_decision=reject_shadow_review`
- `replay_applied=true`

## 4) Inspect operator view

```bash
python3 tools/inspect-campaign.py "$CAMPAIGN_DIR"
```

What to verify:
- `last_work_item` reflects operator replay decision
- receipts preview includes `steamer_operator_gate_decision_replayed`
- replay receipt references `artifacts/steamer/gate-replay/...`

## 5) Inspect persisted proof artifacts

```bash
ls -1 "$CAMPAIGN_DIR"/artifacts/steamer/idea-scout/
ls -1 "$CAMPAIGN_DIR"/artifacts/steamer/gate-replay/
ls -1 "$CAMPAIGN_DIR"/artifacts/steamer/shadow-proof/
```

## 6) Optional: exercise blocked `EVALUATE` recovery slice manually

Canonical seeded replay now exists (`examples/proof-bundles/steamer-resume-evaluate-recovery-seeded-v1/replay.sh`).
Use this manual fixture path only when you want to observe/setup the mutation yourself:

```bash
CAMPAIGN_DIR="$CAMPAIGN_DIR" python3 - <<'PY'
import json, os, pathlib
state_path = pathlib.Path(os.environ["CAMPAIGN_DIR"]) / "CAMPAIGN_STATE.json"
state = json.loads(state_path.read_text(encoding="utf-8"))
state.update({
  "phase": "EVALUATE",
  "status": "BLOCKED",
  "active_item_id": None,
  "item_queue": [],
  "wakeup": {"needed": True, "reason": "steamer_no_candidate_available"},
  "back_transitions_remaining": 1,
})
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --resume --json
```

What to verify:
- `phase_before=EVALUATE`, `phase_after=EXPLORE`
- `status_after=ACTIVE`
- receipt event `steamer_resume_recover_evaluate_to_explore`

This remains intentionally small: one truthful domain artifact + two bounded gate replay outcomes, not a broad general-orchestration claim. Canonical seeded captures now cover the shadow replay approve slice (`examples/proof-bundles/steamer-shadow-proof-seeded-v1/`), both resume recovery slices (`examples/proof-bundles/steamer-resume-recovery-seeded-v1/` and `examples/proof-bundles/steamer-resume-evaluate-recovery-seeded-v1/`), one explicit cycle-budget stop slice (`examples/proof-bundles/steamer-cycle-budget-exhaustion-seeded-v1/`), one operator-gate stalled-timeout visibility slice (`examples/proof-bundles/steamer-operator-gate-timeout-visibility-seeded-v1/`), and one canonical reject replay slice (`examples/proof-bundles/steamer-operator-gate-reject-replay-seeded-v1/`). `examples/operator-gate-reject-demo.sh` remains a shortcut wrapper only.
