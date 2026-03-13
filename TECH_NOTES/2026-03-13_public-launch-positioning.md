# 2026-03-13 — public launch positioning for mandate-campaign-framework

## Verdict

`mandate-campaign-framework` is worth releasing publicly **as an experimental / public-beta product for advanced OpenClaw operators**.
It is **not** ready to be presented as a beginner product or as a fully proven general orchestration platform.

## Why this is releasable now

What is real today:
- file-backed campaign runtime exists: `validate -> init -> advance -> inspect`
- campaign state is durable and inspectable
- schema contracts exist for `CampaignState`, `WorkerStatePatch`, and `ReceiptRecord`
- runtime now enforces explicit phase transition semantics including retry / failure / back-transition behavior
- there is one real reference adapter (`steamer`) and one second adapter sketch used to pressure-test anti-domain-capture boundaries

This means the project is no longer only a design memo. It now has a real operator model, state model, execution model, and validation model.

## What must not be overclaimed

Do **not** market this as:
- a beginner-friendly no-code automation builder
- a polished end-user app
- a fully proven domain-agnostic orchestration platform
- a mature adapter/plugin ecosystem

The kernel discipline is real. The adapter genericity is still being proved.

## Recommended public posture

### Recommended title
- `Mandate Campaign Framework v0.1 (Experimental)`

### Recommended tagline
- `A schema-strict, phase-gated runtime for advanced OpenClaw campaigns.`
- alternate angle: `Durable execution for operator-driven OpenClaw campaigns.`

### Target user
- advanced OpenClaw operators
- workflow designers
- ops-heavy builders
- users who value durable state, bounded progression, operator gates, and inspectable flow

### Release scope
- framework kernel
- one reference adapter
- one seeded example campaign
- `validate-mandate` / `init-campaign` / `advance-campaign` / `inspect-campaign`
- direct docs about operator responsibilities and current limits

### Honest beta disclaimer
- the runtime is real
- schema discipline and phase semantics are the strongest current layer
- adapter-boundary proof and operator UX are still being hardened
- use this if you want predictability / state / governance / inspectability
- do not use this if you want magic / zero-setup / instant generic automation

## CLI advisory convergence

One-shot advisory reviews from both Copilot CLI and Gemini CLI converged on the same judgment:
- public release is justified
- the correct posture is advanced-operator / experimental, not mass-market
- the strongest public asset is explicit runtime discipline (schema contracts + transition semantics + durable state)
- the main risk is overstating generic adapter maturity before it is proven by more than one materially real adapter

## Packaging decision

A separate public repo is justified.
That public repo should be a **curated product package** of the framework, not a dump of the full playbook working tree.

Include:
- root README with public-beta positioning
- status / topology / kernel docs
- adapters / tools / tests / examples / seeded campaign

Do not include:
- handoff artifacts
- internal-only working notes that are not useful to outside operators
- misleading claims that the runtime is more packaged than it is
