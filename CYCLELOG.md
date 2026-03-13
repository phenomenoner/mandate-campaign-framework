# mandate-campaign-framework — CYCLELOG

## 2026-03-13 14:33 Asia/Taipei
- seeded the framework productization track
- created kernel / adapters / protocol / examples / tools docs
- re-positioned Steamer as the first reference adapter / proving ground
- receipt: commit `bba2db2`

## 2026-03-13 14:46 Asia/Taipei
- froze kernel contracts at `0.1.0` in docs
- added `content-production` as the second adapter sketch
- documented the future thin OpenClaw operator skill blueprint
- receipt: commit `0acb12e`

## 2026-03-13 15:03 Asia/Taipei
- documented the Copilot runtime review back into kernel/docs
- added `WorkerStatePatch`, `ReceiptRecord`, and `InitPolicy`
- implemented and manually verified `tools/validate-mandate.py` and `tools/init-campaign.py`
- created one file-backed example campaign under `campaigns/2026-03-tw-vcp-shadow-candidate/`
- receipt: pending commit

## 2026-03-13 16:10 Asia/Taipei
- replaced `_runtime_lib.py` homegrown YAML parser with PyYAML-based loading (`yaml.safe_load`)
- added kernel runtime validators for `CampaignState`, `WorkerStatePatch`, and `ReceiptRecord`
- implemented `tools/advance-campaign.py` with one-step file-backed dispatcher + deterministic stub worker
- implemented `tools/inspect-campaign.py` for operator-friendly state/receipt inspection (`--json` supported)
- updated framework docs (`README.md`, `STATUS.md`, `TOPOLOGY.md`, `tools/README.md`) for runtime surface + dependency posture
- receipt: pending commit

## 2026-03-13 17:00 Asia/Taipei
- documented Copilot CLI hardening advisory under `TECH_NOTES/2026-03-13_copilot-hardening-priority.md`
- added runtime schema fixture tests for `CampaignState`, `WorkerStatePatch`, and `ReceiptRecord` (`tests/test_runtime_schema_fixtures.py`)
- made dispatcher phase transition semantics explicit in runtime validation (allowed transition table + retry/fail/back-transition checks)
- added focused phase transition semantics tests (`tests/test_phase_transition_semantics.py`)
- updated framework posture docs (`README.md`, `STATUS.md`, `tools/README.md`) to reflect revised hardening order
- receipt: commit `f7bc8b9`

## 2026-03-13 17:17 Asia/Taipei
- documented public launch positioning and release-scope judgment under `TECH_NOTES/2026-03-13_public-launch-positioning.md`
- fixed framework posture as **experimental / advanced-operator public beta**, not beginner-facing generic orchestration
- prepared a clean public-packaging direction: curated repo, no handoff dump
- receipt: pending commit

## 2026-03-13 17:20 Asia/Taipei
- spun out the framework into a dedicated public repo package
- rewrote the root README around experimental advanced-operator positioning
- published the curated public surface without handoffs/internal working artifacts
- receipt: initial public repo commit pending
