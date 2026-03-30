from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = (
    PROJECT_ROOT / "examples" / "proof-bundles" / "steamer-resume-recovery-seeded-v1"
)
MANIFEST_PATH = BUNDLE_ROOT / "MANIFEST.json"


class ResumeRecoveryProofBundleTests(unittest.TestCase):
    def test_manifest_and_required_proof_pointers_exist(self) -> None:
        self.assertTrue(MANIFEST_PATH.exists(), f"missing manifest: {MANIFEST_PATH}")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(manifest["bundle_id"], "steamer-resume-recovery-seeded-v1")

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

    def test_bundle_captures_blocked_explore_resume_recovery_flow(self) -> None:
        blocked_step = json.loads(
            (BUNDLE_ROOT / "outputs/advance/001_explore_to_blocked_no_candidate.json").read_text(
                encoding="utf-8"
            )
        )
        blocked_inspect = json.loads(
            (BUNDLE_ROOT / "outputs/inspect_blocked.json").read_text(encoding="utf-8")
        )
        resume_step = json.loads(
            (BUNDLE_ROOT / "outputs/advance/002_blocked_resume_to_evaluate.json").read_text(
                encoding="utf-8"
            )
        )
        post_resume_inspect = json.loads(
            (BUNDLE_ROOT / "outputs/inspect_post_resume.json").read_text(encoding="utf-8")
        )

        self.assertEqual(blocked_step["phase_before"], "EXPLORE")
        self.assertEqual(blocked_step["status_after"], "BLOCKED")
        self.assertFalse(blocked_step["resume_requested"])
        self.assertEqual(blocked_step["receipt_id"], "001_steamer_no_candidate_available")
        self.assertEqual(blocked_step["wakeup"]["reason"], "steamer_no_candidate_available")
        self.assertEqual(blocked_step["acted_item_reason"], "queue_empty")

        self.assertEqual(blocked_inspect["state"]["phase"], "EXPLORE")
        self.assertEqual(blocked_inspect["state"]["status"], "BLOCKED")
        self.assertEqual(
            blocked_inspect["state"]["wakeup"]["reason"],
            "steamer_no_candidate_available",
        )
        self.assertEqual(blocked_inspect["blocked_cause"]["code"], "queue_empty")
        self.assertTrue(blocked_inspect["blocked_cause"]["resume_supported"])
        self.assertEqual(blocked_inspect["resume_hint"]["action"], "run_resume")
        self.assertIn("--resume", blocked_inspect["resume_hint"]["command"])

        self.assertEqual(resume_step["status_before"], "BLOCKED")
        self.assertEqual(resume_step["phase_after"], "EVALUATE")
        self.assertEqual(resume_step["status_after"], "ACTIVE")
        self.assertTrue(resume_step["resume_requested"])
        self.assertTrue(resume_step["resume_applied"])
        self.assertEqual(resume_step["receipt_id"], "002_steamer_resume_retry_idea_scout")
        self.assertEqual(resume_step["acted_item_reason"], "resume_reseeded_queue_head")

        self.assertEqual(post_resume_inspect["state"]["phase"], "EVALUATE")
        self.assertEqual(post_resume_inspect["state"]["status"], "ACTIVE")
        self.assertEqual(post_resume_inspect["drift"]["status"], "clean")

        blocked_receipt = json.loads(
            (
                BUNDLE_ROOT
                / "run/2026-03-tw-vcp-shadow-candidate/receipts/001_steamer_no_candidate_available.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(blocked_receipt["event"], "steamer_no_candidate_available")

        resume_receipt = json.loads(
            (
                BUNDLE_ROOT
                / "run/2026-03-tw-vcp-shadow-candidate/receipts/002_steamer_resume_retry_idea_scout.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(resume_receipt["event"], "steamer_resume_retry_idea_scout")
        self.assertIn("reason=steamer_no_candidate_available", resume_receipt["summary"])

        idea_scout_note = (
            BUNDLE_ROOT
            / "run/2026-03-tw-vcp-shadow-candidate/artifacts/steamer/idea-scout/tw-vcp-breakout-open-auction.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Steamer idea-scout note", idea_scout_note)



if __name__ == "__main__":
    unittest.main()
