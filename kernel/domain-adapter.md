# DomainAdapter

Purpose: define the extension point between the generic campaign kernel and any concrete domain.

## Required responsibilities
A domain adapter must define:
- domain-specific mandate extension fields
- item / candidate shape
- authority classifier
- phase mapping from kernel phases to domain sub-steps
- delivery packet domain metadata

## Required capabilities
At minimum, an adapter should be able to:
- normalize domain mandate extensions
- generate or prioritize items/candidates
- evaluate one active item with domain evidence
- classify whether an action is within bounds, requires gate, or must stop
- package a domain-aware delivery packet

## Boundary rule
The adapter may depend on kernel contracts.
The kernel must not import or assume adapter nouns.

## Minimum mental model
- kernel owns: campaign runtime
- adapter owns: domain semantics
- workers own: bounded execution of one step

## Authority classifier
Adapters should reduce domain-specific authority to one of:
- `within_bounds`
- `requires_gate`
- `stop`

The framework enforces the result; the adapter decides the meaning.
