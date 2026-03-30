# Semantics freeze checklist

This checklist is the current Phase 7 bridge.
It makes the moving parts explicit instead of pretending everything is already stable.

## Freeze-now candidates

These surfaces should be treated as near-frozen unless there is a very good reason to change them:
- CLI entrypoints:
  - `validate-mandate.py`
  - `init-campaign.py`
  - `advance-campaign.py`
  - `inspect-campaign.py`
- phase names:
  - `INTAKE`, `EXPLORE`, `EVALUATE`, `SYNTHESIZE`, `GATE`, `OPERATOR_GATE`, `DELIVER`, `CLOSED`
- status names:
  - `ACTIVE`, `BLOCKED`, `OPERATOR_GATE`, `CLOSED`
- replay decisions:
  - `approve_shadow_review`
  - `reject_shadow_review`
- explicit operator recovery / close-out verbs:
  - `--resume`
  - `--replay-decision`
  - `--close-blocked-visibility`
- inspect JSON surfaces that operators now depend on:
  - `blocked_cause`
  - `resume_hint`
  - `operator_gate_visibility`
  - `blocked_visibility_closeout_eligibility`
  - adapter identity / registration fields

## Still-moving surfaces

These can still evolve without pretending compatibility is settled:
- the exact set of seeded proof bundles
- adapter-specific artifact shapes under `artifacts/`
- example mandate wording
- README / release-matrix phrasing
- how broad the second-adapter proof becomes

## Phase 7 exit questions

Do not call semantics frozen until all of these can be answered cleanly:
1. Can an operator tell which CLI verb to use at each gate/block condition?
2. Are replay-decision and close-out semantics narrow enough that the words will not keep changing?
3. Are inspect JSON keys stable enough to document for third-party operator tooling?
4. Is the intentionally-unstable list short, explicit, and non-scary?
5. Can the changelog story be told without “sorry, that noun changed again” every week?
