from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from _runtime_lib import validate_phase_transition_semantics  # noqa: E402


class PhaseTransitionSemanticsTests(unittest.TestCase):
    def test_advance_forward_transition_is_valid(self) -> None:
        errors = validate_phase_transition_semantics(
            previous_state={
                "phase": "EXPLORE",
                "status": "ACTIVE",
                "back_transitions_remaining": 1,
            },
            state_patch={"phase": "EVALUATE", "status": "ACTIVE"},
            result_type="ADVANCE",
        )
        self.assertEqual(errors, [])

    def test_fail_retry_stays_same_phase(self) -> None:
        errors = validate_phase_transition_semantics(
            previous_state={
                "phase": "SYNTHESIZE",
                "status": "ACTIVE",
                "back_transitions_remaining": 1,
            },
            state_patch={"phase": "SYNTHESIZE", "status": "BLOCKED"},
            result_type="FAIL",
        )
        self.assertEqual(errors, [])

    def test_back_transition_requires_budget_decrement(self) -> None:
        errors = validate_phase_transition_semantics(
            previous_state={
                "phase": "EVALUATE",
                "status": "ACTIVE",
                "back_transitions_remaining": 1,
            },
            state_patch={"phase": "EXPLORE", "status": "ACTIVE"},
            result_type="ADVANCE",
        )
        self.assertTrue(any("back_transitions_remaining decrement" in error for error in errors))

    def test_block_requires_blocked_status(self) -> None:
        errors = validate_phase_transition_semantics(
            previous_state={
                "phase": "EXPLORE",
                "status": "ACTIVE",
                "back_transitions_remaining": 1,
            },
            state_patch={"phase": "EXPLORE", "status": "ACTIVE"},
            result_type="BLOCK",
        )
        self.assertTrue(any("BLOCK results must set state_patch.status=BLOCKED" in error for error in errors))

    def test_fail_cannot_forward_except_closed(self) -> None:
        errors = validate_phase_transition_semantics(
            previous_state={
                "phase": "EXPLORE",
                "status": "ACTIVE",
                "back_transitions_remaining": 1,
            },
            state_patch={"phase": "EVALUATE", "status": "BLOCKED"},
            result_type="FAIL",
        )
        self.assertTrue(any("may only forward-transition to CLOSED" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
