# 2026-03-17 — Tetora-role fit for mandate-campaign and Steamer

## Verdict

`Tetora-role` style multi-role surfaces are a **good fit at the boundary layer** of `mandate-campaign-framework`, and a **bad fit as the kernel/runtime control plane**.

Use roles for:
- intake / triage
- evidence summarization
- operator-facing delivery narration
- conservative hold / red-team judgment

Do **not** use roles as the source of truth for:
- campaign phase transitions
- state mutation authority
- operator gates
- live-enable / capital-posture decisions
- core runtime semantics

## Why the fit is partial, not universal

The framework kernel is intentionally built around:
- `Mandate -> Campaign -> Delivery Packet`
- explicit campaign state
- bounded worker progression
- schema validation
- phase-gated advancement
- receipt-backed operator review

That layer gains value from **contracts and inspectability**, not from persona differentiation.
If kernel decisions are re-expressed as role-to-role dialogue, the system drifts back toward prompt theater and away from explicit runtime truth.

## Fit map

### 1) Kernel / runtime layer — low fit

Low fit for Tetora-role surfaces.

Reason:
- kernel truth should stay domain-free, deterministic, and schema-strict
- transition legality should remain machine-checkable
- worker output should remain bounded by contract, not by conversational consensus

Recommended posture:
- keep the kernel role-agnostic
- keep dispatcher / transition / receipt semantics outside of role-play orchestration

### 2) Adapter / operator layer — high fit

High fit for Tetora-role surfaces.

Reason:
- adapters already own domain meaning
- operator surfaces already translate state into human judgment
- these tasks benefit from persistent role specialization without needing write authority

Strong candidate roles:
- **Mandate Intake / Triage role**
  - classify a new request into the right adapter or reject campaign creation
- **Delivery Packet Narrator role**
  - convert receipts and artifacts into concise operator-facing briefings
- **Hold Judge role**
  - read-only conservative review that explains why a campaign should remain held

These roles should emit:
- notes
- summaries
- proposed classifications
- explicit `UNKNOWN` / `HOLD` / `INSUFFICIENT_EVIDENCE` judgments

They should **not** directly mutate campaign state.

### 3) Steamer adapter layer — medium to high fit

Steamer is a stronger fit than generic coding or ops work because its workflow already contains natural role-like surfaces:
- scout / candidate discovery
- evidence-pack assembly
- operator brief construction
- risk / hold review

Useful Steamer role candidates:
- **Scout role**
  - read-only candidate discovery and relevance filtering
- **Evidence role**
  - summarize replay, live-sim, and nightly receipts into operator-ready evidence packs
- **Operator Brief role**
  - translate campaign state into strategy/operator language
- **Risk Gate role**
  - conservative read-only pass focused on why a candidate should not advance

Hard boundary:
- no role should directly decide capital posture
- no role should directly enable live execution
- no role should become a broker/execution surrogate

## Comparison with our existing workflow stack

The best interpretation is:
- Tetora-role = **persistent functional entrypoints**
- serial subagent / sprint / slow-cook = **execution and governance engine**

So the right composition is:
- roles help with seeing, summarizing, routing, and criticizing
- campaign/sprint/slow-cook machinery continues to own state progression, gates, receipts, and rollback posture

In other words:
- role layer = horizontal functional split
- campaign/sprint/slow-cook = vertical control and delivery discipline

## Where this is probably not worth it

Low-return use cases:
- replacing serial coding subagents with multiple chatting coding personas
- moving campaign advancement decisions into inter-role debate
- using roles to simulate confidence without distinct context, permissions, or verification contracts

For ordinary coding execution, our current stack remains better:
- serial subagent for phase separation
- sprint controller for milestone/gate discipline
- slow-cook for long-horizon low-noise accumulation

## Recommended later experiment

If we test this later, start with a narrow read-only role layer:

1. **Steamer Scout role**
2. **Delivery Brief role**
3. **Hold Judge role**

Success condition:
- better routing / briefing / conservative review quality
- no erosion of kernel contracts
- no new ambiguity around who owns state transitions

Failure mode to watch:
- role theater starts replacing explicit receipts, gate logic, or operator authority.
