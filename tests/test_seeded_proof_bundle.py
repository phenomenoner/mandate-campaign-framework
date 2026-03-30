from __future__ import annotations

import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = PROJECT_ROOT / "examples" / "proof-bundles" / "steamer-shadow-proof-seeded-v1"
MANIFEST_PATH = BUNDLE_ROOT / "MANIFEST.json"


class SeededProofBundleTests(unittest.TestCase):
    def test_manifest_and_required_proof_pointers_exist(self) -> None:
        self.assertTrue(MANIFEST_PATH.exists(), f"missing manifest: {MANIFEST_PATH}")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(manifest["bundle_id"], "steamer-shadow-proof-seeded-v1")

        for rel_path in manifest["advance_outputs"]:
            path = BUNDLE_ROOT / rel_path
            self.assertTrue(path.exists(), f"missing advance output: {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(payload.get("ok"), f"advance output not ok: {path}")

        for key, rel_path in manifest["required_proof_pointers"].items():
            path = BUNDLE_ROOT / rel_path
            self.assertTrue(path.exists(), f"missing required pointer ({key}): {path}")

    def test_bundle_captures_operator_gate_replay_and_clean_inspect(self) -> None:
        step7 = json.loads(
            (BUNDLE_ROOT / "outputs/advance/007_gate_to_operator_gate_escalate.json").read_text(
                encoding="utf-8"
            )
        )
        step8 = json.loads(
            (BUNDLE_ROOT / "outputs/advance/008_operator_gate_replay_to_deliver.json").read_text(
                encoding="utf-8"
            )
        )
        inspect_payload = json.loads((BUNDLE_ROOT / "outputs/inspect.json").read_text(encoding="utf-8"))

        self.assertEqual(step7["status_after"], "OPERATOR_GATE")
        self.assertEqual(step8["phase_after"], "DELIVER")
        self.assertTrue(step8["replay_applied"])
        self.assertEqual(step8["replay_decision"], "approve_shadow_review")

        self.assertEqual(inspect_payload["state"]["phase"], "DELIVER")
        self.assertEqual(inspect_payload["state"]["status"], "ACTIVE")
        self.assertEqual(inspect_payload["drift"]["status"], "clean")

        gate_replay_path = (
            BUNDLE_ROOT
            / "run/2026-03-tw-vcp-shadow-candidate/artifacts/steamer/gate-replay/008_tw-vcp-late-reclaim-pullback_approve_shadow_review.json"
        )
        gate_replay = json.loads(gate_replay_path.read_text(encoding="utf-8"))
        self.assertEqual(gate_replay["operator_decision"], "approve_shadow_review")

        idea_scout_note = (
            BUNDLE_ROOT
            / "run/2026-03-tw-vcp-shadow-candidate/artifacts/steamer/idea-scout/tw-vcp-late-reclaim-pullback.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Steamer idea-scout note", idea_scout_note)


if __name__ == "__main__":
    unittest.main()
