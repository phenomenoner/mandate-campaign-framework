from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROOF_BUNDLES_ROOT = PROJECT_ROOT / "examples" / "proof-bundles"
INDEX_PATH = PROOF_BUNDLES_ROOT / "INDEX.json"
PROOF_INDEX_DOC = PROOF_BUNDLES_ROOT / "PROOF_INDEX.md"
REPLAY_ALL_PATH = PROOF_BUNDLES_ROOT / "replay-all.sh"


class ProofIndexManifestTests(unittest.TestCase):
    def test_index_tracks_six_canonical_bundles_and_live_paths(self) -> None:
        self.assertTrue(INDEX_PATH.exists(), f"missing proof index manifest: {INDEX_PATH}")

        index_payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        bundles = index_payload["bundles"]

        expected_ids = [
            "steamer-shadow-proof-seeded-v1",
            "steamer-resume-recovery-seeded-v1",
            "steamer-resume-evaluate-recovery-seeded-v1",
            "steamer-cycle-budget-exhaustion-seeded-v1",
            "steamer-operator-gate-timeout-visibility-seeded-v1",
            "steamer-operator-gate-reject-replay-seeded-v1",
        ]
        self.assertEqual([entry["bundle_id"] for entry in bundles], expected_ids)

        for entry in bundles:
            for key in ("bundle_path", "readme_path", "manifest_path", "replay_script"):
                rel_path = entry[key]
                abs_path = PROJECT_ROOT / rel_path
                self.assertTrue(abs_path.exists(), f"missing index pointer ({entry['bundle_id']}:{key}): {abs_path}")

            replay_script = PROJECT_ROOT / entry["replay_script"]
            self.assertTrue(
                os.access(replay_script, os.X_OK),
                f"replay script not executable: {replay_script}",
            )

            bundle_manifest = json.loads((PROJECT_ROOT / entry["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(bundle_manifest["bundle_id"], entry["bundle_id"])

    def test_operator_entrypoints_exist(self) -> None:
        self.assertTrue(PROOF_INDEX_DOC.exists(), f"missing proof index doc: {PROOF_INDEX_DOC}")
        self.assertTrue(REPLAY_ALL_PATH.exists(), f"missing replay-all helper: {REPLAY_ALL_PATH}")
        self.assertTrue(os.access(REPLAY_ALL_PATH, os.X_OK), f"replay-all not executable: {REPLAY_ALL_PATH}")

        proof_index_text = PROOF_INDEX_DOC.read_text(encoding="utf-8")
        self.assertIn("steamer-shadow-proof-seeded-v1", proof_index_text)
        self.assertIn("steamer-resume-recovery-seeded-v1", proof_index_text)
        self.assertIn("steamer-resume-evaluate-recovery-seeded-v1", proof_index_text)
        self.assertIn("steamer-cycle-budget-exhaustion-seeded-v1", proof_index_text)
        self.assertIn("steamer-operator-gate-timeout-visibility-seeded-v1", proof_index_text)
        self.assertIn("steamer-operator-gate-reject-replay-seeded-v1", proof_index_text)
        self.assertIn("replay-all.sh", proof_index_text)


if __name__ == "__main__":
    unittest.main()
