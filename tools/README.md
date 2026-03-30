# tools

Thin kernel-facing CLIs:
- `validate-mandate.py` — validate kernel v0.1 mandate fields
- `init-campaign.py` — create campaign directory + canonical mandate/state/initial receipt
- `advance-campaign.py` — run one bounded dispatcher step against a file-backed campaign (default: adapter dispatch; explicit fallback: `--dispatch-mode stub`; `--resume` enables one adapter-defined recovery/resume attempt for blocked campaigns; `--replay-decision approve_shadow_review|reject_shadow_review` records one operator-gate replay decision when status is `OPERATOR_GATE`; `--close-blocked-visibility` performs operator-authorized close-out only for eligible seeded blocked visibility scenarios). Steamer replay semantics stay narrow and explicit: `approve_shadow_review -> DELIVER`, `reject_shadow_review -> CLOSED`, both with durable gate-replay receipts under `artifacts/steamer/gate-replay/`. Steamer blocked-visibility close-out is also narrow/explicit: only `BLOCKED` campaigns with `constraints.control_lane_only=true`, `control_scenario=budget-exhaustion-seeded`, and `wakeup.reason=cycle_budget_exhausted` are eligible; close-out writes durable receipt + `artifacts/steamer/operator-close/*.json` and transitions to `CLOSED/CLOSED` without pretending delivery. Steamer resume slices include blocked queue-empty `EXPLORE` retry and blocked queue-empty `EVALUATE` back-shift-to-`EXPLORE` recovery. Steamer steps surface `acted_item_*` context and materialize bounded artifacts under `artifacts/` (including tiny idea-scout markdown notes, gate-replay receipts, and blocked-visibility close-out receipts).
- `inspect-campaign.py` — inspect state + receipts in human-readable or JSON form, including adapter identity/runtime registration and adapter drift status (`clean` / `warning` / `critical` when hook is available). Inspect surfaces `last_work_item` context when present, emits `operator_gate_visibility` timing/signal fields when a campaign is stalled at `OPERATOR_GATE`, and now exposes blocked-visibility close-out eligibility + action hints so operators can distinguish `--resume` recovery vs `--close-blocked-visibility` close-out.

Shared helper:
- `_runtime_lib.py`
- `_adapter_runtime.py`

Runtime dependency:
- `PyYAML` (`yaml.safe_load`) is required for mandate/defaults parsing.

Design rule:
- keep these CLIs thin and kernel-facing.
- keep adapter domain nouns inside adapter/runtime adapter modules (for example: Steamer phase behavior in `_adapter_runtime.py`, not kernel validators).
- keep phase transition semantics explicit (forward/retry/back/fail) in dispatcher validation, not implicit worker behavior.

Runtime tests:
- `../tests/test_runtime_schema_fixtures.py`
- `../tests/test_phase_transition_semantics.py`
- `../tests/test_adapter_runtime.py`
- `../tests/test_recovery_and_drift.py`

Repro demo:
- `../examples/shadow-proof-demo.md`
- `../examples/operator-gate-reject-demo.sh`
- `../examples/proof-bundles/PROOF_INDEX.md`
