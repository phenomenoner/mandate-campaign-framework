# topology-pack-l0 — mandate-campaign-framework

Pointers:
- README: `README.md`
- status: `STATUS.md`
- cycle log: `CYCLELOG.md`
- topology: `TOPOLOGY.md`
- mandate contract: `kernel/mandate-spec.md`
- campaign state: `kernel/campaign-state.md`
- phase machine: `kernel/phase-machine.md`
- worker protocol: `kernel/worker-protocol.md`
- worker state patch: `kernel/worker-state-patch.md`
- receipt schema: `kernel/receipt-schema.md`
- init policy: `kernel/init-policy.md`
- delivery packet: `kernel/delivery-packet.md`
- domain adapter contract: `kernel/domain-adapter.md`
- kernel freeze: `kernel/v0.1-freeze.md`
- dispatcher: `kernel/dispatcher.md`
- adapter contract: `adapters/README.md`
- Steamer reference adapter: `adapters/steamer/adapter.md`
- content adapter sketch: `adapters/content-production/adapter.md`
- OpenClaw operation: `protocol/openclaw-operation.md`
- skill packaging note: `protocol/skill-packaging.md`
- thin skill blueprint: `protocol/openclaw-operator-skill-blueprint.md`
- tools README: `tools/README.md`
- runtime schema fixtures: `tests/test_runtime_schema_fixtures.py`
- public launch note: `TECH_NOTES/2026-03-13_public-launch-positioning.md`
- example campaigns: `campaigns/README.md`

## 1-paragraph model
The framework is a durable, phase-gated campaign runtime that turns a sealed operator mandate into a delivery packet. The kernel stays domain-free; adapters translate domain nouns and authority rules into campaign work. OpenClaw should operate it with sparse wakeups, durable file state, and bounded workers. Current runtime hardening adds two explicit guardrails: schema-fixture contract locks for `CampaignState` / `WorkerStatePatch` / `ReceiptRecord`, and enforced phase transition semantics covering forward, retry, failure, and back-transition behavior. Publicly, it should be positioned as an experimental advanced-operator runtime rather than a beginner-facing generic orchestration product.
