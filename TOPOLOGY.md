# mandate-campaign-framework — TOPOLOGY

## TL;DR

The framework has three layers:

- **kernel** — domain-free campaign runtime contracts
- **adapters** — domain-specific mappings (Steamer first)
- **workers/tools** — bounded executors that advance campaign state

## Topology graphic

```text
operator mandate
      |
      v
[MandateSpec] -> [CampaignState + phase machine] -> [dispatcher] -> [bounded worker]
      |                                                        |
      |                                                        v
      |                                                [receipt + artifacts]
      |                                                        |
      +------------------------> [operator-gate] <-------------+
                                 |
                                 v
                           [DeliveryPacket]
```

## Layer roles

### 1) `kernel/`
Owns the invariant operating model:
- mandate schema
- campaign state
- phase machine
- worker protocol
- delivery packet
- dispatcher semantics

### 2) `adapters/`
Owns domain semantics:
- candidate shape
- evaluation meaning
- authority classification
- delivery metadata
- domain-specific phase decomposition

Current adapter set:
- `adapters/steamer/` — first reference adapter / proving ground
- `adapters/content-production/` — second adapter sketch used to pressure-test kernel genericity

### 3) `protocol/` / `tools/`
Owns runtime posture:
- how OpenClaw should operate campaigns
- whether/how this should become an agent skill
- validators / init / advance / inspect helpers
- thin operator skill blueprint once the kernel is stable enough

Current runtime-first surfaces:
- `tools/validate-mandate.py`
- `tools/init-campaign.py`
- `tools/advance-campaign.py`
- `tools/inspect-campaign.py`
- `campaigns/` for file-backed campaign instances
- `tests/test_runtime_schema_fixtures.py` for contract-locking schema fixtures

Runtime parser posture:
- mandate/default YAML parsing is standardized on PyYAML (`yaml.safe_load`)

Runtime hardening posture:
- schema contracts for `CampaignState`, `WorkerStatePatch`, and `ReceiptRecord` are now locked by explicit valid/invalid fixtures
- phase movement is no longer just implicit dispatcher flow; runtime now enforces explicit transition semantics including forward / retry / failure / back-transition cases
- current hardening order is: schema fixtures first, explicit phase transition semantics second, adapter-boundary proof later when a second adapter is materially real

## Reference adapter
- `adapters/steamer/` is the first reference adapter.
- It should be treated as a proving ground for the kernel, not as the kernel definition source.

## Release / packaging topology
- This repo is the curated public packaging surface for outside operators.
- It exposes the kernel, adapters, tools, tests, examples, and seeded campaign material.
- It intentionally omits handoffs and internal-only working notes from the working playbook.
- Public posture remains: experimental / advanced-operator, not beginner-facing generic orchestration.
