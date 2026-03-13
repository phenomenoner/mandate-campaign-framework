# CampaignState

Purpose: keep the campaign alive even when workers die.

## Required fields
- `campaign_id`
- `mandate_id`
- `phase`
- `status`
- `active_item_id`
- `item_queue`
- `cycle_budget`
- `back_transitions_remaining`
- `wakeup`
- `last_receipt`
- `updated_at`

## Status values
- `ACTIVE`
- `BLOCKED`
- `OPERATOR_GATE`
- `CLOSED`

## Design rules
- Keep state small enough for a dispatcher to load fully.
- Domain-specific detail should live in adapter artifacts, not in kernel state.
- State transitions should be append-receipted and current-state atomically replaced.
- `init-campaign` owns canonical initial state; adapters may only override budget hints.

See also:
- `kernel/init-policy.md`
- `kernel/receipt-schema.md`

## Minimum shape
```json
{
  "campaign_id": "2026-03-example",
  "mandate_id": "2026-03-example",
  "phase": "EXPLORE",
  "status": "ACTIVE",
  "active_item_id": null,
  "item_queue": [],
  "cycle_budget": 8,
  "back_transitions_remaining": 1,
  "wakeup": {"needed": false, "reason": null},
  "last_receipt": {"path": null, "summary": "campaign created"},
  "updated_at": "2026-03-13T14:00:00+08:00"
}
```
