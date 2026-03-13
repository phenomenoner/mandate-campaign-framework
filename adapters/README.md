# adapters

Adapters bind the generic campaign kernel to a domain.

## Adapter responsibilities
- define domain-specific mandate extension fields
- define item/candidate shapes
- classify authority boundaries
- map generic phases to domain sub-steps
- produce domain-specific delivery metadata

## Hard rule
The kernel must not import adapter assumptions back into itself.
If a kernel change exists only to make one adapter more comfortable, it is probably the wrong change.

## Current adapters
- `steamer/` — first reference adapter / proving ground
- `content-production/` — second adapter sketch for anti-domain-capture pressure testing
