# Worker Protocol

## WorkerContextPack
The dispatcher, not the worker, assembles the worker context pack.

Minimum contents:
- `mandate`
- `campaign_state`
- `phase_instruction`
- `current_item`
- `receipts_tail`
- optional `adapter_context`

## WorkerResult
Minimum fields:
- `result_type` — `ADVANCE | BLOCK | ESCALATE | FAIL | DELIVER`
- `receipt`
- `artifact_refs`
- `state_patch`
- `next_phase_hint` (optional)
- `wakeup` (optional)

## WorkerStatePatch
See:
- `kernel/worker-state-patch.md`

Important rule:
- `state_patch` is a bounded kernel-state patch, not a free-form state dump
- dispatcher must reject patch keys outside the allowlist

## ReceiptRecord
See:
- `kernel/receipt-schema.md`

Important rule:
- workers may produce domain artifacts, but the kernel receipt shape should stay machine-checkable and domain-light

## Design rules
- Workers are bounded executors, not free-roaming strategists.
- Workers propose; the dispatcher validates and writes canonical state.
- Workers should operate on narrow context and produce one meaningful artifact bundle.
