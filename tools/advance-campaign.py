#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from _adapter_runtime import AdapterResolutionError, STUB_RUNTIME_ADAPTER, resolve_runtime_adapter
from _runtime_lib import (
    WORKER_RESULT_TYPES,
    apply_state_patch,
    dump_json_atomic,
    ensure_valid_campaign_state,
    ensure_valid_phase_transition_semantics,
    ensure_valid_receipt_record,
    ensure_valid_worker_state_patch,
    evaluate_blocked_visibility_closeout_eligibility,
    format_receipt_id,
    framework_root_from_script,
    load_json,
    next_receipt_index,
    now_iso,
    read_receipts_tail,
    resolve_campaign_adapter_identity,
    validate_mandate_file,
)


def resolve_campaign_dir(framework_root: Path, campaign_arg: str, campaigns_dir_arg: str | None) -> Path:
    candidate = Path(campaign_arg)
    if candidate.exists():
        return candidate.resolve()

    campaigns_root = Path(campaigns_dir_arg).resolve() if campaigns_dir_arg else framework_root / "campaigns"
    return (campaigns_root / campaign_arg).resolve()


def _phase_instruction(phase: str) -> str:
    return f"advance one bounded step for kernel phase {phase}"


def _resolve_dispatch_adapter(adapter_id: str, dispatch_mode: str):
    if dispatch_mode == "stub":
        return STUB_RUNTIME_ADAPTER
    return resolve_runtime_adapter(adapter_id, allow_stub_fallback=False)


def _validate_work_item_context(work_item: Any) -> None:
    if work_item is None:
        return
    if not isinstance(work_item, dict):
        raise ValueError("worker receipt.work_item must be an object when present")

    for field in ("selection_reason", "decision"):
        value = work_item.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"worker receipt.work_item.{field} must be a non-empty string")

    item_id = work_item.get("id")
    if item_id is not None and not isinstance(item_id, str):
        raise ValueError("worker receipt.work_item.id must be null or string")

    for field in ("queue_before_len", "queue_after_len"):
        if field in work_item:
            value = work_item.get(field)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"worker receipt.work_item.{field} must be a non-negative integer")

    for field in ("queue_before_head", "queue_after_head", "next_item_id"):
        if field in work_item:
            value = work_item.get(field)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"worker receipt.work_item.{field} must be null or string")


def _normalize_artifact_materializations(result: dict[str, Any], artifact_refs: list[str]) -> list[dict[str, Any]]:
    raw = result.get("artifact_materializations")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("worker artifact_materializations must be a list when present")

    normalized: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    artifact_ref_set = set(artifact_refs)

    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"worker artifact_materializations[{index}] must be an object")

        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError(f"worker artifact_materializations[{index}].path must be a non-empty string")
        normalized_path = path.strip()

        rel = Path(normalized_path)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(
                "worker artifact materialization path must be relative without '..': "
                f"{normalized_path}"
            )
        if not normalized_path.startswith("artifacts/"):
            raise ValueError(
                "worker artifact materialization path must stay under artifacts/: "
                f"{normalized_path}"
            )
        if normalized_path in seen_paths:
            raise ValueError(f"duplicate worker artifact materialization path: {normalized_path}")
        seen_paths.add(normalized_path)

        if normalized_path not in artifact_ref_set:
            raise ValueError(
                "worker artifact materialization path must be listed in worker artifact_refs: "
                f"{normalized_path}"
            )

        format_value = item.get("format", "json")
        if not isinstance(format_value, str) or not format_value.strip():
            raise ValueError(
                f"worker artifact_materializations[{index}].format must be a non-empty string"
            )
        materialization_format = format_value.strip().lower()
        if materialization_format not in {"json", "text"}:
            raise ValueError(
                "worker artifact materialization format must be one of ['json', 'text']: "
                f"path={normalized_path}, format={materialization_format}"
            )

        normalized_item: dict[str, Any] = {
            "path": normalized_path,
            "format": materialization_format,
        }
        if materialization_format == "text":
            content = item.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    "worker artifact materialization content must be a non-empty string for text format: "
                    f"path={normalized_path}"
                )
            normalized_item["content"] = content
        else:
            payload = item.get("payload")
            try:
                json.dumps(payload, ensure_ascii=False)
            except TypeError as exc:
                raise ValueError(
                    "worker artifact materialization payload must be JSON-serializable: "
                    f"path={normalized_path} ({exc})"
                ) from exc
            normalized_item["payload"] = payload

        summary = item.get("summary")
        if isinstance(summary, str) and summary.strip():
            normalized_item["summary"] = summary.strip()
        normalized.append(normalized_item)

    return normalized


def _materialize_artifacts(campaign_dir: Path, materializations: list[dict[str, Any]]) -> None:
    for item in materializations:
        target_path = campaign_dir / item["path"]
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if item.get("format") == "text":
            content = item["content"]
            tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")
            tmp_path.write_text(content, encoding="utf-8")
            tmp_path.replace(target_path)
            continue

        dump_json_atomic(target_path, item["payload"])


def validate_worker_result(result: Any, state: dict[str, Any], mandate: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        raise ValueError("worker result must be an object")

    required = {"result_type", "receipt", "artifact_refs", "state_patch"}
    missing = sorted(required - set(result.keys()))
    if missing:
        raise ValueError(f"worker result missing required fields: {', '.join(missing)}")

    result_type = result.get("result_type")
    if result_type not in WORKER_RESULT_TYPES:
        raise ValueError(f"worker result_type must be one of {sorted(WORKER_RESULT_TYPES)}")

    artifact_refs = result.get("artifact_refs")
    if not isinstance(artifact_refs, list) or any(not isinstance(x, str) or not x.strip() for x in artifact_refs):
        raise ValueError("worker artifact_refs must be a list of non-empty strings")

    state_patch = result.get("state_patch")
    ensure_valid_worker_state_patch(state_patch)
    ensure_valid_phase_transition_semantics(
        previous_state=state,
        state_patch=state_patch,
        result_type=result_type,
    )

    receipt = result.get("receipt")
    ensure_valid_receipt_record(
        receipt,
        expected_campaign_id=state["campaign_id"],
        expected_mandate_id=mandate["mandate_id"],
    )
    _validate_work_item_context(receipt.get("work_item"))

    if receipt.get("artifact_refs") != artifact_refs:
        raise ValueError("worker receipt.artifact_refs must match worker artifact_refs")

    expected_receipt_path = f"receipts/{receipt['receipt_id']}.json"
    patch_receipt = state_patch.get("last_receipt")
    if not isinstance(patch_receipt, dict) or patch_receipt.get("path") != expected_receipt_path:
        raise ValueError(
            "worker state_patch.last_receipt.path must match receipt path "
            f"({expected_receipt_path})"
        )

    return _normalize_artifact_materializations(result, artifact_refs)


def render_text_result(payload: dict[str, Any]) -> str:
    lines = ["advance-campaign: OK" if payload["ok"] else "advance-campaign: FAIL"]
    lines.append(f"campaign_dir: {payload['campaign_dir']}")
    lines.append(f"changed: {payload['changed']}")
    if payload.get("adapter_id"):
        lines.append(
            "adapter: "
            f"{payload.get('adapter_id')} "
            f"(source={payload.get('adapter_source')}, runtime={payload.get('runtime_adapter')}, dispatch={payload.get('dispatch_mode')})"
        )
    lines.append(f"phase: {payload['phase_before']} -> {payload['phase_after']}")
    lines.append(f"status: {payload['status_before']} -> {payload['status_after']}")
    if "resume_requested" in payload:
        lines.append(
            f"resume: requested={payload.get('resume_requested')} applied={payload.get('resume_applied')}"
        )
    if payload.get("replay_decision"):
        lines.append(
            "replay_decision: "
            f"decision={payload.get('replay_decision')} applied={payload.get('replay_applied')}"
        )
    if "close_blocked_visibility_requested" in payload:
        lines.append(
            "close_blocked_visibility: "
            "requested="
            f"{payload.get('close_blocked_visibility_requested')} "
            "applied="
            f"{payload.get('close_blocked_visibility_applied')}"
        )

    if payload.get("acted_item_decision"):
        lines.append(
            "acted_item: "
            f"id={payload.get('acted_item_id')} "
            f"reason={payload.get('acted_item_reason')} "
            f"decision={payload.get('acted_item_decision')}"
        )
    if "queue_len_before" in payload and "queue_len_after" in payload:
        lines.append(
            f"queue_len: {payload.get('queue_len_before')} -> {payload.get('queue_len_after')}"
        )

    if payload.get("receipt_path"):
        lines.append(f"receipt: {payload['receipt_path']}")
    materialized = payload.get("materialized_artifacts")
    if isinstance(materialized, list) and materialized:
        lines.append("materialized_artifacts:")
        for path in materialized:
            lines.append(f"- {path}")
    if payload.get("message"):
        lines.append(f"message: {payload['message']}")
    if payload.get("errors"):
        lines.append("errors:")
        for error in payload["errors"]:
            lines.append(f"- {error}")

    return "\n".join(lines)


def _slug_for_path(value: str | None, fallback: str = "visibility") -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or fallback


def _run_close_blocked_visibility(
    *,
    state: dict[str, Any],
    mandate: dict[str, Any],
    campaign_dir: Path,
    state_path: Path,
    receipts_dir: Path,
    adapter_id: str,
    adapter_source: str,
    runtime_adapter: str,
    dispatch_mode: str,
    dry_run: bool,
    phase_before: str,
    status_before: str,
    close_note: str | None,
) -> dict[str, Any]:
    eligibility = evaluate_blocked_visibility_closeout_eligibility(state, mandate)
    if not eligibility["eligible"]:
        raise ValueError(
            "--close-blocked-visibility is only valid for seeded blocked visibility scenarios: "
            + "; ".join(eligibility["reasons"])
        )

    receipt_index = next_receipt_index(receipts_dir)
    receipt_id = format_receipt_id(receipt_index, "operator_close_blocked_visibility")
    receipt_rel_path = f"receipts/{receipt_id}.json"
    receipt_path = campaign_dir / receipt_rel_path
    if receipt_path.exists():
        raise ValueError(f"receipt already exists: {receipt_path}")

    control_scenario = eligibility.get("control_scenario")
    wakeup_reason = eligibility.get("wakeup_reason")
    scenario_slug = _slug_for_path(control_scenario)
    artifact_rel_path = (
        f"artifacts/{adapter_id}/operator-close/"
        f"{receipt_index:03d}_{scenario_slug}_blocked_visibility_closed.json"
    )
    artifact_path = campaign_dir / artifact_rel_path

    close_summary = (
        "operator-authorized close-out for seeded blocked visibility scenario "
        f"(control_scenario={control_scenario}, wakeup_reason={wakeup_reason}); "
        "campaign closed without delivery advancement"
    )

    timestamp = now_iso()
    artifact_payload: dict[str, Any] = {
        "event": "operator_close_blocked_visibility",
        "operator_decision": "close_blocked_visibility_seeded_control",
        "operator_note": close_note,
        "control_scenario": control_scenario,
        "control_lane_only": eligibility.get("control_lane_only"),
        "wakeup_reason": wakeup_reason,
        "phase_before": phase_before,
        "status_before": status_before,
        "phase_after": "CLOSED",
        "status_after": "CLOSED",
        "created_at": timestamp,
    }

    receipt = {
        "receipt_id": receipt_id,
        "campaign_id": state["campaign_id"],
        "mandate_id": mandate["mandate_id"],
        "phase": "CLOSED",
        "event": "operator_close_blocked_visibility",
        "summary": close_summary,
        "artifact_refs": [
            "CAMPAIGN_STATE.json",
            artifact_rel_path,
        ],
        "created_at": timestamp,
    }
    ensure_valid_receipt_record(
        receipt,
        expected_campaign_id=state["campaign_id"],
        expected_mandate_id=mandate["mandate_id"],
    )

    state_patch = {
        "phase": "CLOSED",
        "status": "CLOSED",
        "wakeup": {"needed": False, "reason": None},
        "last_receipt": {
            "path": receipt_rel_path,
            "summary": close_summary,
        },
    }
    new_state = apply_state_patch(state, state_patch)
    ensure_valid_campaign_state(new_state)

    if not dry_run:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        dump_json_atomic(artifact_path, artifact_payload)
        dump_json_atomic(receipt_path, receipt)
        dump_json_atomic(state_path, new_state)

    return {
        "ok": True,
        "changed": True,
        "dry_run": bool(dry_run),
        "campaign_dir": str(campaign_dir),
        "adapter_id": adapter_id,
        "adapter_source": adapter_source,
        "runtime_adapter": runtime_adapter,
        "dispatch_mode": dispatch_mode,
        "phase_before": phase_before,
        "phase_after": new_state["phase"],
        "status_before": status_before,
        "status_after": new_state["status"],
        "result_type": "ADVANCE",
        "resume_requested": False,
        "resume_applied": False,
        "replay_decision": None,
        "replay_applied": False,
        "close_blocked_visibility_requested": True,
        "close_blocked_visibility_applied": True,
        "close_note": close_note,
        "receipt_id": receipt_id,
        "receipt_path": str(receipt_path),
        "materialized_artifacts": [artifact_rel_path],
        "wakeup": new_state.get("wakeup"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Advance one campaign by one bounded dispatcher step.")
    parser.add_argument("campaign", help="Campaign id under campaigns/ or path to campaign directory")
    parser.add_argument(
        "--campaigns-dir",
        default=None,
        help="Optional campaigns root when <campaign> is an id (defaults to <framework>/campaigns)",
    )
    parser.add_argument(
        "--dispatch-mode",
        choices=["adapter", "stub"],
        default="adapter",
        help="Worker dispatch mode (default: adapter). Use stub only for explicit dev fallback.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and simulate one step without writing files")
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Allow one adapter-defined recovery/resume attempt when campaign is BLOCKED "
            "(for steamer: recover queue-empty EXPLORE by retrying idea-scout, or recover "
            "queue-empty BLOCKED EVALUATE by back-shifting to EXPLORE with reseeded context)"
        ),
    )
    parser.add_argument(
        "--replay-decision",
        choices=["approve_shadow_review", "reject_shadow_review"],
        default=None,
        help=(
            "Replay one operator decision when campaign is at OPERATOR_GATE "
            "(steamer paths: approve_shadow_review -> DELIVER, reject_shadow_review -> CLOSED)"
        ),
    )
    parser.add_argument(
        "--replay-note",
        default=None,
        help="Optional operator note persisted in the gate decision replay artifact",
    )
    parser.add_argument(
        "--close-blocked-visibility",
        action="store_true",
        help=(
            "Operator-authorized close-out for eligible seeded BLOCKED visibility scenarios "
            "(narrow path: control-lane-only + seeded control_scenario + blocked visibility wakeup)"
        ),
    )
    parser.add_argument(
        "--close-note",
        default=None,
        help="Optional operator note persisted in the blocked-visibility close-out artifact",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    framework_root = framework_root_from_script(__file__)
    campaign_dir = resolve_campaign_dir(framework_root, args.campaign, args.campaigns_dir)
    mandate_path = campaign_dir / "MANDATE.yaml"
    state_path = campaign_dir / "CAMPAIGN_STATE.json"
    receipts_dir = campaign_dir / "receipts"

    errors: list[str] = []
    if not campaign_dir.exists() or not campaign_dir.is_dir():
        errors.append(f"campaign directory not found: {campaign_dir}")
    if not mandate_path.exists():
        errors.append(f"missing mandate file: {mandate_path}")
    if not state_path.exists():
        errors.append(f"missing state file: {state_path}")
    if not receipts_dir.exists() or not receipts_dir.is_dir():
        errors.append(f"missing receipts directory: {receipts_dir}")

    if errors:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": None,
            "phase_after": None,
            "status_before": None,
            "status_after": None,
            "errors": errors,
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    mandate_result = validate_mandate_file(mandate_path, framework_root)
    if not mandate_result.ok:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": None,
            "phase_after": None,
            "status_before": None,
            "status_after": None,
            "errors": [f"invalid mandate: {e}" for e in mandate_result.errors],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    mandate = mandate_result.mandate

    try:
        state = load_json(state_path)
        ensure_valid_campaign_state(state)
    except Exception as exc:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": None,
            "phase_after": None,
            "status_before": None,
            "status_after": None,
            "errors": [f"invalid campaign state: {exc}"],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    phase_before = state["phase"]
    status_before = state["status"]

    if state["campaign_id"] != mandate["mandate_id"] or state["mandate_id"] != mandate["mandate_id"]:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "errors": [
                "campaign state/mandate id mismatch: "
                f"state campaign_id={state['campaign_id']}, state mandate_id={state['mandate_id']}, "
                f"mandate_id={mandate['mandate_id']}"
            ],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    try:
        adapter_identity = resolve_campaign_adapter_identity(state, mandate)
    except Exception as exc:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "errors": [f"failed to resolve adapter identity: {exc}"],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    try:
        dispatch_adapter = _resolve_dispatch_adapter(adapter_identity.adapter_id, args.dispatch_mode)
    except AdapterResolutionError as exc:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "dispatch_mode": args.dispatch_mode,
            "errors": [str(exc)],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    replay_note = args.replay_note.strip() if isinstance(args.replay_note, str) and args.replay_note.strip() else None
    close_note = args.close_note.strip() if isinstance(args.close_note, str) and args.close_note.strip() else None

    action_count = int(bool(args.resume)) + int(args.replay_decision is not None) + int(
        bool(args.close_blocked_visibility)
    )
    if action_count > 1:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "resume_requested": bool(args.resume),
            "replay_decision": args.replay_decision,
            "close_blocked_visibility_requested": bool(args.close_blocked_visibility),
            "errors": [
                "choose only one bounded action at a time: --resume OR --replay-decision OR --close-blocked-visibility"
            ],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    if close_note and not args.close_blocked_visibility:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "resume_requested": bool(args.resume),
            "replay_decision": args.replay_decision,
            "close_blocked_visibility_requested": bool(args.close_blocked_visibility),
            "errors": ["--close-note requires --close-blocked-visibility"],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    if args.replay_decision and status_before != "OPERATOR_GATE":
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "resume_requested": bool(args.resume),
            "replay_decision": args.replay_decision,
            "errors": [
                "--replay-decision is only valid when campaign status is OPERATOR_GATE"
            ],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    if args.close_blocked_visibility and status_before != "BLOCKED":
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "resume_requested": bool(args.resume),
            "replay_decision": args.replay_decision,
            "close_blocked_visibility_requested": True,
            "errors": [
                "--close-blocked-visibility is only valid when campaign status is BLOCKED"
            ],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    if status_before == "CLOSED":
        payload = {
            "ok": True,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "resume_requested": bool(args.resume),
            "replay_decision": args.replay_decision,
            "close_blocked_visibility_requested": bool(args.close_blocked_visibility),
            "close_blocked_visibility_applied": False,
            "message": "campaign status is CLOSED; no bounded step executed",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload))
        return 0

    if status_before == "OPERATOR_GATE" and not args.replay_decision:
        payload = {
            "ok": True,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "resume_requested": bool(args.resume),
            "replay_decision": None,
            "close_blocked_visibility_requested": bool(args.close_blocked_visibility),
            "close_blocked_visibility_applied": False,
            "message": (
                "campaign status is OPERATOR_GATE; pass --replay-decision "
                "approve_shadow_review (continue to DELIVER) or reject_shadow_review "
                "(close campaign)"
            ),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload))
        return 0

    if status_before == "BLOCKED" and not args.resume and not args.close_blocked_visibility:
        closeout_eligibility = evaluate_blocked_visibility_closeout_eligibility(state, mandate)
        blocked_message = "campaign status is BLOCKED; pass --resume to attempt one recovery/resume step"
        if closeout_eligibility.get("eligible"):
            blocked_message = (
                "campaign status is BLOCKED; pass --resume for recovery or "
                "--close-blocked-visibility for seeded blocked visibility close-out"
            )

        payload = {
            "ok": True,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "resume_requested": False,
            "replay_decision": args.replay_decision,
            "close_blocked_visibility_requested": False,
            "close_blocked_visibility_applied": False,
            "message": blocked_message,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload))
        return 0

    if args.close_blocked_visibility:
        try:
            payload = _run_close_blocked_visibility(
                state=state,
                mandate=mandate,
                campaign_dir=campaign_dir,
                state_path=state_path,
                receipts_dir=receipts_dir,
                adapter_id=adapter_identity.adapter_id,
                adapter_source=adapter_identity.source,
                runtime_adapter=dispatch_adapter.adapter_id,
                dispatch_mode=args.dispatch_mode,
                dry_run=bool(args.dry_run),
                phase_before=phase_before,
                status_before=status_before,
                close_note=close_note,
            )
        except Exception as exc:
            payload = {
                "ok": False,
                "changed": False,
                "campaign_dir": str(campaign_dir),
                "phase_before": phase_before,
                "phase_after": phase_before,
                "status_before": status_before,
                "status_after": status_before,
                "adapter_id": adapter_identity.adapter_id,
                "adapter_source": adapter_identity.source,
                "runtime_adapter": dispatch_adapter.adapter_id,
                "dispatch_mode": args.dispatch_mode,
                "close_blocked_visibility_requested": True,
                "close_blocked_visibility_applied": False,
                "errors": [str(exc)],
            }
            print(
                json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
                file=sys.stderr,
            )
            return 1

        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload))
        return 0

    normalized_mandate = (
        dispatch_adapter.normalize_mandate(mandate)
        if callable(dispatch_adapter.normalize_mandate)
        else mandate
    )

    worker_context_pack = {
        "mandate": normalized_mandate,
        "campaign_state": state,
        "phase_instruction": _phase_instruction(phase_before),
        "current_item": state.get("active_item_id"),
        "receipts_tail": read_receipts_tail(receipts_dir, limit=5),
        "adapter_context": None,
        "resume_requested": bool(args.resume),
        "replay_decision": args.replay_decision,
        "replay_note": replay_note,
        "adapter_identity": {
            "adapter_id": adapter_identity.adapter_id,
            "source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
        },
    }
    if callable(dispatch_adapter.enrich_context):
        worker_context_pack["adapter_context"] = dispatch_adapter.enrich_context(worker_context_pack)

    result = dispatch_adapter.worker(worker_context_pack, receipt_index=next_receipt_index(receipts_dir))

    try:
        artifact_materializations = validate_worker_result(result, state=state, mandate=normalized_mandate)
    except Exception as exc:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
            "errors": [f"invalid worker result: {exc}"],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    new_state = apply_state_patch(state, result["state_patch"])

    try:
        ensure_valid_campaign_state(new_state)
    except Exception as exc:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
            "errors": [f"patched campaign state invalid: {exc}"],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    receipt = result["receipt"]
    receipt_path = receipts_dir / f"{receipt['receipt_id']}.json"
    if receipt_path.exists():
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "adapter_id": adapter_identity.adapter_id,
            "adapter_source": adapter_identity.source,
            "runtime_adapter": dispatch_adapter.adapter_id,
            "dispatch_mode": args.dispatch_mode,
            "errors": [f"receipt already exists: {receipt_path}"],
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload),
            file=sys.stderr,
        )
        return 1

    if not args.dry_run:
        _materialize_artifacts(campaign_dir, artifact_materializations)
        dump_json_atomic(receipt_path, receipt)
        dump_json_atomic(state_path, new_state)

    work_item = receipt.get("work_item") if isinstance(receipt.get("work_item"), dict) else None
    payload = {
        "ok": True,
        "changed": True,
        "dry_run": bool(args.dry_run),
        "campaign_dir": str(campaign_dir),
        "adapter_id": adapter_identity.adapter_id,
        "adapter_source": adapter_identity.source,
        "runtime_adapter": dispatch_adapter.adapter_id,
        "dispatch_mode": args.dispatch_mode,
        "phase_before": phase_before,
        "phase_after": new_state["phase"],
        "status_before": status_before,
        "status_after": new_state["status"],
        "result_type": result["result_type"],
        "resume_requested": bool(args.resume),
        "resume_applied": bool(status_before == "BLOCKED" and new_state["status"] == "ACTIVE"),
        "replay_decision": args.replay_decision,
        "replay_applied": bool(
            status_before == "OPERATOR_GATE"
            and args.replay_decision is not None
            and new_state["status"] != "OPERATOR_GATE"
        ),
        "close_blocked_visibility_requested": bool(args.close_blocked_visibility),
        "close_blocked_visibility_applied": False,
        "receipt_id": receipt["receipt_id"],
        "receipt_path": str(receipt_path),
        "materialized_artifacts": [item["path"] for item in artifact_materializations],
        "wakeup": new_state.get("wakeup"),
    }
    if work_item is not None:
        payload.update(
            {
                "acted_item_id": work_item.get("id"),
                "acted_item_reason": work_item.get("selection_reason"),
                "acted_item_decision": work_item.get("decision"),
                "queue_len_before": work_item.get("queue_before_len"),
                "queue_len_after": work_item.get("queue_after_len"),
            }
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
