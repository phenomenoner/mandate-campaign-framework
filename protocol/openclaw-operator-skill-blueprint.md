# OpenClaw Operator Skill Blueprint

Purpose: describe the future thin operator skill that sits on top of the framework.

## Principle
The skill should be a **thin operator shell** over repo/runtime truth.
It should not become the framework.

## Candidate entrypoints
- `start_campaign`
- `inspect_campaign`
- `explain_gate`
- `summarize_delivery`

## What the skill should do
- help the operator assemble or validate a mandate
- start or resume a campaign using repo-backed files
- summarize current status from campaign state + receipts
- explain what decision is being asked at a gate
- compress a delivery packet into a short operator-friendly answer

## What the skill should not do
- store canonical campaign state inside prompt memory
- hardcode one adapter's nouns into generic flows
- replace dispatcher/runtime responsibilities
- silently mutate kernel contracts

## Recommended OpenClaw operating shape
- skill = operator interface
- repo files = source of truth
- dispatcher/background workers = execution substrate
- chat = intake / review / gate / summary surface

## Candidate maturity gate before shipping
Only cut the skill when all are true:
- kernel contracts are not moving every few days
- at least one adapter has completed a full campaign path
- gate / unblock / deliver semantics are predictable
- thin skill commands can be described without leaking domain internals
