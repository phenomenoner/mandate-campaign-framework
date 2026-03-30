from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = (
    PROJECT_ROOT / "examples" / "proof-bundles" / "steamer-cycle-budget-exhaustion-seeded-v1"
)
MANIFEST_PATH = BUNDLE_ROOT / "MANIFEST.json"


class CycleBudgetProofBundleTests(unittest.TestCase):
    def test_manifest_and_required_proof_pointers_exist(self) -> None:
        self.assertTrue(MANIFEST_PATH.exists(), f"missing manifest: {MANIFEST_PATH}")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(manifest["bundle_id"], "steamer-cycle-budget-exhaustion-seeded-v1")

        replay_path = BUNDLE_ROOT / "replay.sh"
        self.assertTrue(replay_path.exists(), f"missing replay script: {replay_path}")
        self.assertTrue(os.access(replay_path, os.X_OK), f"replay script not executable: {replay_path}")

        for rel_path in manifest["advance_outputs"]:
            path = BUNDLE_ROOT / rel_path
            self.assertTrue(path.exists(), f"missing advance output: {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(payload.get("ok"), f"advance output not ok: {path}")

        for key, rel_path in manifest["required_proof_pointers"].items():
            path = BUNDLE_ROOT / rel_path
            self.assertTrue(path.exists(), f"missing required pointer ({key}): {path}")

    def test_bundle_captures_budget_exhaustion_block_and_inspect_output(self) -> None:
        blocked_step = json.loads(
            (BUNDLE_ROOT / "outputs/advance/001_explore_to_blocked_cycle_budget.json").read_text(
                encoding="utf-8"
            )
        )
        blocked_inspect = json.loads(
            (BUNDLE_ROOT / "outputs/inspect_blocked.json").read_text(encoding="utf-8")
        )

        self.assertEqual(blocked_step["phase_before"], "EXPLORE")
        self.assertEqual(blocked_step["phase_after"], "EXPLORE")
        self.assertEqual(blocked_step["status_after"], "BLOCKED")
        self.assertEqual(blocked_step["result_type"], "BLOCK")
        self.assertEqual(blocked_step["receipt_id"], "001_cycle_budget_exhausted")
        self.assertEqual(blocked_step["wakeup"]["reason"], "cycle_budget_exhausted")

        self.assertEqual(blocked_inspect["state"]["phase"], "EXPLORE")
        self.assertEqual(blocked_inspect["state"]["status"], "BLOCKED")
        self.assertEqual(blocked_inspect["state"]["cycle_budget"], 0)
        self.assertEqual(
            blocked_inspect["state"]["wakeup"]["reason"],
            "cycle_budget_exhausted",
        )
        self.assertEqual(blocked_inspect["drift"]["status"], "clean")

        blocked_receipt = json.loads(
            (
                BUNDLE_ROOT
                / "run/2026-03-tw-vcp-shadow-candidate/receipts/001_cycle_budget_exhausted.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(blocked_receipt["event"], "cycle_budget_exhausted")
        self.assertIn("cycle budget exhausted", blocked_receipt["summary"])


if __name__ == "__main__":
    unittest.main()
