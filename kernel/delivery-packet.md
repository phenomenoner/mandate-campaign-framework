# DeliveryPacket

Purpose: define the operator-facing output that makes the campaign worth running.

## Required fields
- `mandate_id`
- `summary`
- `artifacts`
- `confidence`
- `operator_actions`
- `receipt_log`
- `closed_at`

## Design rules
- Delivery packet matters more than conversational exhaust.
- An operator should be able to read the packet without replaying the entire campaign.
- Domain-specific metrics belong in `domain_metadata`, not in the kernel field list.

## Minimal operator questions a packet should answer
- What was produced?
- How confident should I be?
- What evidence supports it?
- What do I need to decide, if anything?
- What are the next recommended actions?
