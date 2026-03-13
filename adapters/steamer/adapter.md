# Steamer Adapter

Steamer is the first **reference adapter** for the mandate-campaign framework.

## Important boundary
Steamer is a proving ground, not the kernel.
Its current `autonomous-slow-cook` lane should be read as:
- an adapter discovery source
- a reference implementation of campaign state / receipts / bounded workers
- not the product definition source for the framework

## Domain nouns that stay in the adapter
- strategy
- ticker / market universe
- replay / backtest
- shadow-ready
- paper-only
- regime
- portfolio governor

## Adapter responsibilities
- map trading strategy mandates into candidate-oriented campaigns
- define what counts as a candidate, evidence, hold, iterate, kill, shadow-ready
- classify authority boundaries (e.g. shadow-only vs capital posture changes)
- package delivery in strategy/operator language

## Current mapping source
- `projects/steamer/lanes/autonomous-slow-cook/`
- `projects/steamer/lanes/TOPOLOGY.md`
- `projects/steamer/topology-pack-l0.md`

## Current caution
The current Steamer pilot has already proven that campaign state, receipts, and domain artifacts can advance autonomously.
It has **not** yet proven that the framework kernel should speak Steamer's nouns.
