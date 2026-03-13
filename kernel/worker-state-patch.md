# WorkerStatePatch

Purpose: prevent domain nouns from leaking into canonical `CampaignState` through loose worker patches.

## Allowed fields
A worker state patch may only touch these kernel fields:
- `phase`
- `status`
- `active_item_id`
- `item_queue`
- `cycle_budget`
- `back_transitions_remaining`
- `wakeup`
- `last_receipt`

## Not allowed
- adapter-specific metadata
- domain evaluation details
- arbitrary extra keys
- artifact contents

Those belong in artifacts / adapter artifacts referenced by receipts.

## Design rule
Workers propose a bounded patch; the dispatcher validates it against this allowlist before writing canonical state.

## Why this matters
Without this allowlist, the easiest way for Steamer nouns or any future domain nouns to colonize the kernel is by sneaking them into `CampaignState` as “just one more patch field”.
