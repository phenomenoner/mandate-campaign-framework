# Adapter Template

Use this when bringing a new domain into the framework.

## Adapter must define
- domain-specific mandate extension fields
- item / candidate shape
- authority classifier
- generic-phase -> domain-substep mapping
- domain metadata for delivery packet

## Adapter must not do
- modify kernel contracts to fit domain nouns
- redefine generic phase semantics
- smuggle domain assumptions back into `kernel/`
