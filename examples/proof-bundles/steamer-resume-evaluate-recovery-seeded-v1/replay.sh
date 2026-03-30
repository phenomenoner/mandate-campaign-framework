#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_ROOT="${1:-$(mktemp -d)}"
RUN_ROOT="$OUT_ROOT/run"
OUT_DIR="$OUT_ROOT/outputs"
CAMPAIGN_ID="2026-03-tw-vcp-shadow-candidate"
CAMPAIGN_DIR="$RUN_ROOT/$CAMPAIGN_ID"
PYTHON_RUN=(uv run --with pyyaml -- python3)

mkdir -p "$OUT_DIR/advance"

cd "$PROJECT_ROOT"
"${PYTHON_RUN[@]}" tools/init-campaign.py examples/steamer-vcp-mandate.yaml --campaigns-dir "$RUN_ROOT" > "$OUT_DIR/000_init.txt"

"${PYTHON_RUN[@]}" - "$CAMPAIGN_DIR" > "$OUT_DIR/001_force_evaluate_queue_empty.txt" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

campaign_dir = Path(sys.argv[1])
mandate_path = campaign_dir / "MANDATE.yaml"
mandate = yaml.safe_load(mandate_path.read_text(encoding="utf-8"))
constraints = mandate.setdefault("constraints", {})
constraints["control_lane_only"] = True
mandate["control_scenario"] = "resume-evaluate-recovery-seeded"
mandate_path.write_text(yaml.safe_dump(mandate, allow_unicode=True, sort_keys=False), encoding="utf-8")

state_path = campaign_dir / "CAMPAIGN_STATE.json"
state = json.loads(state_path.read_text(encoding="utf-8"))
state["phase"] = "EVALUATE"
state["status"] = "ACTIVE"
state["active_item_id"] = None
state["item_queue"] = []
state["wakeup"] = {"needed": False, "reason": None}
state["back_transitions_remaining"] = 1
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("fixture_mutation=applied")
print("mandate.constraints.control_lane_only=true")
print("mandate.control_scenario=resume-evaluate-recovery-seeded")
print("phase=EVALUATE")
print("status=ACTIVE")
print("active_item_id=null")
print("item_queue=[]")
print("wakeup.reason=null")
print("back_transitions_remaining=1")
PY

"${PYTHON_RUN[@]}" tools/advance-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/advance/001_evaluate_to_blocked_no_candidate.json"
"${PYTHON_RUN[@]}" tools/inspect-campaign.py "$CAMPAIGN_DIR" > "$OUT_DIR/inspect_blocked.txt"
"${PYTHON_RUN[@]}" tools/inspect-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/inspect_blocked.json"
"${PYTHON_RUN[@]}" tools/advance-campaign.py "$CAMPAIGN_DIR" --json --resume > "$OUT_DIR/advance/002_blocked_resume_to_explore.json"
"${PYTHON_RUN[@]}" tools/inspect-campaign.py "$CAMPAIGN_DIR" > "$OUT_DIR/inspect_post_resume.txt"
"${PYTHON_RUN[@]}" tools/inspect-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/inspect_post_resume.json"

printf 'replay_complete\nout_root=%s\ncampaign_dir=%s\n' "$OUT_ROOT" "$CAMPAIGN_DIR"
