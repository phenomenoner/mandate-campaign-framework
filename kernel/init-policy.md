# Init Policy

Purpose: define who is responsible for initial campaign defaults.

## Kernel-owned defaults
Unless explicitly overridden by adapter defaults, `init-campaign` should initialize:
- `phase = INTAKE`
- `status = ACTIVE`
- `cycle_budget = 8`
- `back_transitions_remaining = 1`
- `active_item_id = null`
- `item_queue = []`
- `wakeup.needed = false`

## Adapter override posture
Adapters may provide **initializer hints** for:
- `cycle_budget`
- `back_transitions_remaining`

These hints may override kernel defaults, but adapters may not introduce new kernel state fields.

## Recommended adapter file
If used, adapter defaults should live at:
- `adapters/<adapter>/defaults.yaml`

## Design rule
`init-campaign` owns canonical initial state.
Adapters may suggest budgets; they do not own the campaign state schema.
