# Canonical proof index (operator-facing)

This is the single compare/replay surface for the six current canonical proof bundles.

## Quick use (from project root)

```bash
cd .
```

Replay one bundle:

```bash
bash examples/proof-bundles/steamer-shadow-proof-seeded-v1/replay.sh
bash examples/proof-bundles/steamer-resume-recovery-seeded-v1/replay.sh
bash examples/proof-bundles/steamer-resume-evaluate-recovery-seeded-v1/replay.sh
bash examples/proof-bundles/steamer-cycle-budget-exhaustion-seeded-v1/replay.sh
bash examples/proof-bundles/steamer-operator-gate-timeout-visibility-seeded-v1/replay.sh
bash examples/proof-bundles/steamer-operator-gate-reject-replay-seeded-v1/replay.sh
```

Replay all six bundles in one pass:

```bash
bash examples/proof-bundles/replay-all.sh
# optional output root
bash examples/proof-bundles/replay-all.sh /tmp/mcf-proof-replays
```

## Bundle comparison

| Bundle | What it proves | Key end state | Replay command/path | Known caveats / gaps |
|---|---|---|---|---|
| `steamer-shadow-proof-seeded-v1` | End-to-end seeded shadow run through `INTAKE -> ... -> OPERATOR_GATE`, with explicit operator replay (`approve_shadow_review`) and inspectable artifacts/receipts. | `phase=DELIVER`, `status=ACTIVE`, drift `clean`, replay receipt `008_steamer_operator_gate_decision_replayed`. | `bash examples/proof-bundles/steamer-shadow-proof-seeded-v1/replay.sh` | Positive replay path only (`approve_shadow_review`). |
| `steamer-resume-recovery-seeded-v1` | Blocked `EXPLORE` (queue-empty) wake reason + explicit `--resume` recovery to continue work. | post-resume `phase=EVALUATE`, `status=ACTIVE`, drift `clean`, recovery receipt `002_steamer_resume_retry_idea_scout`. | `bash examples/proof-bundles/steamer-resume-recovery-seeded-v1/replay.sh` | Blocked condition is fixture-forced queue-empty only; no broader blocked-cause matrix yet. |
| `steamer-resume-evaluate-recovery-seeded-v1` | Blocked `EVALUATE` (queue-empty) wake reason + explicit `--resume` back-shift recovery to restore candidate context. | blocked inspect now stays `drift=clean` with note `seeded_blocked_evaluate_fixture`; post-resume `phase=EXPLORE`, `status=ACTIVE`, `back_transitions_remaining=0`, recovery receipt `002_steamer_resume_recover_evaluate_to_explore`. | `bash examples/proof-bundles/steamer-resume-evaluate-recovery-seeded-v1/replay.sh` | Explicit control-lane seeded fixture; recovery depth intentionally narrow (one bounded back-shift rule). |
| `steamer-cycle-budget-exhaustion-seeded-v1` | Adapter-dispatch cycle-budget exhaustion stop path with explicit block receipt + wake reason. | `phase=EXPLORE`, `status=BLOCKED`, `wakeup.reason=cycle_budget_exhausted`, drift `clean`, receipt `001_cycle_budget_exhausted`. | `bash examples/proof-bundles/steamer-cycle-budget-exhaustion-seeded-v1/replay.sh` | Fixture-forced `cycle_budget=0` setup only; does not yet cover retry-budget interplay matrix. |
| `steamer-operator-gate-timeout-visibility-seeded-v1` | Operator-gate stall/timeout visibility slice: runtime `GATE -> OPERATOR_GATE` escalation plus inspect-level stale-timeout signal. | `phase=GATE`, `status=OPERATOR_GATE`, `wakeup.reason=steamer_shadow_review_gate`, `operator_gate_visibility.signal=operator_gate_timeout_exceeded`, `stale=true`. | `bash examples/proof-bundles/steamer-operator-gate-timeout-visibility-seeded-v1/replay.sh` | Visibility slice only; does not auto-close or enforce gate-timeout policy actions. |
| `steamer-operator-gate-reject-replay-seeded-v1` | Canonical negative operator decision replay with explicit pre-replay gate evidence, replay invocation/note, durable receipt+artifact, and closed-state verification. | pre-replay `phase=GATE,status=OPERATOR_GATE`; post-replay `phase=CLOSED`, `status=CLOSED`, replay receipt `008_steamer_operator_gate_decision_replayed`. | `bash examples/proof-bundles/steamer-operator-gate-reject-replay-seeded-v1/replay.sh` | Narrow to one bounded reject decision path (`reject_shadow_review`) and one seeded candidate. |

## Canonical pointer map

Machine-readable index: `examples/proof-bundles/INDEX.json`

Per-bundle entry points:
- `examples/proof-bundles/steamer-shadow-proof-seeded-v1/README.md`
- `examples/proof-bundles/steamer-resume-recovery-seeded-v1/README.md`
- `examples/proof-bundles/steamer-resume-evaluate-recovery-seeded-v1/README.md`
- `examples/proof-bundles/steamer-cycle-budget-exhaustion-seeded-v1/README.md`
- `examples/proof-bundles/steamer-operator-gate-timeout-visibility-seeded-v1/README.md`
- `examples/proof-bundles/steamer-operator-gate-reject-replay-seeded-v1/README.md`

Optional concise standalone demo pointer:
- `examples/operator-gate-reject-demo.sh` (`OPERATOR_GATE -> CLOSED` via `--replay-decision reject_shadow_review`)

## Remaining proof gap after this index

The proof set is now easy to discover/replay, but coverage is still intentionally narrow:
- blocked recovery captures remain queue-empty focused,
- cycle-budget stop is proven for one forced fixture state only,
- gate-timeout capture is visibility-only (no auto-action policy),
- no broad blocked-cause/retry-budget/action-policy matrix yet.
