#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_ROOT="${1:-$(mktemp -d)}"

BUNDLES=(
  "steamer-shadow-proof-seeded-v1"
  "steamer-resume-recovery-seeded-v1"
  "steamer-resume-evaluate-recovery-seeded-v1"
  "steamer-cycle-budget-exhaustion-seeded-v1"
  "steamer-operator-gate-timeout-visibility-seeded-v1"
  "steamer-operator-gate-reject-replay-seeded-v1"
)

cd "$PROJECT_ROOT"

for bundle in "${BUNDLES[@]}"; do
  bundle_out="$OUT_ROOT/$bundle"
  mkdir -p "$bundle_out"
  printf 'replaying_bundle=%s\nout_root=%s\n' "$bundle" "$bundle_out"
  bash "examples/proof-bundles/$bundle/replay.sh" "$bundle_out"
  printf 'replay_ok=%s\n' "$bundle"
  echo
done

printf 'replay_all_complete\nout_root=%s\n' "$OUT_ROOT"
