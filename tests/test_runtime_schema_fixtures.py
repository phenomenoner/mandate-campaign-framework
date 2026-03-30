from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from _runtime_lib import (  # noqa: E402
    validate_campaign_state,
    validate_receipt_record,
    validate_worker_state_patch,
)


def _valid_campaign_state() -> dict:
    return {
        "campaign_id": "2026-03-example",
        "mandate_id": "2026-03-example",
        "adapter": "steamer",
        "phase": "EXPLORE",
        "status": "ACTIVE",
        "active_item_id": None,
        "item_queue": ["item-001"],
        "cycle_budget": 8,
        "back_transitions_remaining": 1,
        "wakeup": {"needed": False, "reason": None},
        "last_receipt": {
            "path": "receipts/001_phase_advanced_intake_to_explore.json",
            "summary": "advanced campaign one bounded step: INTAKE -> EXPLORE",
        },
        "updated_at": "2026-03-13T16:50:00+08:00",
    }


def _valid_worker_state_patch() -> dict:
    return {
        "phase": "EVALUATE",
        "status": "ACTIVE",
        "active_item_id": "item-002",
        "item_queue": ["item-002", "item-003"],
        "cycle_budget": 7,
        "back_transitions_remaining": 1,
        "wakeup": {"needed": False, "reason": None},
        "last_receipt": {
            "path": "receipts/002_phase_advanced_explore_to_evaluate.json",
            "summary": "advanced campaign one bounded step: EXPLORE -> EVALUATE",
        },
    }


def _valid_receipt_record() -> dict:
    return {
        "receipt_id": "002_phase_advanced_explore_to_evaluate",
        "campaign_id": "2026-03-example",
        "mandate_id": "2026-03-example",
        "phase": "EVALUATE",
        "event": "phase_advanced_explore_to_evaluate",
        "summary": "advanced campaign one bounded step: EXPLORE -> EVALUATE",
        "artifact_refs": ["CAMPAIGN_STATE.json"],
        "work_item": {
            "id": "item-002",
            "selection_reason": "item_queue_head",
            "decision": "idea_scout_completed",
            "queue_before_len": 2,
            "queue_after_len": 2,
        },
        "created_at": "2026-03-13T16:52:00+08:00",
    }


class RuntimeSchemaFixtureTests(unittest.TestCase):
    def test_campaign_state_valid_fixture(self) -> None:
        errors = validate_campaign_state(_valid_campaign_state())
        self.assertEqual(errors, [])

    def test_campaign_state_invalid_fixture(self) -> None:
        payload = deepcopy(_valid_campaign_state())
        payload["phase"] = "BROKEN"
        payload["adapter"] = "bad adapter id"
        payload["cycle_budget"] = -1
        payload["wakeup"] = "now"
        payload["updated_at"] = "not-an-iso-datetime"

        errors = validate_campaign_state(payload)

        self.assertTrue(any("campaign_state.phase" in error for error in errors))
        self.assertTrue(any("campaign_state.adapter" in error for error in errors))
        self.assertTrue(any("campaign_state.cycle_budget" in error for error in errors))
        self.assertTrue(any("campaign_state.wakeup" in error for error in errors))
        self.assertTrue(any("campaign_state.updated_at" in error for error in errors))

    def test_worker_state_patch_valid_fixture(self) -> None:
        errors = validate_worker_state_patch(_valid_worker_state_patch())
        self.assertEqual(errors, [])

    def test_worker_state_patch_invalid_fixture(self) -> None:
        payload = deepcopy(_valid_worker_state_patch())
        payload["phase"] = "UNKNOWN"
        payload["cycle_budget"] = -9
        payload["unknown_field"] = "should-not-pass"
        payload["wakeup"] = {"needed": "yes", "reason": 123}

        errors = validate_worker_state_patch(payload)

        self.assertTrue(any("disallowed keys" in error for error in errors))
        self.assertTrue(any("state_patch.phase" in error for error in errors))
        self.assertTrue(any("state_patch.cycle_budget" in error for error in errors))
        self.assertTrue(any("state_patch.wakeup.needed" in error for error in errors))
        self.assertTrue(any("state_patch.wakeup.reason" in error for error in errors))

    def test_receipt_record_valid_fixture(self) -> None:
        errors = validate_receipt_record(
            _valid_receipt_record(),
            expected_campaign_id="2026-03-example",
            expected_mandate_id="2026-03-example",
        )
        self.assertEqual(errors, [])

    def test_receipt_record_invalid_fixture(self) -> None:
        payload = deepcopy(_valid_receipt_record())
        payload["artifact_refs"] = ["CAMPAIGN_STATE.json", ""]
        payload["created_at"] = "bad-time"
        payload["campaign_id"] = "wrong-campaign"
        payload["work_item"]["decision"] = ""
        payload["work_item"]["queue_before_len"] = -1

        errors = validate_receipt_record(
            payload,
            expected_campaign_id="2026-03-example",
            expected_mandate_id="2026-03-example",
        )

        self.assertTrue(any("artifact_refs" in error for error in errors))
        self.assertTrue(any("created_at" in error for error in errors))
        self.assertTrue(any("campaign_id mismatch" in error for error in errors))
        self.assertTrue(any("receipt.work_item.decision" in error for error in errors))
        self.assertTrue(any("receipt.work_item.queue_before_len" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
