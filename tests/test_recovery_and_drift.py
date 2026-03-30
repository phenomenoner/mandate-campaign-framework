from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADVANCE_SCRIPT = PROJECT_ROOT / "tools" / "advance-campaign.py"
INSPECT_SCRIPT = PROJECT_ROOT / "tools" / "inspect-campaign.py"


class RecoveryAndDriftTests(unittest.TestCase):
    def _run_json(self, script: Path, campaign_dir: Path, *args: str) -> dict:
        cmd = [sys.executable, str(script), str(campaign_dir), "--json", *args]
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"command failed ({proc.returncode}):\nSTDERR:\n{proc.stderr}\nSTDOUT:\n{proc.stdout}"
            )
        return json.loads(proc.stdout)

    def _run_json_expect_fail(self, script: Path, campaign_dir: Path, *args: str) -> dict:
        cmd = [sys.executable, str(script), str(campaign_dir), "--json", *args]
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            raise AssertionError(f"expected failure but command succeeded: {proc.stdout}")

        raw = proc.stderr.strip() or proc.stdout.strip()
        if not raw:
            raise AssertionError("expected JSON error payload but command returned empty output")

        return json.loads(raw)

    def _write_campaign_fixture(
        self,
        root: Path,
        *,
        state_phase: str,
        state_status: str,
        active_item_id: str | None,
        item_queue: list[str],
        wakeup_reason: str | None,
        cycle_budget: int = 6,
        back_transitions_remaining: int = 1,
        receipt_event: str = "steamer_no_candidate_available",
        receipt_summary: str | None = None,
        mandate_control_lane_only: bool = False,
        mandate_control_scenario: str | None = None,
        receipt_created_at: str = "2026-03-13T16:55:00+08:00",
        state_updated_at: str = "2026-03-13T16:55:00+08:00",
    ) -> Path:
        campaign_dir = root / "fixture-campaign"
        receipts_dir = campaign_dir / "receipts"
        receipts_dir.mkdir(parents=True, exist_ok=True)

        constraints = {"paper_only": True}
        if mandate_control_lane_only:
            constraints["control_lane_only"] = True

        mandate_payload = {
            "mandate_id": "fixture-campaign",
            "adapter": "steamer",
            "objective": "produce one shadow-review candidate",
            "scope": {"in": ["TW equities"], "out": ["live capital changes"]},
            "constraints": constraints,
            "authority": {
                "autonomous": ["idea_scout"],
                "requires_gate": ["promotion_to_shadow_review"],
            },
            "escalation": {
                "gate_conditions": ["evidence_insufficient_for_promotion"],
                "operator_gate_timeout_days": 3,
            },
            "success_criteria": ["one candidate disposition"],
            "ttl_days": 14,
            "delivery_shape": "shadow-reviewable strategy packet",
            "work_items": ["tw-vcp-a", "tw-vcp-b"],
        }
        if isinstance(mandate_control_scenario, str):
            mandate_payload["control_scenario"] = mandate_control_scenario
        (campaign_dir / "MANDATE.yaml").write_text(
            json.dumps(mandate_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        receipt0 = {
            "receipt_id": "000_campaign_created",
            "campaign_id": "fixture-campaign",
            "mandate_id": "fixture-campaign",
            "phase": "INTAKE",
            "event": "campaign_created",
            "summary": "campaign initialized from validated mandate",
            "artifact_refs": ["MANDATE.yaml", "CAMPAIGN_STATE.json"],
            "created_at": "2026-03-13T16:50:00+08:00",
        }
        (receipts_dir / "000_campaign_created.json").write_text(
            json.dumps(receipt0, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if receipt_summary is None:
            if receipt_event == "cycle_budget_exhausted":
                receipt_summary = "campaign blocked: cycle budget exhausted (dispatch=adapter, adapter=steamer)"
            else:
                receipt_summary = "steamer worker blocked: no candidate available for bounded step"

        receipt_artifact_refs = ["CAMPAIGN_STATE.json"]
        if receipt_event == "steamer_no_candidate_available":
            receipt_artifact_refs.append("artifacts/steamer/idea-scout/queue-empty.json")

        receipt1 = {
            "receipt_id": "001_seeded_blocked_state",
            "campaign_id": "fixture-campaign",
            "mandate_id": "fixture-campaign",
            "phase": state_phase,
            "event": receipt_event,
            "summary": receipt_summary,
            "artifact_refs": receipt_artifact_refs,
            "created_at": receipt_created_at,
        }
        (receipts_dir / "001_seeded_blocked_state.json").write_text(
            json.dumps(receipt1, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        state_payload = {
            "campaign_id": "fixture-campaign",
            "mandate_id": "fixture-campaign",
            "adapter": "steamer",
            "phase": state_phase,
            "status": state_status,
            "active_item_id": active_item_id,
            "item_queue": item_queue,
            "cycle_budget": cycle_budget,
            "back_transitions_remaining": back_transitions_remaining,
            "wakeup": {"needed": wakeup_reason is not None, "reason": wakeup_reason},
            "last_receipt": {
                "path": "receipts/001_seeded_blocked_state.json",
                "summary": receipt1["summary"],
            },
            "updated_at": state_updated_at,
        }
        (campaign_dir / "CAMPAIGN_STATE.json").write_text(
            json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        return campaign_dir

    def test_resume_flag_retries_blocked_explore_without_manual_state_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EXPLORE",
                state_status="BLOCKED",
                active_item_id=None,
                item_queue=[],
                wakeup_reason="steamer_no_candidate_available",
            )

            payload = self._run_json(ADVANCE_SCRIPT, campaign_dir, "--resume")
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["changed"])
            self.assertTrue(payload["resume_requested"])
            self.assertTrue(payload["resume_applied"])
            self.assertEqual(payload["phase_before"], "EXPLORE")
            self.assertEqual(payload["phase_after"], "EVALUATE")
            self.assertEqual(payload["status_after"], "ACTIVE")

            new_state = json.loads((campaign_dir / "CAMPAIGN_STATE.json").read_text(encoding="utf-8"))
            self.assertEqual(new_state["status"], "ACTIVE")
            self.assertEqual(new_state["phase"], "EVALUATE")
            self.assertTrue(new_state["item_queue"])
            self.assertTrue(isinstance(new_state["active_item_id"], str))

            receipt_path = campaign_dir / new_state["last_receipt"]["path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["event"], "steamer_resume_retry_idea_scout")
            self.assertIn("recovered", receipt["summary"])
            self.assertIn("retried", receipt["summary"])

            queue_artifact = campaign_dir / "artifacts/steamer/candidate-queue.json"
            self.assertTrue(queue_artifact.exists())
            queue_payload = json.loads(queue_artifact.read_text(encoding="utf-8"))
            self.assertEqual(queue_payload["active_item_id"], new_state["active_item_id"])
            self.assertTrue(queue_payload["item_queue"])

            trace_refs = [
                ref
                for ref in receipt["artifact_refs"]
                if isinstance(ref, str) and ref.startswith("artifacts/steamer/shadow-proof/")
            ]
            self.assertTrue(trace_refs)
            self.assertTrue((campaign_dir / trace_refs[0]).exists())

            idea_scout_note = campaign_dir / f"artifacts/steamer/idea-scout/{new_state['active_item_id']}.md"
            self.assertTrue(idea_scout_note.exists())
            note_text = idea_scout_note.read_text(encoding="utf-8")
            self.assertIn("Steamer idea-scout note", note_text)

    def test_resume_flag_recovers_blocked_evaluate_to_explore_without_manual_state_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EVALUATE",
                state_status="BLOCKED",
                active_item_id=None,
                item_queue=[],
                wakeup_reason="steamer_no_candidate_available",
                back_transitions_remaining=1,
            )

            payload = self._run_json(ADVANCE_SCRIPT, campaign_dir, "--resume")
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["changed"])
            self.assertTrue(payload["resume_requested"])
            self.assertTrue(payload["resume_applied"])
            self.assertEqual(payload["phase_before"], "EVALUATE")
            self.assertEqual(payload["phase_after"], "EXPLORE")
            self.assertEqual(payload["status_after"], "ACTIVE")

            new_state = json.loads((campaign_dir / "CAMPAIGN_STATE.json").read_text(encoding="utf-8"))
            self.assertEqual(new_state["status"], "ACTIVE")
            self.assertEqual(new_state["phase"], "EXPLORE")
            self.assertEqual(new_state["back_transitions_remaining"], 0)
            self.assertTrue(new_state["item_queue"])
            self.assertTrue(isinstance(new_state["active_item_id"], str))

            inspect_payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(inspect_payload["ok"])
            self.assertEqual(inspect_payload["drift"]["status"], "clean")

            receipt_path = campaign_dir / new_state["last_receipt"]["path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["event"], "steamer_resume_recover_evaluate_to_explore")
            self.assertIn("back-shifted to EXPLORE", receipt["summary"])

            queue_artifact = campaign_dir / "artifacts/steamer/candidate-queue.json"
            self.assertTrue(queue_artifact.exists())
            queue_payload = json.loads(queue_artifact.read_text(encoding="utf-8"))
            self.assertEqual(queue_payload["active_item_id"], new_state["active_item_id"])
            self.assertTrue(queue_payload["item_queue"])

            trace_refs = [
                ref
                for ref in receipt["artifact_refs"]
                if isinstance(ref, str) and ref.startswith("artifacts/steamer/shadow-proof/")
            ]
            self.assertTrue(trace_refs)
            self.assertTrue((campaign_dir / trace_refs[0]).exists())

    def test_operator_gate_replay_decision_creates_receiptable_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="GATE",
                state_status="OPERATOR_GATE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_reason="steamer_shadow_review_gate",
            )

            payload = self._run_json(
                ADVANCE_SCRIPT,
                campaign_dir,
                "--replay-decision",
                "approve_shadow_review",
                "--replay-note",
                "shadow evidence accepted",
            )
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["changed"])
            self.assertEqual(payload["phase_before"], "GATE")
            self.assertEqual(payload["phase_after"], "DELIVER")
            self.assertEqual(payload["status_before"], "OPERATOR_GATE")
            self.assertEqual(payload["status_after"], "ACTIVE")
            self.assertEqual(payload["replay_decision"], "approve_shadow_review")
            self.assertTrue(payload["replay_applied"])

            new_state = json.loads((campaign_dir / "CAMPAIGN_STATE.json").read_text(encoding="utf-8"))
            self.assertEqual(new_state["phase"], "DELIVER")
            self.assertEqual(new_state["status"], "ACTIVE")

            receipt_path = campaign_dir / new_state["last_receipt"]["path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["event"], "steamer_operator_gate_decision_replayed")
            self.assertEqual(
                receipt["work_item"]["decision"],
                "operator_gate_replay_approved_shadow_review",
            )

            gate_replay_refs = [
                ref
                for ref in receipt["artifact_refs"]
                if isinstance(ref, str) and ref.startswith("artifacts/steamer/gate-replay/")
            ]
            self.assertTrue(gate_replay_refs)
            gate_replay_payload = json.loads((campaign_dir / gate_replay_refs[0]).read_text(encoding="utf-8"))
            self.assertEqual(gate_replay_payload["operator_decision"], "approve_shadow_review")
            self.assertEqual(gate_replay_payload["phase_after"], "DELIVER")
            self.assertEqual(gate_replay_payload["operator_note"], "shadow evidence accepted")

    def test_operator_gate_replay_reject_decision_closes_campaign_with_receipt_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="GATE",
                state_status="OPERATOR_GATE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_reason="steamer_shadow_review_gate",
            )

            payload = self._run_json(
                ADVANCE_SCRIPT,
                campaign_dir,
                "--replay-decision",
                "reject_shadow_review",
                "--replay-note",
                "risk posture not acceptable",
            )
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["changed"])
            self.assertEqual(payload["phase_before"], "GATE")
            self.assertEqual(payload["phase_after"], "CLOSED")
            self.assertEqual(payload["status_before"], "OPERATOR_GATE")
            self.assertEqual(payload["status_after"], "CLOSED")
            self.assertEqual(payload["replay_decision"], "reject_shadow_review")
            self.assertTrue(payload["replay_applied"])

            new_state = json.loads((campaign_dir / "CAMPAIGN_STATE.json").read_text(encoding="utf-8"))
            self.assertEqual(new_state["phase"], "CLOSED")
            self.assertEqual(new_state["status"], "CLOSED")

            receipt_path = campaign_dir / new_state["last_receipt"]["path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["event"], "steamer_operator_gate_decision_replayed")
            self.assertEqual(
                receipt["work_item"]["decision"],
                "operator_gate_replay_rejected_shadow_review",
            )

            gate_replay_refs = [
                ref
                for ref in receipt["artifact_refs"]
                if isinstance(ref, str) and ref.startswith("artifacts/steamer/gate-replay/")
            ]
            self.assertTrue(gate_replay_refs)
            gate_replay_payload = json.loads((campaign_dir / gate_replay_refs[0]).read_text(encoding="utf-8"))
            self.assertEqual(gate_replay_payload["operator_decision"], "reject_shadow_review")
            self.assertEqual(gate_replay_payload["phase_after"], "CLOSED")
            self.assertEqual(gate_replay_payload["status_after"], "CLOSED")
            self.assertEqual(gate_replay_payload["operator_note"], "risk posture not acceptable")


    def test_close_blocked_visibility_closes_eligible_seeded_campaign_with_durable_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EXPLORE",
                state_status="BLOCKED",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a", "tw-vcp-b"],
                wakeup_reason="cycle_budget_exhausted",
                cycle_budget=0,
                receipt_event="cycle_budget_exhausted",
                mandate_control_lane_only=True,
                mandate_control_scenario="budget-exhaustion-seeded",
            )

            payload = self._run_json(
                ADVANCE_SCRIPT,
                campaign_dir,
                "--close-blocked-visibility",
                "--close-note",
                "objective already satisfied after seeded visibility capture",
            )
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["changed"])
            self.assertEqual(payload["phase_before"], "EXPLORE")
            self.assertEqual(payload["phase_after"], "CLOSED")
            self.assertEqual(payload["status_before"], "BLOCKED")
            self.assertEqual(payload["status_after"], "CLOSED")
            self.assertTrue(payload["close_blocked_visibility_requested"])
            self.assertTrue(payload["close_blocked_visibility_applied"])

            new_state = json.loads((campaign_dir / "CAMPAIGN_STATE.json").read_text(encoding="utf-8"))
            self.assertEqual(new_state["phase"], "CLOSED")
            self.assertEqual(new_state["status"], "CLOSED")

            receipt_path = campaign_dir / new_state["last_receipt"]["path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["event"], "operator_close_blocked_visibility")
            self.assertEqual(receipt["phase"], "CLOSED")
            self.assertIn("without delivery advancement", receipt["summary"])

            close_refs = [
                ref
                for ref in receipt["artifact_refs"]
                if isinstance(ref, str) and ref.startswith("artifacts/steamer/operator-close/")
            ]
            self.assertTrue(close_refs)
            close_artifact = json.loads((campaign_dir / close_refs[0]).read_text(encoding="utf-8"))
            self.assertEqual(close_artifact["event"], "operator_close_blocked_visibility")
            self.assertEqual(close_artifact["operator_decision"], "close_blocked_visibility_seeded_control")
            self.assertEqual(close_artifact["control_scenario"], "budget-exhaustion-seeded")
            self.assertEqual(close_artifact["wakeup_reason"], "cycle_budget_exhausted")
            self.assertEqual(close_artifact["phase_after"], "CLOSED")
            self.assertEqual(close_artifact["status_after"], "CLOSED")

    def test_close_blocked_visibility_rejects_non_eligible_blocked_campaign(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EXPLORE",
                state_status="BLOCKED",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_reason="cycle_budget_exhausted",
                cycle_budget=0,
                receipt_event="cycle_budget_exhausted",
                mandate_control_lane_only=False,
                mandate_control_scenario=None,
            )

            payload = self._run_json_expect_fail(
                ADVANCE_SCRIPT,
                campaign_dir,
                "--close-blocked-visibility",
            )
            self.assertFalse(payload["ok"])
            self.assertFalse(payload["changed"])
            self.assertTrue(payload["close_blocked_visibility_requested"])
            self.assertFalse(payload["close_blocked_visibility_applied"])
            self.assertTrue(any("control_lane_only" in item for item in payload["errors"]))

    def test_inspect_surfaces_blocked_cause_and_resume_hint_for_queue_empty_blocked_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EXPLORE",
                state_status="BLOCKED",
                active_item_id=None,
                item_queue=[],
                wakeup_reason="steamer_no_candidate_available",
            )

            explore_payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(explore_payload["ok"])
            self.assertEqual(explore_payload["blocked_cause"]["code"], "queue_empty")
            self.assertTrue(explore_payload["blocked_cause"]["resume_supported"])
            self.assertEqual(explore_payload["resume_hint"]["action"], "run_resume")
            self.assertIn("--resume", explore_payload["resume_hint"]["command"])
            self.assertIn("BLOCKED(EXPLORE)", explore_payload["resume_hint"]["summary"])

        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EVALUATE",
                state_status="BLOCKED",
                active_item_id=None,
                item_queue=[],
                wakeup_reason="steamer_no_candidate_available",
            )

            eval_payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(eval_payload["ok"])
            self.assertEqual(eval_payload["blocked_cause"]["code"], "queue_empty")
            self.assertEqual(eval_payload["resume_hint"]["action"], "run_resume")
            self.assertIn("BLOCKED(EVALUATE)", eval_payload["resume_hint"]["summary"])

    def test_inspect_labels_seeded_blocked_evaluate_fixture_without_fake_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EVALUATE",
                state_status="BLOCKED",
                active_item_id=None,
                item_queue=[],
                wakeup_reason="steamer_no_candidate_available",
                mandate_control_lane_only=True,
                mandate_control_scenario="resume-evaluate-recovery-seeded",
            )

            payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["blocked_cause"]["code"], "queue_empty")
            self.assertEqual(payload["drift"]["status"], "clean")
            self.assertEqual(payload["drift"]["summary"], "note=1")
            codes = {item["code"] for item in payload["drift"]["findings"]}
            self.assertIn("seeded_blocked_evaluate_fixture", codes)
            self.assertNotIn("missing_active_item", codes)

    def test_inspect_surfaces_non_resume_blocked_causes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EXPLORE",
                state_status="BLOCKED",
                active_item_id=None,
                item_queue=[],
                wakeup_reason="cycle_budget_exhausted",
                cycle_budget=0,
            )

            budget_payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(budget_payload["ok"])
            self.assertEqual(budget_payload["blocked_cause"]["code"], "cycle_budget_exhausted")
            self.assertFalse(budget_payload["blocked_cause"]["resume_supported"])
            self.assertEqual(budget_payload["resume_hint"]["action"], "reset_or_recut_budget")

        now = datetime.now(timezone.utc)
        stale_at = (now - timedelta(days=5)).isoformat(timespec="seconds")
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="GATE",
                state_status="OPERATOR_GATE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_reason="steamer_shadow_review_gate",
                receipt_created_at=stale_at,
                state_updated_at=stale_at,
            )

            gate_payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(gate_payload["ok"])
            self.assertEqual(gate_payload["blocked_cause"]["code"], "operator_gate_timeout")
            self.assertEqual(gate_payload["resume_hint"]["action"], "operator_decision_needed")

    def test_inspect_hints_close_blocked_visibility_for_eligible_seeded_budget_visibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EXPLORE",
                state_status="BLOCKED",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_reason="cycle_budget_exhausted",
                cycle_budget=0,
                receipt_event="cycle_budget_exhausted",
                mandate_control_lane_only=True,
                mandate_control_scenario="budget-exhaustion-seeded",
            )

            payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["blocked_cause"]["code"], "cycle_budget_exhausted")
            self.assertEqual(payload["resume_hint"]["action"], "run_close_blocked_visibility")
            self.assertIn("--close-blocked-visibility", payload["resume_hint"]["command"])
            self.assertTrue(payload["blocked_visibility_closeout_eligibility"]["eligible"])

    def test_inspect_surfaces_operator_gate_timeout_visibility_signal(self) -> None:
        now = datetime.now(timezone.utc)
        stale_at = (now - timedelta(days=5)).isoformat(timespec="seconds")
        fresh_at = (now - timedelta(hours=1)).isoformat(timespec="seconds")

        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="GATE",
                state_status="OPERATOR_GATE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_reason="steamer_shadow_review_gate",
                receipt_created_at=stale_at,
                state_updated_at=stale_at,
            )

            stale_payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(stale_payload["ok"])
            stale_gate = stale_payload["operator_gate_visibility"]
            self.assertIsNotNone(stale_gate)
            self.assertTrue(stale_gate["blocked"])
            self.assertTrue(stale_gate["stale"])
            self.assertEqual(stale_gate["signal"], "operator_gate_timeout_exceeded")
            self.assertEqual(stale_gate["timeout_days"], 3)
            self.assertEqual(stale_gate["wakeup_reason"], "steamer_shadow_review_gate")
            self.assertGreater(stale_gate["age_seconds"], stale_gate["timeout_seconds"])
            self.assertGreater(stale_gate["overdue_seconds"], 0)

        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="GATE",
                state_status="OPERATOR_GATE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_reason="steamer_shadow_review_gate",
                receipt_created_at=fresh_at,
                state_updated_at=fresh_at,
            )

            fresh_payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(fresh_payload["ok"])
            fresh_gate = fresh_payload["operator_gate_visibility"]
            self.assertIsNotNone(fresh_gate)
            self.assertFalse(fresh_gate["stale"])
            self.assertEqual(fresh_gate["signal"], "operator_gate_waiting_for_operator")
            self.assertGreaterEqual(fresh_gate["remaining_seconds"], 0)

    def test_inspect_reports_warning_drift_without_raw_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EXPLORE",
                state_status="BLOCKED",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_reason="steamer_no_candidate_available",
            )

            payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["drift"]["status"], "warning")
            codes = {item["code"] for item in payload["drift"]["findings"]}
            self.assertIn("blocked_no_candidate_inconsistent", codes)
            self.assertIsNone(payload["last_work_item"])

    def test_inspect_reports_critical_drift_for_operator_gate_phase_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = self._write_campaign_fixture(
                Path(tmp_dir),
                state_phase="EXPLORE",
                state_status="OPERATOR_GATE",
                active_item_id="tw-vcp-a",
                item_queue=["tw-vcp-a"],
                wakeup_reason="steamer_shadow_review_gate",
            )

            payload = self._run_json(INSPECT_SCRIPT, campaign_dir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["drift"]["status"], "critical")
            codes = {item["code"] for item in payload["drift"]["findings"]}
            self.assertIn("operator_gate_phase_mismatch", codes)


if __name__ == "__main__":
    unittest.main()
