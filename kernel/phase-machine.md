# Phase Machine

## Generic phases
- `INTAKE`
- `EXPLORE`
- `EVALUATE`
- `SYNTHESIZE`
- `GATE`
- `DELIVER`
- `CLOSED`

## Valid typical transitions
- `INTAKE -> EXPLORE`
- `EXPLORE -> EVALUATE`
- `EVALUATE -> SYNTHESIZE`
- `SYNTHESIZE -> GATE`
- `GATE -> DELIVER`
- `GATE -> EVALUATE`
- `GATE -> CLOSED`
- `DELIVER -> CLOSED`
- `EVALUATE -> EXPLORE` only if back-transition budget remains

## Runtime transition semantics (dispatcher)
- The dispatcher validates transitions explicitly instead of trusting worker intent.
- Result semantics:
  - `ADVANCE`: must be a valid forward transition; may use approved back transitions.
  - `BLOCK`: retry semantics only (`phase` unchanged, `status=BLOCKED`).
  - `ESCALATE`: must set `status=OPERATOR_GATE`; phase may stay put or move to `GATE`.
  - `FAIL`: may retry (`phase` unchanged), use approved back-transition, or close.
  - `DELIVER`: must move to `DELIVER` or `CLOSED`.
- Back-transitions consume budget:
  - `state_patch.back_transitions_remaining` must decrement by exactly 1.
  - no back-transition is allowed once budget is exhausted.

## Design rules
- The kernel phase machine must remain domain-free.
- Adapters may decompose a generic phase into internal sub-steps, but the kernel should still see the generic phase.
- A campaign can fail or block; failure is a first-class outcome, not a bug.

## Anti-capture rule
If a proposed phase name would sound absurd in a non-Steamer domain, it does not belong in the kernel.
