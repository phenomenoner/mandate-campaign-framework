#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from _runtime_lib import (
    WORKER_RESULT_TYPES,
    apply_state_patch,
    dump_json_atomic,
    ensure_valid_campaign_state,
    ensure_valid_phase_transition_semantics,
    ensure_valid_receipt_record,
    ensure_valid_worker_state_patch,
    format_receipt_id,
    framework_root_from_script,
    load_json,
    next_receipt_index,
    now_iso,
    read_receipts_tail,
    validate_mandate_file,
)

PHASE_FORWARD_DEFAULT = {
    "INTAKE": "EXPLORE",
    "EXPLORE": "EVALUATE",
    "EVALUATE": "SYNTHESIZE",
    "SYNTHESIZE": "GATE",
    "GATE": "DELIVER",
    "DELIVER": "CLOSED",
}


def resolve_campaign_dir(framework_root: Path, campaign_arg: str, campaigns_dir_arg: str | None) -> Path:
    candidate = Path(campaign_arg)
    if candidate.exists():
        return candidate.resolve()

    campaigns_root = Path(campaigns_dir_arg).resolve() if campaigns_dir_arg else framework_root / "campaigns"
    return (campaigns_root / campaign_arg).resolve()


def _phase_instruction(phase: str) -> str:
    return f"advance one bounded step for kernel phase {phase}"


def run_stub_worker(context_pack: dict[str, Any], receipt_index: int) -> dict[str, Any]:
    state = context_pack["campaign_state"]
    mandate = context_pack["mandate"]
    current_phase = state["phase"]
    campaign_id = state["campaign_id"]
    mandate_id = mandate["mandate_id"]

    if state["cycle_budget"] <= 0 and current_phase not in {"DELIVER", "CLOSED"}:
        event = "cycle_budget_exhausted"
        receipt_id = format_receipt_id(receipt_index, event)
        receipt_rel_path = f"receipts/{receipt_id}.json"
        summary = "campaign blocked: cycle budget exhausted"
        artifact_refs = ["CAMPAIGN_STATE.json"]
        return {
            "result_type": "BLOCK",
            "artifact_refs": artifact_refs,
            "state_patch": {
                "status": "BLOCKED",
                "wakeup": {"needed": True, "reason": "cycle_budget_exhausted"},
                "last_receipt": {"path": receipt_rel_path, "summary": summary},
            },
            "receipt": {
                "receipt_id": receipt_id,
                "campaign_id": campaign_id,
                "mandate_id": mandate_id,
                "phase": current_phase,
                "event": event,
                "summary": summary,
                "artifact_refs": artifact_refs,
                "created_at": now_iso(),
            },
            "next_phase_hint": current_phase,
            "wakeup": {"needed": True, "reason": "cycle_budget_exhausted"},
        }

    next_phase = PHASE_FORWARD_DEFAULT.get(current_phase, "CLOSED")
    next_status = "CLOSED" if next_phase == "CLOSED" else "ACTIVE"
    wakeup = {"needed": False, "reason": None}
    if next_phase == "DELIVER":
        wakeup = {"needed": True, "reason": "delivery_ready"}

    event = f"phase_advanced_{current_phase.lower()}_to_{next_phase.lower()}"
    receipt_id = format_receipt_id(receipt_index, event)
    receipt_rel_path = f"receipts/{receipt_id}.json"
    summary = f"advanced campaign one bounded step: {current_phase} -> {next_phase}"
    artifact_refs = ["CAMPAIGN_STATE.json"]

    return {
        "result_type": "DELIVER" if next_phase == "DELIVER" else "ADVANCE",
        "artifact_refs": artifact_refs,
        "state_patch": {
            "phase": next_phase,
            "status": next_status,
            "cycle_budget": max(0, state["cycle_budget"] - 1),
            "wakeup": wakeup,
            "last_receipt": {"path": receipt_rel_path, "summary": summary},
        },
        "receipt": {
            "receipt_id": receipt_id,
            "campaign_id": campaign_id,
            "mandate_id": mandate_id,
            "phase": next_phase,
            "event": event,
            "summary": summary,
            "artifact_refs": artifact_refs,
            "created_at": now_iso(),
        },
        "next_phase_hint": next_phase,
        "wakeup": wakeup,
    }


def validate_worker_result(result: Any, state: dict[str, Any], mandate: dict[str, Any]) -> None:
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

    if receipt.get("artifact_refs") != artifact_refs:
        raise ValueError("worker receipt.artifact_refs must match worker artifact_refs")

    expected_receipt_path = f"receipts/{receipt['receipt_id']}.json"
    patch_receipt = state_patch.get("last_receipt")
    if not isinstance(patch_receipt, dict) or patch_receipt.get("path") != expected_receipt_path:
        raise ValueError(
            "worker state_patch.last_receipt.path must match receipt path "
            f"({expected_receipt_path})"
        )


def render_text_result(payload: dict[str, Any]) -> str:
    lines = ["advance-campaign: OK" if payload["ok"] else "advance-campaign: FAIL"]
    lines.append(f"campaign_dir: {payload['campaign_dir']}")
    lines.append(f"changed: {payload['changed']}")
    lines.append(f"phase: {payload['phase_before']} -> {payload['phase_after']}")
    lines.append(f"status: {payload['status_before']} -> {payload['status_after']}")

    if payload.get("receipt_path"):
        lines.append(f"receipt: {payload['receipt_path']}")
    if payload.get("message"):
        lines.append(f"message: {payload['message']}")
    if payload.get("errors"):
        lines.append("errors:")
        for error in payload["errors"]:
            lines.append(f"- {error}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Advance one campaign by one bounded dispatcher step.")
    parser.add_argument("campaign", help="Campaign id under campaigns/ or path to campaign directory")
    parser.add_argument(
        "--campaigns-dir",
        default=None,
        help="Optional campaigns root when <campaign> is an id (defaults to <framework>/campaigns)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and simulate one step without writing files")
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
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload), file=sys.stderr)
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
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload), file=sys.stderr)
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
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload), file=sys.stderr)
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
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload), file=sys.stderr)
        return 1

    if status_before in {"BLOCKED", "OPERATOR_GATE", "CLOSED"}:
        payload = {
            "ok": True,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "message": f"campaign status is {status_before}; no bounded step executed",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload))
        return 0

    worker_context_pack = {
        "mandate": mandate,
        "campaign_state": state,
        "phase_instruction": _phase_instruction(phase_before),
        "current_item": state.get("active_item_id"),
        "receipts_tail": read_receipts_tail(receipts_dir, limit=5),
        "adapter_context": None,
    }

    result = run_stub_worker(worker_context_pack, receipt_index=next_receipt_index(receipts_dir))

    try:
        validate_worker_result(result, state=state, mandate=mandate)
    except Exception as exc:
        payload = {
            "ok": False,
            "changed": False,
            "campaign_dir": str(campaign_dir),
            "phase_before": phase_before,
            "phase_after": phase_before,
            "status_before": status_before,
            "status_after": status_before,
            "errors": [f"invalid worker result: {exc}"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload), file=sys.stderr)
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
            "errors": [f"patched campaign state invalid: {exc}"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload), file=sys.stderr)
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
            "errors": [f"receipt already exists: {receipt_path}"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload), file=sys.stderr)
        return 1

    if not args.dry_run:
        dump_json_atomic(receipt_path, receipt)
        dump_json_atomic(state_path, new_state)

    payload = {
        "ok": True,
        "changed": True,
        "dry_run": bool(args.dry_run),
        "campaign_dir": str(campaign_dir),
        "phase_before": phase_before,
        "phase_after": new_state["phase"],
        "status_before": status_before,
        "status_after": new_state["status"],
        "result_type": result["result_type"],
        "receipt_id": receipt["receipt_id"],
        "receipt_path": str(receipt_path),
        "wakeup": new_state.get("wakeup"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_text_result(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
