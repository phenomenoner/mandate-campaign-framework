from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADVANCE_SCRIPT = PROJECT_ROOT / "tools" / "advance-campaign.py"
CAMPAIGN_ID = "2026-03-tw-vcp-shadow-candidate"


class AdvanceCampaignDispatchTests(unittest.TestCase):
    def _run_advance(self, *args: str) -> dict:
        cmd = [
            sys.executable,
            str(ADVANCE_SCRIPT),
            CAMPAIGN_ID,
            "--json",
            "--dry-run",
            *args,
        ]
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(f"command failed ({proc.returncode}): {proc.stderr}\n{proc.stdout}")
        return json.loads(proc.stdout)

    def test_default_dispatch_mode_uses_runtime_adapter(self) -> None:
        payload = self._run_advance()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["dispatch_mode"], "adapter")
        self.assertEqual(payload["adapter_id"], "steamer")
        self.assertEqual(payload["runtime_adapter"], "steamer")
        self.assertTrue(isinstance(payload.get("acted_item_id"), str))
        self.assertEqual(payload.get("acted_item_decision"), "seed_candidates_for_idea_scout")
        self.assertGreaterEqual(payload.get("queue_len_after", 0), 1)
        self.assertTrue(
            any(
                isinstance(path, str) and path.startswith("artifacts/steamer/shadow-proof/")
                for path in payload.get("materialized_artifacts", [])
            )
        )

    def test_stub_dispatch_mode_is_explicit_fallback(self) -> None:
        payload = self._run_advance("--dispatch-mode", "stub")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["dispatch_mode"], "stub")
        self.assertEqual(payload["adapter_id"], "steamer")
        self.assertEqual(payload["runtime_adapter"], "stub")


if __name__ == "__main__":
    unittest.main()
