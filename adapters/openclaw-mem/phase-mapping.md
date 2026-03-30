# openclaw-mem Phase Mapping

## Generic -> openclaw-mem dev-decision
- `INTAKE` -> source signal intake (harvest/triage pointer check)
- `EXPLORE` -> failure clustering
- `EVALUATE` -> root-cause candidate shaping
- `SYNTHESIZE` -> next experiment / decision packet synthesis
- `GATE` -> operator decision gate (accept/reject/defer)
- `DELIVER` -> bounded dev-decision packet delivered
- `CLOSED` -> run closed

## Note
Execution now materializes bounded mem artifacts at each phase (cluster/cause/proposal/gate/packet)
so packet-depth and proposal-actionability can be judged from bundle evidence instead of placeholder linear transitions.
