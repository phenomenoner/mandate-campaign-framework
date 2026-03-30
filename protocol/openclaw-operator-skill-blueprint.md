# OpenClaw Operator Skill Blueprint

Purpose: describe the thin operator skill that can now sit on top of the framework.

## Principle

The skill should stay a **thin operator shell** over repo/runtime truth.
It should not become the framework.

## Current posture

A thin skill is now justified for the **experimental / advanced-operator** product surface.
It is justified because the repo now has:
- bounded CLIs
- inspectable replay/gate mechanics
- public-safe drills
- a checked-in phase-closure matrix

It is **not** a license to ship a monolithic “framework-in-the-prompt” skill.

## Candidate entrypoints

- `validate_mandate`
- `start_campaign`
- `inspect_campaign`
- `run_operator_drill`
- `explain_gate`
- `summarize_delivery`

## What the skill should do

- help the operator assemble or validate a mandate
- start or resume a campaign using repo-backed files
- summarize current status from campaign state + receipts
- explain what decision is being asked at a gate
- run or explain the public-safe operator drills
- compress a delivery packet into a short operator-friendly answer

## What the skill should not do

- store canonical campaign state inside prompt memory
- hardcode one adapter's nouns into generic flows
- replace dispatcher/runtime responsibilities
- silently mutate kernel contracts
- promise stable semantics beyond the checked-in freeze checklist

## Recommended OpenClaw operating shape

- skill = operator interface
- repo files = source of truth
- dispatcher/background workers = execution substrate
- chat = intake / review / gate / summary surface

## Canonical operator read bundle

- `STATUS.md`
- `RELEASES/phase-closure-proof-matrix.md`
- `examples/operator-drills.md`
- `protocol/external-operator-usability-pack.md`
- `protocol/semantics-freeze-checklist.md`

## Shipping posture

Ship the skill as:
- thin
- explicit
- advanced-operator only
- honest about experimental status

Do not ship it as:
- a claim that the framework is already stable
- a substitute for repo truth
- a giant adapter-shaped monolith
