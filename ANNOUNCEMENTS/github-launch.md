# GitHub launch announcement — Mandate Campaign Framework v0.1.0 (Experimental)

Today I’m releasing **Mandate Campaign Framework v0.1.0 (Experimental)**.

Repo:
- https://github.com/phenomenoner/mandate-campaign-framework

This is a **schema-strict, phase-gated runtime for advanced OpenClaw campaigns**.

It is built for operators who need:
- durable file-backed state
- bounded worker progression
- explicit transition semantics
- inspectable campaign flow
- operator-gated execution

## What ships

- a campaign kernel with frozen v0.1 contracts
- runtime CLI: `validate-mandate`, `init-campaign`, `advance-campaign`, `inspect-campaign`
- schema validation and tests for `CampaignState`, `WorkerStatePatch`, and `ReceiptRecord`
- explicit phase semantics for forward / retry / failure / back-transition behavior
- one reference adapter (`steamer`)
- one second adapter sketch (`content-production`) for pressure-testing kernel boundaries
- one seeded example campaign

## What this is not

This is **not**:
- a no-code builder
- a polished end-user app
- a claim that domain-agnostic orchestration maturity is already fully proven

The runtime is real. The contracts are real. The boundaries are explicit.
What is still being proven is broader adapter genericity and public operator UX.

If you care about predictability, state, governance, and inspectability in long-lived workflows, this should be interesting.
