# Steamer Phase Mapping

Map the generic kernel phases to Steamer-specific execution shape.

## Generic -> Steamer
- `INTAKE` -> `mandate-intake`
- `EXPLORE` -> `idea-scout`
- `EVALUATE` -> `fast-triage` + `deep-validation`
- `SYNTHESIZE` -> `card-synthesis` + `shadow-packaging`
- `GATE` -> `operator-gate`
- `DELIVER` -> shadow-reviewable candidate packet / governed hold-kill packet
- `CLOSED` -> promoted / held / killed / expired

## Why this matters
This mapping lets the framework stay generic while still honoring the real shape of Steamer work.

## Anti-capture note
If the kernel ever needs to know what `shadow-ready` means, the adapter boundary has already failed.
