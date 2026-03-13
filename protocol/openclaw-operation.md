# OpenClaw Operation Notes

## Recommended posture
Operate the framework in OpenClaw as:
- durable files as source of truth
- low-cadence dispatcher / scheduler
- bounded workers with narrow context packs
- sparse user wakeups

## What should wake the user
- authority gate
- blocker requiring external resource
- promotion/delivery packet ready
- stop-loss / TTL exhausted

## What should not wake the user
- ordinary phase transitions
- internal receipts
- routine pruning
- expected failed branches

## OpenClaw runtime shape
- main chat: intake / review / operator decisions
- background workers or delegated runs: bounded campaign steps
- campaign state lives in files, not in chat history

## Important rule
Do not use heartbeat-style main-agent babysitting as the execution substrate.
The campaign should survive worker/session death because the files survive.
