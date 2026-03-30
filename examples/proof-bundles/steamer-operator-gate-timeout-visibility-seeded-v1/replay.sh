#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_ROOT="${1:-$(mktemp -d)}"
RUN_ROOT="$OUT_ROOT/run"
OUT_DIR="$OUT_ROOT/outputs"
CAMPAIGN_ID="2026-03-tw-vcp-shadow-candidate"
CAMPAIGN_DIR="$RUN_ROOT/$CAMPAIGN_ID"

mkdir -p "$OUT_DIR/advance"

cd "$PROJECT_ROOT"
python3 tools/init-campaign.py examples/steamer-vcp-mandate.yaml --campaigns-dir "$RUN_ROOT" > "$OUT_DIR/000_init.txt"

python3 - "$CAMPAIGN_DIR" > "$OUT_DIR/001_force_gate_active_fixture.txt" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

campaign_dir = Path(sys.argv[1])
state_path = campaign_dir / "CAMPAIGN_STATE.json"
state = json.loads(state_path.read_text(encoding="utf-8"))
state["phase"] = "GATE"
state["status"] = "ACTIVE"
state["active_item_id"] = "tw-vcp-late-reclaim-pullback"
state["item_queue"] = ["tw-vcp-late-reclaim-pullback"]
state["cycle_budget"] = 6
state["wakeup"] = {"needed": False, "reason": None}
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("fixture_mutation=applied")
print("phase=GATE")
print("status=ACTIVE")
print("active_item_id=tw-vcp-late-reclaim-pullback")
print("item_queue_len=1")
print("cycle_budget=6")
PY

python3 tools/advance-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/advance/001_gate_to_operator_gate_escalate.json"

python3 - "$CAMPAIGN_DIR" > "$OUT_DIR/002_force_operator_gate_stale_fixture.txt" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

campaign_dir = Path(sys.argv[1])
state_path = campaign_dir / "CAMPAIGN_STATE.json"
state = json.loads(state_path.read_text(encoding="utf-8"))

stale_ts = "2000-01-01T00:00:00+00:00"
state["updated_at"] = stale_ts

last_receipt_path = campaign_dir / state["last_receipt"]["path"]
receipt = json.loads(last_receipt_path.read_text(encoding="utf-8"))
receipt["created_at"] = stale_ts

state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
last_receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("fixture_mutation=applied")
print("updated_at=2000-01-01T00:00:00+00:00")
print(f"last_receipt={state['last_receipt']['path']}")
print("receipt.created_at=2000-01-01T00:00:00+00:00")
PY

python3 tools/inspect-campaign.py "$CAMPAIGN_DIR" > "$OUT_DIR/inspect_operator_gate_stale.txt"
python3 tools/inspect-campaign.py "$CAMPAIGN_DIR" --json > "$OUT_DIR/inspect_operator_gate_stale.json"

printf 'replay_complete\nout_root=%s\ncampaign_dir=%s\n' "$OUT_ROOT" "$CAMPAIGN_DIR"
