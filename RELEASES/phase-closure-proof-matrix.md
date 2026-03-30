# Phase-closure proof matrix

This is the public compare surface for the still-open release phases.

## Current forcing move

The current forcing move is to make the remaining phases legible through repo-local proof, drills, usability, and semantics surfaces — not to wait on active development in another product line.

## Matrix

| Phase | Current read | What is already real here | Current compare surface | What still has to turn green |
|---|---|---|---|---|
| 4 — Repeatability proof | **Open / in progress** | six canonical seeded proof bundles, replay helpers, runtime/proof tests | `examples/proof-bundles/PROOF_INDEX.md`, `examples/operator-drills.md`, `tests/` | broader repeated clean runs, lower interpretation load, less Steamer concentration |
| 5 — Anti-domain-capture proof | **Minimally done** | second executable adapter path exists (`openclaw-mem`) and shared contracts still stay generic | `adapters/openclaw-mem/`, `tests/test_adapter_runtime.py`, `tests/test_advance_campaign_dispatch.py` | stronger public-safe second-adapter drills, more than mere runtime presence |
| 6 — Beta operator usability | **Open** | public-safe examples and proof bundle index exist | `examples/operator-drills.md`, `protocol/external-operator-usability-pack.md` | an external advanced operator should be able to run the basics without mind-reading |
| 7 — Stable semantics freeze | **Open** | the core CLI names and inspect/replay surfaces are now explicit enough to audit | `protocol/semantics-freeze-checklist.md`, `tools/README.md` | freeze-now vs still-moving semantics must stay explicit and small |
| 8 — Release candidate | **Open** | proof bundles, tests, operator drills, and current limits are now gatherable in one repo | this file + `STATUS.md` + `tests/` | assemble a small RC packet with known limits, validation commands, and no trust-killing ambiguity |

## Exit-rule reminder

A later phase can only be called closed when:
- the compare surface is explicit
- the execution primitive is named
- the resulting proof is inspectable without tribal knowledge
- the maturity language stays honest
