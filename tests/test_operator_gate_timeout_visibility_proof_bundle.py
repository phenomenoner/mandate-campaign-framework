from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = (
    PROJECT_ROOT
    / "examples"
    / "proof-bundles"
    / "steamer-operator-gate-timeout-visibility-seeded-v1"
)
MANIFEST_PATH = BUNDLE_ROOT / "MANIFEST.json"


class OperatorGateTimeoutVisibilityProofBundleTests(unittest.TestCase):
    def test_manifest_and_required_proof_pointers_exist(self) -> None:
        self.assertTrue(MANIFEST_PATH.exists(), f"missing manifest: {MANIFEST_PATH}")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(manifest["bundle_id"], "steamer-operator-gate-timeout-visibility-seeded-v1")

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

    def test_bundle_captures_operator_gate_stale_timeout_visibility(self) -> None:
        advance_payload = json.loads(
            (BUNDLE_ROOT / "outputs/advance/001_gate_to_operator_gate_escalate.json").read_text(
                encoding="utf-8"
            )
        )
        inspect_payload = json.loads(
            (BUNDLE_ROOT / "outputs/inspect_operator_gate_stale.json").read_text(encoding="utf-8")
        )
        inspect_text = (BUNDLE_ROOT / "outputs/inspect_operator_gate_stale.txt").read_text(
            encoding="utf-8"
        )

        self.assertEqual(advance_payload["phase_before"], "GATE")
        self.assertEqual(advance_payload["phase_after"], "GATE")
        self.assertEqual(advance_payload["status_after"], "OPERATOR_GATE")
        self.assertEqual(advance_payload["result_type"], "ESCALATE")
        self.assertEqual(advance_payload["wakeup"]["reason"], "steamer_shadow_review_gate")

        gate_visibility = inspect_payload["operator_gate_visibility"]
        self.assertTrue(gate_visibility["blocked"])
        self.assertTrue(gate_visibility["stale"])
        self.assertEqual(gate_visibility["signal"], "operator_gate_timeout_exceeded")
        self.assertEqual(gate_visibility["timeout_days"], 3)
        self.assertGreater(gate_visibility["overdue_seconds"], 0)
        self.assertEqual(inspect_payload["blocked_cause"]["code"], "operator_gate_timeout")
        self.assertEqual(inspect_payload["resume_hint"]["action"], "operator_decision_needed")

        self.assertIn("operator_gate: blocked=True", inspect_text)
        self.assertIn("signal=operator_gate_timeout_exceeded", inspect_text)
        self.assertIn("blocked_cause: code=operator_gate_timeout", inspect_text)
        self.assertIn("resume_hint: action=operator_decision_needed", inspect_text)


if __name__ == "__main__":
    unittest.main()
