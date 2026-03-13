# Skill Packaging Consideration

## Short answer
**Yes, eventually — but not as one giant monolithic skill that bundles kernel + adapter + runtime assumptions together.**

## Recommended packaging posture
Package this into OpenClaw as a **thin operator skill**, not as the whole framework itself.

### Good skill shape
A skill should help the operator:
- write / validate a mandate
- start or inspect a campaign
- explain gate status
- summarize a delivery packet

### Bad skill shape
A skill should **not** become:
- the canonical store of campaign state
- the only place kernel contracts live
- a giant Steamer-shaped workflow bundle pretending to be general

## Recommended split
1. **Framework repo/docs/runtime** remain the source of truth
2. **Thin OpenClaw skill** becomes the operator-facing launcher / explainer
3. **Adapters** stay as repo artifacts; adapter-specific helper skills can exist later if warranted

## When it is a good idea
It becomes a good skill candidate when:
- kernel contracts stop changing every few days
- at least one adapter is battle-tested
- campaign init / inspect / gate / deliver flows are predictable

## When it is a bad idea
It is premature if:
- the framework is still being discovered through Steamer-specific iteration
- the skill would mostly mirror unstable docs
- the skill would hardcode Steamer nouns into generic flows

## Recommended OpenClaw operating model
- skill entrypoint: `start_campaign` / `inspect_campaign` / `summarize_delivery`
- repo files remain authoritative
- background dispatcher remains outside the skill prompt itself
- skill should orchestrate, not embody the kernel

## Current verdict
- **Do not** ship a full "mandate-campaign-framework + Steamer adapter" monolithic skill yet.
- **Do** plan for a thin operator skill once the kernel contracts are stable enough.
