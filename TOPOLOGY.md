# mandate-campaign-framework — TOPOLOGY

## TL;DR

Four-layer shape:
- **kernel** — shared campaign contracts and phase semantics
- **adapters** — domain mappings
- **runtime/tools** — bounded dispatcher + inspect surfaces
- **proof surfaces** — replayable bundles and tests

Current autonomy reality:
- operator-gated
- file-backed
- inspectable
- intentionally narrow
- not a stable general orchestration system

## Topology sketch

```text
operator mandate
      |
      v
[MandateSpec] -> [CampaignState + phase machine] -> [advance dispatcher] -> [runtime adapter]
      |                                                       |                    |
      |                                                       v                    v
      |                                                [receipts + artifacts] -> [inspect]
      |                                                                            |
      +------------------------------> [operator gate / replay / close-out] <------+
```

## Executable adapter topology

### `steamer`
Reference proving-ground adapter with real bounded behavior for:
- candidate queue seeding
- idea-scout / validation / synthesis progression
- operator-gate escalation
- replay decisions (`approve_shadow_review`, `reject_shadow_review`)
- queue-empty recovery via `--resume`
- strict seeded blocked-visibility close-out via `--close-blocked-visibility`

### `openclaw-mem`
Minimal second executable adapter proving the framework is not only a Steamer wrapper.
Its bounded packet spine materializes:
- source signal intake
- failure clusters
- root-cause candidates
- next-experiment proposal
- operator-gate packet
- delivered dev-decision packet

### `content-production`
Still a sketch adapter. Useful for contract pressure-testing, not for maturity claims.

## Proof topology

Public proof is centered on:
- `examples/proof-bundles/PROOF_INDEX.md`
- `examples/proof-bundles/replay-all.sh`
- `examples/operator-gate-reject-demo.sh`
- `tests/`

The six seeded proof bundles cover the current narrow operator-loop slices. They are meant to be replayable and inspectable, not marketed as broad production evidence.

## Roadmap calibration

- **Phase 0 done**
- **Phase 1 done**
- **Phase 2 done**
- **Phase 3 done**
- **Phase 4 in progress**
- **Phase 5 minimally done**

Interpretation rule:
- the framework direction is real
- the operator loop is no longer only theoretical
- repeatability and external usability are still open work

## Packaging caution

Use this repo as an explicit-contract, operator-facing runtime package.
Do not treat it as a claim that generic orchestration maturity is already solved.
