# MandateSpec

Purpose: seal operator intent into a durable campaign input.

## Required fields
- `mandate_id`
- `objective`
- `adapter`
- `scope`
- `constraints`
- `authority`
- `escalation`
- `success_criteria`
- `ttl_days`
- `delivery_shape`

## Design rules
- Intake should reject malformed mandates early.
- A mandate is not a conversation transcript.
- Workers do not renegotiate mandate scope.
- Authority should be enumerated, not hand-wavy.

## Minimum shape
```yaml
mandate_id: 2026-03-example
adapter: steamer
objective: >-
  Produce one shadow-reviewable candidate strategy packet.
scope:
  in: [TW equities, intraday, paper-only]
  out: [live capital changes]
constraints:
  no_new_paid_data: true
authority:
  autonomous: [idea_scout, card_synthesis, replay_triage]
  requires_gate: [capital_posture_change, promotion_to_live]
escalation:
  gate_conditions: [external_resource_needed, promotion_ready, stop_loss]
  operator_gate_timeout_days: 3
success_criteria:
  - one delivery packet with evidence summary
  - clear disposition for all touched candidates
ttl_days: 14
delivery_shape: shadow-reviewable strategy packet
```
