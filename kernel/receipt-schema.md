# ReceiptRecord

Purpose: give the kernel one machine-checkable receipt shape before runtime tooling diverges.

## Required fields
- `receipt_id`
- `campaign_id`
- `mandate_id`
- `phase`
- `event`
- `summary`
- `artifact_refs`
- `created_at`

## Design rules
- receipts are append-only
- the kernel should be able to tail receipts without parsing domain-specific prose
- summary should stay short; bulky evidence belongs in artifacts
- adapter-specific detail belongs in `artifact_refs` targets, not in the receipt schema itself

## Minimum shape
```json
{
  "receipt_id": "000_campaign_created",
  "campaign_id": "2026-03-example",
  "mandate_id": "2026-03-example",
  "phase": "INTAKE",
  "event": "campaign_created",
  "summary": "campaign initialized from validated mandate",
  "artifact_refs": ["MANDATE.yaml", "CAMPAIGN_STATE.json"],
  "created_at": "2026-03-13T14:00:00+08:00"
}
```
