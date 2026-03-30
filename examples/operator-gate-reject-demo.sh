#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_ROOT="${1:-$PROJECT_ROOT/examples/demo-outputs/steamer-gate-reject-replay-v1}"
RUN_ROOT="$OUT_ROOT/run"
OUT_DIR="$OUT_ROOT/outputs"
CAMPAIGN_ID="2026-03-tw-vcp-shadow-candidate"
CAMPAIGN_DIR="$RUN_ROOT/$CAMPAIGN_ID"

rm -rf "$OUT_ROOT"
mkdir -p "$RUN_ROOT" "$OUT_DIR/advance"

cd "$PROJECT_ROOT"

python3 tools/init-campaign.py examples/steamer-vcp-mandate.yaml --campaigns-dir "$RUN_ROOT" > "$OUT_DIR/000_init.txt"
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/advance/001_intake_to_explore.json"
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/advance/002_explore_to_evaluate.json"
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/advance/003_evaluate_back_to_explore.json"
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/advance/004_explore_to_evaluate.json"
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/advance/005_evaluate_to_synthesize.json"
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/advance/006_synthesize_to_gate.json"
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/advance/007_gate_to_operator_gate_escalate.json"
python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json \
  --replay-decision reject_shadow_review \
  --replay-note "risk posture not acceptable for this shadow promotion" \
  > "$OUT_DIR/advance/008_operator_gate_replay_reject_to_closed.json"

python3 tools/inspect-campaign.py "$CAMPAIGN_DIR" > "$OUT_DIR/inspect.txt"
python3 tools/inspect-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/inspect.json"

cat <<EOF
operator-gate reject demo: OK
output_root: $OUT_ROOT
campaign_dir: $CAMPAIGN_DIR
reject_replay_output: $OUT_DIR/advance/008_operator_gate_replay_reject_to_closed.json
inspect_json: $OUT_DIR/inspect.json
gate_replay_artifacts:
$(ls -1 "$CAMPAIGN_DIR"/artifacts/steamer/gate-replay/)
EOF
