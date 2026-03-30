#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _adapter_runtime import AdapterResolutionError, resolve_runtime_adapter
from _runtime_lib import (
    ensure_valid_campaign_state,
    evaluate_blocked_visibility_closeout_eligibility,
    framework_root_from_script,
    list_receipt_files,
    load_json,
    load_yaml,
    resolve_campaign_adapter_identity,
    validate_mandate_file,
    validate_receipt_record,
)


def resolve_campaign_dir(framework_root: Path, campaign_arg: str, campaigns_dir_arg: str | None) -> Path:
    candidate = Path(campaign_arg)
    if candidate.exists():
        return candidate.resolve()

    campaigns_root = Path(campaigns_dir_arg).resolve() if campaigns_dir_arg else framework_root / "campaigns"
    return (campaigns_root / campaign_arg).resolve()


def _format_work_item_short(work_item: dict[str, Any] | None) -> str | None:
    if not isinstance(work_item, dict):
        return None
    decision = work_item.get("decision")
    reason = work_item.get("selection_reason")
    if not isinstance(decision, str) or not decision.strip():
        return None
    return (
        f"id={work_item.get('id')} "
        f"reason={reason} "
        f"decision={decision}"
    )


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _classify_blocked_cause(
    state: dict[str, Any] | None,
    operator_gate_visibility: dict[str, Any] | None,
    drift_report: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(state, dict):
        return None

    status = state.get("status")
    phase = state.get("phase")
    wakeup = state.get("wakeup") if isinstance(state.get("wakeup"), dict) else {}
    wakeup_reason = wakeup.get("reason") if isinstance(wakeup.get("reason"), str) else None

    if status == "BLOCKED":
        if wakeup_reason == "steamer_no_candidate_available":
            return {
                "code": "queue_empty",
                "wakeup_reason": wakeup_reason,
                "resume_supported": phase in {"EXPLORE", "EVALUATE"},
                "source": "state.wakeup.reason",
            }
        if wakeup_reason == "cycle_budget_exhausted":
            return {
                "code": "cycle_budget_exhausted",
                "wakeup_reason": wakeup_reason,
                "resume_supported": False,
                "source": "state.wakeup.reason",
            }
        if isinstance(drift_report, dict) and drift_report.get("status") in {"warning", "critical"}:
            return {
                "code": "adapter_drift",
                "wakeup_reason": wakeup_reason,
                "resume_supported": False,
                "source": "inspect.drift",
            }
        return {
            "code": "unknown",
            "wakeup_reason": wakeup_reason,
            "resume_supported": False,
            "source": "fallback",
        }

    if status == "OPERATOR_GATE" and isinstance(operator_gate_visibility, dict):
        if operator_gate_visibility.get("signal") == "operator_gate_timeout_exceeded":
            return {
                "code": "operator_gate_timeout",
                "wakeup_reason": operator_gate_visibility.get("wakeup_reason"),
                "resume_supported": False,
                "source": "operator_gate_visibility.signal",
            }

    return None


def _build_resume_hint(
    campaign_dir: Path,
    state: dict[str, Any] | None,
    blocked_cause: dict[str, Any] | None,
    mandate: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(state, dict) or not isinstance(blocked_cause, dict):
        return None

    code = blocked_cause.get("code")
    phase = state.get("phase")
    campaign_arg = str(campaign_dir)

    if code == "queue_empty" and phase == "EXPLORE":
        return {
            "action": "run_resume",
            "command": f"python3 tools/advance-campaign.py {campaign_arg} --resume",
            "summary": "Queue-empty BLOCKED(EXPLORE). Resume is the intended move: reseed candidate context and retry idea-scout in one bounded step.",
        }

    if code == "queue_empty" and phase == "EVALUATE":
        return {
            "action": "run_resume",
            "command": f"python3 tools/advance-campaign.py {campaign_arg} --resume",
            "summary": "Queue-empty BLOCKED(EVALUATE). Resume is the intended move: reseed candidate context and back-shift to EXPLORE for one bounded recovery step.",
        }

    if code == "cycle_budget_exhausted":
        closeout_eligibility = evaluate_blocked_visibility_closeout_eligibility(state, mandate)
        if closeout_eligibility.get("eligible"):
            return {
                "action": "run_close_blocked_visibility",
                "command": f"python3 tools/advance-campaign.py {campaign_arg} --close-blocked-visibility",
                "summary": (
                    "Seeded blocked visibility scenario is eligible for operator close-out. "
                    "Use --close-blocked-visibility to close without pretending delivery work was executed."
                ),
            }
        return {
            "action": "reset_or_recut_budget",
            "command": None,
            "summary": "Cycle budget is exhausted. Do not use --resume; replenish/reset cycle_budget or re-cut the campaign before advancing again.",
        }

    if code == "operator_gate_timeout":
        return {
            "action": "operator_decision_needed",
            "command": None,
            "summary": "Operator gate timeout has gone stale. Review the gate packet and record one explicit replay decision instead of using --resume.",
        }

    if code == "adapter_drift":
        return {
            "action": "inspect_and_reconcile_drift",
            "command": None,
            "summary": "Inspect drift findings before any resume attempt; current blocked state looks internally inconsistent.",
        }

    return None


def _compute_operator_gate_visibility(
    state: dict[str, Any] | None,
    mandate: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(state, dict):
        return None
    if state.get("status") != "OPERATOR_GATE":
        return None

    wakeup = state.get("wakeup") if isinstance(state.get("wakeup"), dict) else {}
    wakeup_reason = wakeup.get("reason") if isinstance(wakeup.get("reason"), str) else None

    updated_at_raw = state.get("updated_at")
    updated_at = _parse_iso_datetime(updated_at_raw)

    age_seconds: int | None = None
    if updated_at is not None:
        now_dt = datetime.now(tz=updated_at.tzinfo)
        age_seconds = max(0, int((now_dt - updated_at).total_seconds()))

    timeout_days: int | None = None
    if isinstance(mandate, dict):
        escalation = mandate.get("escalation")
        if isinstance(escalation, dict):
            timeout_candidate = escalation.get("operator_gate_timeout_days")
            if isinstance(timeout_candidate, int) and timeout_candidate > 0:
                timeout_days = timeout_candidate

    timeout_seconds = timeout_days * 24 * 60 * 60 if timeout_days is not None else None
    stale: bool | None = None
    if timeout_seconds is not None and age_seconds is not None:
        stale = age_seconds >= timeout_seconds

    signal = "operator_gate_waiting_for_operator"
    signal_reason = "within_timeout_window"
    if timeout_seconds is None:
        signal_reason = "timeout_unconfigured"
    elif age_seconds is None:
        signal_reason = "updated_at_missing_or_invalid"
    elif stale:
        signal = "operator_gate_timeout_exceeded"
        signal_reason = "timeout_window_exceeded"

    remaining_seconds: int | None = None
    overdue_seconds: int | None = None
    if timeout_seconds is not None and age_seconds is not None:
        delta = timeout_seconds - age_seconds
        if delta >= 0:
            remaining_seconds = delta
        else:
            overdue_seconds = abs(delta)

    return {
        "blocked": True,
        "status": "OPERATOR_GATE",
        "wakeup_reason": wakeup_reason,
        "updated_at": updated_at_raw if isinstance(updated_at_raw, str) else None,
        "age_seconds": age_seconds,
        "timeout_days": timeout_days,
        "timeout_seconds": timeout_seconds,
        "remaining_seconds": remaining_seconds,
        "overdue_seconds": overdue_seconds,
        "stale": stale,
        "signal": signal,
        "signal_reason": signal_reason,
    }


def render_text_report(payload: dict[str, Any], receipt_preview_limit: int) -> str:
    lines: list[str] = []
    lines.append("inspect-campaign: OK" if payload["ok"] else "inspect-campaign: FAIL")
    lines.append(f"campaign_dir: {payload['campaign_dir']}")

    if payload.get("state"):
        state = payload["state"]
        lines.append(f"campaign_id: {state.get('campaign_id')}")
        lines.append(f"mandate_id: {state.get('mandate_id')}")
        lines.append(
            "adapter: "
            f"{payload.get('adapter_id')} "
            f"(source={payload.get('adapter_source')}, runtime_registered={payload.get('adapter_runtime_registered')})"
        )
        lines.append(f"phase: {state.get('phase')}")
        lines.append(f"status: {state.get('status')}")
        lines.append(f"cycle_budget: {state.get('cycle_budget')}")
        lines.append(f"back_transitions_remaining: {state.get('back_transitions_remaining')}")
        lines.append(f"active_item_id: {state.get('active_item_id')}")
        queue = state.get("item_queue")
        lines.append(f"item_queue_len: {len(queue) if isinstance(queue, list) else 'n/a'}")

        wakeup = state.get("wakeup", {})
        lines.append(f"wakeup: needed={wakeup.get('needed')} reason={wakeup.get('reason')}")
        lines.append(f"updated_at: {state.get('updated_at')}")

        blocked_cause = payload.get("blocked_cause")
        if isinstance(blocked_cause, dict):
            lines.append(
                "blocked_cause: "
                f"code={blocked_cause.get('code')} "
                f"wakeup_reason={blocked_cause.get('wakeup_reason')} "
                f"resume_supported={blocked_cause.get('resume_supported')}"
            )

        closeout_eligibility = payload.get("blocked_visibility_closeout_eligibility")
        if isinstance(closeout_eligibility, dict):
            lines.append(
                "blocked_visibility_closeout: "
                f"eligible={closeout_eligibility.get('eligible')} "
                f"control_scenario={closeout_eligibility.get('control_scenario')} "
                f"wakeup_reason={closeout_eligibility.get('wakeup_reason')}"
            )

        resume_hint = payload.get("resume_hint")
        if isinstance(resume_hint, dict):
            lines.append(
                "resume_hint: "
                f"action={resume_hint.get('action')} "
                f"command={resume_hint.get('command')}"
            )
            lines.append(f"resume_hint_summary: {resume_hint.get('summary')}")

        gate_visibility = payload.get("operator_gate_visibility")
        if isinstance(gate_visibility, dict):
            lines.append(
                "operator_gate: "
                f"blocked={gate_visibility.get('blocked')} "
                f"stale={gate_visibility.get('stale')} "
                f"signal={gate_visibility.get('signal')} "
                f"signal_reason={gate_visibility.get('signal_reason')}"
            )
            lines.append(
                "operator_gate_timing: "
                f"age_seconds={gate_visibility.get('age_seconds')} "
                f"timeout_seconds={gate_visibility.get('timeout_seconds')} "
                f"remaining_seconds={gate_visibility.get('remaining_seconds')} "
                f"overdue_seconds={gate_visibility.get('overdue_seconds')}"
            )

        last_receipt = state.get("last_receipt", {})
        lines.append(
            "last_receipt: "
            f"path={last_receipt.get('path')} summary={last_receipt.get('summary')}"
        )
        if payload.get("last_work_item"):
            lines.append(f"last_work_item: {_format_work_item_short(payload.get('last_work_item'))}")

    lines.append(f"receipts_total: {payload['receipts_total']}")

    drift = payload.get("drift")
    if isinstance(drift, dict):
        lines.append(f"drift: {drift.get('status')} ({drift.get('summary')})")
        for finding in drift.get("findings", []):
            lines.append(
                "- "
                + f"[{finding.get('severity')}] {finding.get('code')}: {finding.get('message')}"
            )

    preview = payload.get("receipts_preview", [])
    if preview:
        lines.append(f"receipts_preview(last {receipt_preview_limit}):")
        for item in preview:
            cols = [
                str(item.get("receipt_id")),
                str(item.get("phase")),
                str(item.get("event")),
                str(item.get("summary")),
                str(item.get("created_at")),
            ]
            work_item_short = _format_work_item_short(item.get("work_item"))
            if work_item_short:
                cols.append(work_item_short)
            lines.append("- " + " | ".join(cols))

    if payload.get("warnings"):
        lines.append("warnings:")
        for warning in payload["warnings"]:
            lines.append(f"- {warning}")

    if payload.get("errors"):
        lines.append("errors:")
        for error in payload["errors"]:
            lines.append(f"- {error}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a file-backed campaign state and receipt stream.")
    parser.add_argument("campaign", help="Campaign id under campaigns/ or path to campaign directory")
    parser.add_argument(
        "--campaigns-dir",
        default=None,
        help="Optional campaigns root when <campaign> is an id (defaults to <framework>/campaigns)",
    )
    parser.add_argument(
        "--receipts",
        type=int,
        default=5,
        help="How many latest receipts to include in preview output (default: 5)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    framework_root = framework_root_from_script(__file__)
    campaign_dir = resolve_campaign_dir(framework_root, args.campaign, args.campaigns_dir)
    mandate_path = campaign_dir / "MANDATE.yaml"
    state_path = campaign_dir / "CAMPAIGN_STATE.json"
    receipts_dir = campaign_dir / "receipts"

    errors: list[str] = []
    warnings: list[str] = []

    if not campaign_dir.exists() or not campaign_dir.is_dir():
        errors.append(f"campaign directory not found: {campaign_dir}")

    if not mandate_path.exists():
        errors.append(f"missing mandate file: {mandate_path}")

    if not state_path.exists():
        errors.append(f"missing state file: {state_path}")

    if not receipts_dir.exists() or not receipts_dir.is_dir():
        errors.append(f"missing receipts directory: {receipts_dir}")

    mandate_data: dict[str, Any] | None = None
    state_data: dict[str, Any] | None = None
    receipt_files: list[Path] = []
    receipts_preview: list[dict[str, Any]] = []
    adapter_id: str | None = None
    adapter_source: str | None = None
    adapter_runtime_registered = False
    dispatch_adapter = None
    drift_report: dict[str, Any] | None = None
    operator_gate_visibility: dict[str, Any] | None = None
    last_work_item: dict[str, Any] | None = None

    if not errors:
        mandate_result = validate_mandate_file(mandate_path, framework_root)
        if not mandate_result.ok:
            errors.extend(f"invalid mandate: {item}" for item in mandate_result.errors)
        warnings.extend(mandate_result.warnings)

        try:
            mandate_payload = load_yaml(mandate_path)
            if isinstance(mandate_payload, dict):
                mandate_data = mandate_payload
            else:
                errors.append("MANDATE.yaml must parse to an object")
        except Exception as exc:
            errors.append(f"failed to read MANDATE.yaml: {exc}")

        try:
            loaded_state = load_json(state_path)
            ensure_valid_campaign_state(loaded_state)
            state_data = loaded_state
        except Exception as exc:
            errors.append(f"invalid CAMPAIGN_STATE.json: {exc}")

        if isinstance(state_data, dict) and isinstance(mandate_data, dict):
            try:
                adapter_identity = resolve_campaign_adapter_identity(state_data, mandate_data)
                adapter_id = adapter_identity.adapter_id
                adapter_source = adapter_identity.source
                dispatch_adapter = resolve_runtime_adapter(adapter_id)
                adapter_runtime_registered = True
            except AdapterResolutionError as exc:
                warnings.append(str(exc))
            except Exception as exc:
                errors.append(f"failed to resolve adapter identity: {exc}")

        receipt_files = list_receipt_files(receipts_dir)
        for path in receipt_files[-max(0, args.receipts) :]:
            try:
                receipt = load_json(path)
            except Exception as exc:
                errors.append(f"failed to read receipt {path.name}: {exc}")
                continue

            if not isinstance(receipt, dict):
                errors.append(f"receipt {path.name} must be an object")
                continue

            receipt_errors = validate_receipt_record(
                receipt,
                expected_campaign_id=state_data.get("campaign_id") if isinstance(state_data, dict) else None,
                expected_mandate_id=state_data.get("mandate_id") if isinstance(state_data, dict) else None,
            )
            if receipt_errors:
                errors.extend(f"receipt {path.name}: {item}" for item in receipt_errors)

            receipt_preview = {
                "receipt_id": receipt.get("receipt_id"),
                "phase": receipt.get("phase"),
                "event": receipt.get("event"),
                "summary": receipt.get("summary"),
                "created_at": receipt.get("created_at"),
                "path": str(path),
                "work_item": receipt.get("work_item") if isinstance(receipt.get("work_item"), dict) else None,
            }
            receipts_preview.append(receipt_preview)

        if isinstance(state_data, dict):
            last_receipt_payload: dict[str, Any] | None = None
            last_receipt = state_data.get("last_receipt")
            if isinstance(last_receipt, dict) and isinstance(last_receipt.get("path"), str):
                expected_last = campaign_dir / last_receipt["path"]
                if not expected_last.exists():
                    warnings.append(
                        "state last_receipt path does not exist on disk: "
                        f"{last_receipt['path']}"
                    )
                else:
                    try:
                        payload = load_json(expected_last)
                        if isinstance(payload, dict):
                            last_receipt_payload = payload
                            if isinstance(payload.get("work_item"), dict):
                                last_work_item = payload.get("work_item")
                        else:
                            warnings.append(
                                "state last_receipt path is not a receipt object: "
                                f"{last_receipt['path']}"
                            )
                    except Exception as exc:
                        warnings.append(
                            "failed to read state last_receipt payload: "
                            f"{last_receipt['path']} ({exc})"
                        )

            if isinstance(mandate_data, dict):
                if state_data.get("campaign_id") != mandate_data.get("mandate_id"):
                    errors.append(
                        "campaign_id mismatch between state and mandate: "
                        f"{state_data.get('campaign_id')} vs {mandate_data.get('mandate_id')}"
                    )
                if state_data.get("mandate_id") != mandate_data.get("mandate_id"):
                    errors.append(
                        "mandate_id mismatch between state and mandate: "
                        f"{state_data.get('mandate_id')} vs {mandate_data.get('mandate_id')}"
                    )

            if (
                isinstance(mandate_data, dict)
                and adapter_runtime_registered
                and dispatch_adapter is not None
                and callable(dispatch_adapter.inspect_hook)
            ):
                try:
                    drift_candidate = dispatch_adapter.inspect_hook(
                        state_data,
                        {
                            "campaign_dir": str(campaign_dir),
                            "mandate": mandate_data,
                            "last_receipt_payload": last_receipt_payload,
                            "receipts_total": len(receipt_files),
                        },
                    )
                    if isinstance(drift_candidate, dict):
                        drift_report = drift_candidate
                except Exception as exc:
                    warnings.append(f"adapter inspect hook failed: {exc}")

    operator_gate_visibility = _compute_operator_gate_visibility(state_data, mandate_data)
    blocked_cause = _classify_blocked_cause(state_data, operator_gate_visibility, drift_report)
    blocked_visibility_closeout_eligibility = evaluate_blocked_visibility_closeout_eligibility(
        state_data,
        mandate_data,
    )
    resume_hint = _build_resume_hint(campaign_dir, state_data, blocked_cause, mandate_data)

    payload = {
        "ok": not errors,
        "campaign_dir": str(campaign_dir),
        "adapter": adapter_id,
        "adapter_id": adapter_id,
        "adapter_source": adapter_source,
        "adapter_runtime_registered": adapter_runtime_registered,
        "state": state_data,
        "blocked_cause": blocked_cause,
        "blocked_visibility_closeout_eligibility": blocked_visibility_closeout_eligibility,
        "resume_hint": resume_hint,
        "operator_gate_visibility": operator_gate_visibility,
        "last_work_item": last_work_item,
        "receipts_total": len(receipt_files),
        "receipts_preview": receipts_preview,
        "drift": drift_report,
        "warnings": warnings,
        "errors": errors,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        stream = sys.stdout if payload["ok"] else sys.stderr
        print(render_text_report(payload, receipt_preview_limit=args.receipts), file=stream)

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
