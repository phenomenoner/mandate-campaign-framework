# Dispatcher

Purpose: advance one campaign step at a time with durable state and sparse wakeups.

## Responsibilities
- load `CampaignState`
- assemble `WorkerContextPack`
- invoke one bounded worker
- validate `WorkerResult`
- validate `WorkerStatePatch` against the kernel allowlist
- validate `ReceiptRecord` shape
- write receipts / state atomically
- surface real gates only

## Non-responsibilities
- inventing new mandate scope
- silently widening authority
- turning domain-specific heuristics into kernel logic

## Core loop
1. validate current state
2. assemble narrow context pack
3. run one bounded worker
4. validate result schema
5. apply receipt + state patch atomically
6. decide whether to continue quietly, gate, deliver, or close

## Wakeup posture
Default wakeups should be sparse:
- real blocker
- authority gate
- promotion/delivery readiness
- stop-loss / TTL exhaustion

## Important rule
`expectedOutputs`-style planning hints are advisory, not canonical truth. Canonical truth is the artifact path actually written and receipted in the cycle.

See also:
- `kernel/worker-state-patch.md`
- `kernel/receipt-schema.md`
