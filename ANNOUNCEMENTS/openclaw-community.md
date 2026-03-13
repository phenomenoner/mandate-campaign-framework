# OpenClaw community announcement — Mandate Campaign Framework v0.1.0 (Experimental)

I just spun out a new public repo:
- https://github.com/phenomenoner/mandate-campaign-framework

**Mandate Campaign Framework** is a schema-strict, phase-gated runtime for advanced OpenClaw campaigns.

Short version:
- durable file-backed campaign state
- explicit contracts
- validate → init → advance → inspect runtime loop
- explicit phase transition semantics
- operator-gated progression

This is meant for power users / workflow designers, not for beginners looking for a no-code automation builder.

Current posture:
- experimental public beta
- real runtime surface
- one reference adapter (`steamer`)
- one second adapter sketch for genericity pressure-testing
- still proving broader adapter maturity and public UX

Why I think it matters:
Most agent workflows still go mushy around state, retries, and operator control. This line is trying to make those boundaries explicit and inspectable instead of magical.

If that sounds useful, start with:
- README
- TOPOLOGY
- STATUS
- tools/README

If you want, I can also turn this into a thin OpenClaw operator skill later — but only after the kernel/adapter boundary gets a bit more battle-tested.
