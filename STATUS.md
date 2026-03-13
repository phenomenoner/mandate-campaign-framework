# mandate-campaign-framework — STATUS

## Current state
- Kernel framing is now explicit: **Mandate -> Campaign -> Delivery Packet**.
- Cycle log now exists at `CYCLELOG.md`.
- Steamer is re-positioned as the first **reference adapter / proving ground**, not the framework itself.
- Kernel v0.1 freeze docs have been seeded.
- A second non-Steamer adapter sketch (`content-production`) now exists to pressure-test the kernel boundary.
- Thin OpenClaw operator skill posture is now documented as a blueprint, not yet a shipped skill.
- Thin runtime tools now exist and have been manually verified:
  - `tools/validate-mandate.py`
  - `tools/init-campaign.py`
  - `tools/advance-campaign.py`
  - `tools/inspect-campaign.py`
- Runtime validation now enforces:
  - `CampaignState` required-shape validation
  - `WorkerStatePatch` allowlist semantics
  - `ReceiptRecord` required-shape validation
- Runtime schema fixture tests now exist under `tests/` for valid + invalid contract cases.
- Runtime phase transition semantics are now explicit in dispatcher validation (allowed transition table + retry/fail/back-transition checks).
- Runtime YAML parsing now uses PyYAML (`yaml.safe_load`) instead of the previous hand-rolled parser path.
- A file-backed example campaign now exists:
  - `campaigns/2026-03-tw-vcp-shadow-candidate/`
- Hardening judgment is now explicit: schema fixture tests first, explicit transition semantics second, adapter stub contract proofs later.
- Public-release judgment is now explicit: release as an experimental advanced-operator framework, not as a beginner/no-code/general-orchestration product.

## Next 3
1. Replace stub worker behavior with adapter-bound worker dispatch while preserving kernel validation boundaries.
2. Add one or two CLI integration fixtures for `advance-campaign.py` (happy path + a rejected illegal transition).
3. Revisit whether a thin OpenClaw operator skill is justified now that start/advance/inspect loop exists.

## Blockers
- None for docs-first work.
- Runtime implementation should wait until the kernel contracts stop moving weekly.

## Current design caution
- Do not mistake the current Steamer slow-cook pipeline for the product itself.
- The framework should be generic enough to host Steamer, coding, ops, or research campaigns without importing their nouns into the kernel.
