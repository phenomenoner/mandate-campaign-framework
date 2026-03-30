# mandate-campaign-framework — TOPOLOGY

## TL;DR

Four-layer shape:
- **kernel** — shared campaign contracts and phase semantics
- **adapters** — domain mappings
- **runtime/tools** — bounded dispatcher + inspect surfaces
- **proof / closure surfaces** — replayable bundles, drills, release matrix, and tests

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

## Proof / closure topology

Public proof is centered on:
- `examples/proof-bundles/PROOF_INDEX.md`
- `examples/proof-bundles/replay-all.sh`
- `examples/operator-drills.md`
- `examples/operator-gate-reject-demo.sh`
- `RELEASES/phase-closure-proof-matrix.md`
- `protocol/external-operator-usability-pack.md`
- `protocol/semantics-freeze-checklist.md`
- `tests/`

The six seeded proof bundles cover the current narrow operator-loop slices.
The newer closure surfaces turn those bounded proofs into a single product-native compare surface for the still-open release phases.

## Roadmap calibration

- **Phase 0 done**
- **Phase 1 done**
- **Phase 2 done**
- **Phase 3 done**
- **Phase 4 in progress**
- **Phase 5 minimally done**
- **Phase 6+ open**

Interpretation rule:
- the framework direction is real
- the operator loop is no longer only theoretical
- the remaining gate is now less about other repos and more about whether this repo can present repeatability, usability, and semantics honestly

## Packaging caution

Use this repo as an explicit-contract, operator-facing runtime package.
Do not treat it as a claim that generic orchestration maturity is already solved.
