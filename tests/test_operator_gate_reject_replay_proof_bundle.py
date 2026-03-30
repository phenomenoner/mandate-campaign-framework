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
    / "steamer-operator-gate-reject-replay-seeded-v1"
)
MANIFEST_PATH = BUNDLE_ROOT / "MANIFEST.json"


class OperatorGateRejectReplayProofBundleTests(unittest.TestCase):
    def test_manifest_and_required_proof_pointers_exist(self) -> None:
        self.assertTrue(MANIFEST_PATH.exists(), f"missing manifest: {MANIFEST_PATH}")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(manifest["bundle_id"], "steamer-operator-gate-reject-replay-seeded-v1")

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

    def test_bundle_captures_negative_operator_gate_replay_with_pre_post_evidence(self) -> None:
        pre_replay_inspect = json.loads(
            (BUNDLE_ROOT / "outputs/inspect_pre_replay.json").read_text(encoding="utf-8")
        )
        pre_replay_state = json.loads(
            (BUNDLE_ROOT / "outputs/state_pre_replay.json").read_text(encoding="utf-8")
        )
        replay_payload = json.loads(
            (
                BUNDLE_ROOT
                / "outputs/advance/008_operator_gate_replay_reject_to_closed.json"
            ).read_text(encoding="utf-8")
        )
        post_replay_inspect = json.loads(
            (BUNDLE_ROOT / "outputs/inspect_post_replay.json").read_text(encoding="utf-8")
        )
        post_replay_state = json.loads(
            (BUNDLE_ROOT / "outputs/state_post_replay.json").read_text(encoding="utf-8")
        )

        self.assertEqual(pre_replay_inspect["state"]["phase"], "GATE")
        self.assertEqual(pre_replay_inspect["state"]["status"], "OPERATOR_GATE")
        self.assertEqual(pre_replay_state["phase"], "GATE")
        self.assertEqual(pre_replay_state["status"], "OPERATOR_GATE")

        self.assertEqual(replay_payload["status_before"], "OPERATOR_GATE")
        self.assertEqual(replay_payload["phase_after"], "CLOSED")
        self.assertEqual(replay_payload["status_after"], "CLOSED")
        self.assertEqual(replay_payload["replay_decision"], "reject_shadow_review")
        self.assertTrue(replay_payload["replay_applied"])

        self.assertEqual(post_replay_inspect["state"]["phase"], "CLOSED")
        self.assertEqual(post_replay_inspect["state"]["status"], "CLOSED")
        self.assertEqual(post_replay_inspect["drift"]["status"], "clean")
        self.assertEqual(post_replay_state["phase"], "CLOSED")
        self.assertEqual(post_replay_state["status"], "CLOSED")

        replay_receipt = json.loads(
            (
                BUNDLE_ROOT
                / "run/2026-03-tw-vcp-shadow-candidate/receipts/008_steamer_operator_gate_decision_replayed.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(replay_receipt["event"], "steamer_operator_gate_decision_replayed")
        self.assertEqual(replay_receipt["phase"], "CLOSED")
        self.assertEqual(replay_receipt["work_item"]["operator_decision"], "reject_shadow_review")
        self.assertEqual(
            replay_receipt["work_item"]["decision"],
            "operator_gate_replay_rejected_shadow_review",
        )

        replay_artifact = json.loads(
            (
                BUNDLE_ROOT
                / "run/2026-03-tw-vcp-shadow-candidate/artifacts/steamer/gate-replay/008_tw-vcp-late-reclaim-pullback_reject_shadow_review.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(replay_artifact["operator_decision"], "reject_shadow_review")
        self.assertEqual(replay_artifact["phase_after"], "CLOSED")
        self.assertEqual(replay_artifact["status_after"], "CLOSED")
        self.assertIn("seeded proof", replay_artifact["operator_note"])


if __name__ == "__main__":
    unittest.main()
