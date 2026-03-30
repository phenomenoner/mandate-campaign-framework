from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from _adapter_runtime import resolve_runtime_adapter  # noqa: E402
from _runtime_lib import resolve_campaign_adapter_identity  # noqa: E402


class AdapterRuntimeTests(unittest.TestCase):
    def test_resolve_campaign_adapter_identity_prefers_state(self) -> None:
        identity = resolve_campaign_adapter_identity(
            campaign_state={"adapter": "steamer"},
            mandate={"adapter": "steamer"},
        )
        self.assertEqual(identity.adapter_id, "steamer")
        self.assertEqual(identity.source, "campaign_state.adapter")

    def test_resolve_campaign_adapter_identity_falls_back_to_mandate(self) -> None:
        identity = resolve_campaign_adapter_identity(
            campaign_state={},
            mandate={"adapter": "content-production"},
        )
        self.assertEqual(identity.adapter_id, "content-production")
        self.assertEqual(identity.source, "mandate.adapter")

    def test_resolve_campaign_adapter_identity_rejects_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            resolve_campaign_adapter_identity(
                campaign_state={"adapter": "steamer"},
                mandate={"adapter": "content-production"},
            )

    def test_runtime_adapter_registry_contains_steamer(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        self.assertEqual(adapter.adapter_id, "steamer")
        self.assertTrue(callable(adapter.worker))

    def test_runtime_adapter_registry_contains_openclaw_mem(self) -> None:
        adapter = resolve_runtime_adapter("openclaw-mem")
        self.assertEqual(adapter.adapter_id, "openclaw-mem")
        self.assertTrue(callable(adapter.worker))

    def test_runtime_adapter_unknown_requires_explicit_stub_fallback(self) -> None:
        with self.assertRaises(Exception):
            resolve_runtime_adapter("unknown-adapter")

        fallback = resolve_runtime_adapter("unknown-adapter", allow_stub_fallback=True)
        self.assertEqual(fallback.adapter_id, "stub")

    def _openclaw_mem_context(
        self,
        *,
        phase: str,
        cycle_budget: int = 8,
        active_item_id: str | None = None,
        item_queue: list[str] | None = None,
        status: str = "ACTIVE",
    ) -> dict:
        source_pointer = str((Path(__file__).resolve().parents[1] / "STATUS.md").resolve())
        return {
            "mandate": {
                "mandate_id": "SL-M1-UNITTEST-01",
                "adapter": "openclaw-mem",
                "objective": "package one bounded dev-decision packet",
                "scope": {"in": [source_pointer], "out": []},
                "constraints": {
                    "max_cluster_items": 20,
                    "max_root_cause_candidates": 3,
                    "cycle_budget": 6,
                    "mandate_timebox_minutes": 60,
                },
                "work_items": [
                    {"status_pointer": source_pointer},
                ],
            },
            "campaign_state": {
                "campaign_id": "SL-M1-UNITTEST-01",
                "mandate_id": "SL-M1-UNITTEST-01",
                "adapter": "openclaw-mem",
                "phase": phase,
                "status": status,
                "active_item_id": active_item_id,
                "item_queue": item_queue or [],
                "cycle_budget": cycle_budget,
                "back_transitions_remaining": 1,
                "wakeup": {"needed": False, "reason": None},
                "last_receipt": {
                    "path": "receipts/000_campaign_created.json",
                    "summary": "campaign initialized",
                },
                "updated_at": "2026-03-13T16:50:00+08:00",
            },
            "resume_requested": False,
            "replay_decision": None,
            "replay_note": None,
        }

    def test_openclaw_mem_intake_materializes_signal_inventory(self) -> None:
        adapter = resolve_runtime_adapter("openclaw-mem")
        result = adapter.worker(self._openclaw_mem_context(phase="INTAKE"), receipt_index=1)

        self.assertEqual(result["result_type"], "ADVANCE")
        self.assertEqual(result["state_patch"]["phase"], "EXPLORE")
        self.assertTrue(result["state_patch"]["item_queue"])
        self.assertTrue(
            any(item["path"] == "artifacts/openclaw-mem/mandate-intake.json" for item in result["artifact_materializations"])
        )

    def test_openclaw_mem_deliver_materializes_dev_decision_packet(self) -> None:
        adapter = resolve_runtime_adapter("openclaw-mem")
        result = adapter.worker(
            self._openclaw_mem_context(
                phase="DELIVER",
                active_item_id="m1-cluster-01",
                item_queue=["m1-cluster-01"],
            ),
            receipt_index=6,
        )

        self.assertEqual(result["state_patch"]["phase"], "CLOSED")
        self.assertEqual(result["state_patch"]["status"], "CLOSED")
        self.assertTrue(
            any(item["path"] == "artifacts/openclaw-mem/dev-decision-packet.json" for item in result["artifact_materializations"])
        )
        packet_quality = next(
            item["payload"]
            for item in result["artifact_materializations"]
            if item["path"] == "artifacts/openclaw-mem/packet-quality-assessment.json"
        )
        self.assertGreaterEqual(packet_quality["packet_depth_score"], 0)

    def _steamer_context(
        self,
        *,
        phase: str,
        cycle_budget: int = 8,
        active_item_id: str | None = None,
        item_queue: list[str] | None = None,
        back_transitions_remaining: int = 1,
        status: str = "ACTIVE",
        wakeup_needed: bool = False,
        wakeup_reason: str | None = None,
        resume_requested: bool = False,
        replay_decision: str | None = None,
        replay_note: str | None = None,
    ) -> dict:
        return {
            "mandate": {
                "mandate_id": "2026-03-steamer-test",
                "adapter": "steamer",
                "objective": "prepare one candidate for shadow review",
            },
            "campaign_state": {
                "campaign_id": "2026-03-steamer-test",
                "mandate_id": "2026-03-steamer-test",
                "adapter": "steamer",
                "phase": phase,
                "status": status,
                "active_item_id": active_item_id,
                "item_queue": item_queue or [],
                "cycle_budget": cycle_budget,
                "back_transitions_remaining": back_transitions_remaining,
                "wakeup": {"needed": wakeup_needed, "reason": wakeup_reason},
                "last_receipt": {
                    "path": "receipts/000_campaign_created.json",
                    "summary": "campaign initialized",
                },
                "updated_at": "2026-03-13T16:50:00+08:00",
            },
            "resume_requested": resume_requested,
            "replay_decision": replay_decision,
            "replay_note": replay_note,
        }

    def test_steamer_intake_seeds_queue_and_advances(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(self._steamer_context(phase="INTAKE"), receipt_index=1)

        self.assertEqual(result["result_type"], "ADVANCE")
        self.assertEqual(result["state_patch"]["phase"], "EXPLORE")
        self.assertTrue(result["state_patch"]["item_queue"])
        self.assertIsNotNone(result["state_patch"]["active_item_id"])
        self.assertTrue(
            any("artifacts/steamer/mandate-intake.json" in ref for ref in result["artifact_refs"])
        )
        self.assertEqual(result["receipt"]["work_item"]["decision"], "seed_candidates_for_idea_scout")
        self.assertTrue(
            any(item["path"] == "artifacts/steamer/candidate-queue.json" for item in result["artifact_materializations"])
        )

    def test_steamer_explore_materializes_idea_scout_note(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(
                phase="EXPLORE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a", "tw-vcp-b"],
            ),
            receipt_index=2,
        )

        self.assertEqual(result["result_type"], "ADVANCE")
        self.assertEqual(result["state_patch"]["phase"], "EVALUATE")
        note = next(
            item
            for item in result["artifact_materializations"]
            if item["path"] == "artifacts/steamer/idea-scout/tw-vcp-a.md"
        )
        self.assertEqual(note["format"], "text")
        self.assertIn("Steamer idea-scout note", note["content"])
        self.assertIn(note["path"], result["artifact_refs"])

    def test_steamer_explore_blocks_when_candidate_is_missing(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(phase="EXPLORE", active_item_id=None, item_queue=[]),
            receipt_index=2,
        )

        self.assertEqual(result["result_type"], "BLOCK")
        self.assertEqual(result["state_patch"]["status"], "BLOCKED")
        self.assertEqual(result["state_patch"]["wakeup"]["reason"], "steamer_no_candidate_available")
        self.assertEqual(result["receipt"]["work_item"]["decision"], "blocked_no_candidate_available")
        self.assertTrue(
            any("shadow-proof" in item["path"] for item in result["artifact_materializations"])
        )

    def test_steamer_blocks_when_cycle_budget_exhausted(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(
                phase="EXPLORE",
                cycle_budget=0,
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a", "tw-vcp-b"],
            ),
            receipt_index=2,
        )

        self.assertEqual(result["result_type"], "BLOCK")
        self.assertEqual(result["receipt"]["event"], "cycle_budget_exhausted")
        self.assertEqual(result["state_patch"]["status"], "BLOCKED")
        self.assertEqual(result["state_patch"]["wakeup"]["reason"], "cycle_budget_exhausted")

    def test_steamer_resume_retry_reseeds_blocked_explore(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(
                phase="EXPLORE",
                status="BLOCKED",
                active_item_id=None,
                item_queue=[],
                wakeup_needed=True,
                wakeup_reason="steamer_no_candidate_available",
                resume_requested=True,
            ),
            receipt_index=3,
        )

        self.assertEqual(result["result_type"], "ADVANCE")
        self.assertEqual(result["receipt"]["event"], "steamer_resume_retry_idea_scout")
        self.assertEqual(result["state_patch"]["phase"], "EVALUATE")
        self.assertEqual(result["state_patch"]["status"], "ACTIVE")
        self.assertTrue(result["state_patch"]["item_queue"])
        self.assertIn("retried idea-scout", result["receipt"]["summary"])
        self.assertEqual(result["receipt"]["work_item"]["selection_reason"], "resume_reseeded_queue_head")

    def test_steamer_resume_recover_blocked_evaluate_to_explore(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(
                phase="EVALUATE",
                status="BLOCKED",
                active_item_id=None,
                item_queue=[],
                wakeup_needed=True,
                wakeup_reason="steamer_no_candidate_available",
                resume_requested=True,
                back_transitions_remaining=1,
            ),
            receipt_index=4,
        )

        self.assertEqual(result["result_type"], "ADVANCE")
        self.assertEqual(result["receipt"]["event"], "steamer_resume_recover_evaluate_to_explore")
        self.assertEqual(result["state_patch"]["phase"], "EXPLORE")
        self.assertEqual(result["state_patch"]["status"], "ACTIVE")
        self.assertTrue(result["state_patch"]["item_queue"])
        self.assertIsNotNone(result["state_patch"]["active_item_id"])
        self.assertEqual(result["state_patch"]["back_transitions_remaining"], 0)
        self.assertEqual(
            result["receipt"]["work_item"]["decision"],
            "resume_recovered_evaluate_missing_candidate_context",
        )

    def test_steamer_resume_recover_blocked_evaluate_requires_back_budget(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(
                phase="EVALUATE",
                status="BLOCKED",
                active_item_id=None,
                item_queue=[],
                wakeup_needed=True,
                wakeup_reason="steamer_no_candidate_available",
                resume_requested=True,
                back_transitions_remaining=0,
            ),
            receipt_index=4,
        )

        self.assertEqual(result["result_type"], "BLOCK")
        self.assertEqual(result["receipt"]["event"], "steamer_no_candidate_available")
        self.assertEqual(result["state_patch"]["status"], "BLOCKED")

    def test_steamer_evaluate_can_request_back_transition(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(
                phase="EVALUATE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a", "tw-vcp-b"],
                back_transitions_remaining=1,
            ),
            receipt_index=3,
        )

        self.assertEqual(result["result_type"], "ADVANCE")
        self.assertEqual(result["state_patch"]["phase"], "EXPLORE")
        self.assertEqual(result["state_patch"]["active_item_id"], "tw-vcp-b")
        self.assertEqual(result["state_patch"]["back_transitions_remaining"], 0)
        self.assertEqual(result["receipt"]["work_item"]["next_item_id"], "tw-vcp-b")

    def test_steamer_synthesize_blocks_without_candidate_context(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(phase="SYNTHESIZE", active_item_id=None, item_queue=[]),
            receipt_index=4,
        )

        self.assertEqual(result["result_type"], "BLOCK")
        self.assertEqual(result["state_patch"]["status"], "BLOCKED")
        self.assertEqual(result["state_patch"]["wakeup"]["reason"], "steamer_no_candidate_available")

    def test_steamer_gate_phase_escalates_to_operator_gate(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(
                phase="GATE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
            ),
            receipt_index=5,
        )

        self.assertEqual(result["result_type"], "ESCALATE")
        self.assertEqual(result["state_patch"]["phase"], "GATE")
        self.assertEqual(result["state_patch"]["status"], "OPERATOR_GATE")
        self.assertTrue(result["state_patch"]["wakeup"]["needed"])
        self.assertEqual(result["state_patch"]["wakeup"]["reason"], "steamer_shadow_review_gate")
        self.assertEqual(result["state_patch"]["item_queue"], ["tw-vcp-a"])
        self.assertEqual(result["receipt"]["work_item"]["decision"], "operator_gate_shadow_review_required")

    def test_steamer_gate_operator_decision_replay_advances_to_deliver(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(
                phase="GATE",
                status="OPERATOR_GATE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_needed=True,
                wakeup_reason="steamer_shadow_review_gate",
                replay_decision="approve_shadow_review",
                replay_note="shadow evidence accepted",
            ),
            receipt_index=6,
        )

        self.assertEqual(result["result_type"], "ADVANCE")
        self.assertEqual(result["state_patch"]["phase"], "DELIVER")
        self.assertEqual(result["state_patch"]["status"], "ACTIVE")
        self.assertEqual(
            result["receipt"]["work_item"]["decision"],
            "operator_gate_replay_approved_shadow_review",
        )
        gate_replay = next(
            item
            for item in result["artifact_materializations"]
            if item["path"].startswith("artifacts/steamer/gate-replay/")
        )
        self.assertEqual(gate_replay["format"], "json")
        self.assertEqual(gate_replay["payload"]["operator_decision"], "approve_shadow_review")

    def test_steamer_gate_operator_decision_replay_rejects_to_closed(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        result = adapter.worker(
            self._steamer_context(
                phase="GATE",
                status="OPERATOR_GATE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_needed=True,
                wakeup_reason="steamer_shadow_review_gate",
                replay_decision="reject_shadow_review",
                replay_note="insufficient evidence",
            ),
            receipt_index=7,
        )

        self.assertEqual(result["result_type"], "ADVANCE")
        self.assertEqual(result["state_patch"]["phase"], "CLOSED")
        self.assertEqual(result["state_patch"]["status"], "CLOSED")
        self.assertEqual(
            result["receipt"]["work_item"]["decision"],
            "operator_gate_replay_rejected_shadow_review",
        )
        gate_replay = next(
            item
            for item in result["artifact_materializations"]
            if item["path"].startswith("artifacts/steamer/gate-replay/")
        )
        self.assertEqual(gate_replay["format"], "json")
        self.assertEqual(gate_replay["payload"]["operator_decision"], "reject_shadow_review")
        self.assertEqual(gate_replay["payload"]["phase_after"], "CLOSED")
        self.assertEqual(gate_replay["payload"]["status_after"], "CLOSED")

    def test_steamer_inspect_accepts_work_item_next_item_alignment(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        drift = adapter.inspect_hook(  # type: ignore[misc]
            {
                "phase": "EXPLORE",
                "status": "ACTIVE",
                "active_item_id": "tw-vcp-b",
                "item_queue": ["tw-vcp-b", "tw-vcp-c"],
                "cycle_budget": 5,
                "wakeup": {"needed": False, "reason": None},
            },
            {
                "last_receipt_payload": {
                    "phase": "EXPLORE",
                    "artifact_refs": [
                        "artifacts/steamer/replay/fast-triage-tw-vcp-a.json",
                        "artifacts/steamer/candidate-queue.json",
                    ],
                    "work_item": {
                        "id": "tw-vcp-a",
                        "next_item_id": "tw-vcp-b",
                        "queue_after_head": "tw-vcp-b",
                    },
                }
            },
        )

        self.assertIsNotNone(drift)
        self.assertEqual(drift["status"], "clean")

    def test_steamer_inspect_warns_when_work_item_context_disagrees_with_active_item(self) -> None:
        adapter = resolve_runtime_adapter("steamer")
        drift = adapter.inspect_hook(  # type: ignore[misc]
            {
                "phase": "EXPLORE",
                "status": "ACTIVE",
                "active_item_id": "tw-vcp-c",
                "item_queue": ["tw-vcp-c"],
                "cycle_budget": 5,
                "wakeup": {"needed": False, "reason": None},
            },
            {
                "last_receipt_payload": {
                    "phase": "EXPLORE",
                    "artifact_refs": [
                        "artifacts/steamer/replay/fast-triage-tw-vcp-a.json",
                        "artifacts/steamer/candidate-queue.json",
                    ],
                    "work_item": {
                        "id": "tw-vcp-a",
                        "next_item_id": "tw-vcp-b",
                        "queue_after_head": "tw-vcp-b",
                    },
                }
            },
        )

        self.assertIsNotNone(drift)
        self.assertEqual(drift["status"], "warning")
        codes = {item["code"] for item in drift["findings"]}
        self.assertIn("last_receipt_active_item_mismatch", codes)


if __name__ == "__main__":
    unittest.main()
