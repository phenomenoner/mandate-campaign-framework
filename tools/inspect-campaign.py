#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from _runtime_lib import (
    ensure_valid_campaign_state,
    framework_root_from_script,
    list_receipt_files,
    load_json,
    load_yaml,
    validate_mandate_file,
    validate_receipt_record,
)


def resolve_campaign_dir(framework_root: Path, campaign_arg: str, campaigns_dir_arg: str | None) -> Path:
    candidate = Path(campaign_arg)
    if candidate.exists():
        return candidate.resolve()

    campaigns_root = Path(campaigns_dir_arg).resolve() if campaigns_dir_arg else framework_root / "campaigns"
    return (campaigns_root / campaign_arg).resolve()


def render_text_report(payload: dict[str, Any], receipt_preview_limit: int) -> str:
    lines: list[str] = []
    lines.append("inspect-campaign: OK" if payload["ok"] else "inspect-campaign: FAIL")
    lines.append(f"campaign_dir: {payload['campaign_dir']}")

    if payload.get("state"):
        state = payload["state"]
        lines.append(f"campaign_id: {state.get('campaign_id')}")
        lines.append(f"mandate_id: {state.get('mandate_id')}")
        lines.append(f"adapter: {payload.get('adapter')}")
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

        last_receipt = state.get("last_receipt", {})
        lines.append(
            "last_receipt: "
            f"path={last_receipt.get('path')} summary={last_receipt.get('summary')}"
        )

    lines.append(f"receipts_total: {payload['receipts_total']}")

    preview = payload.get("receipts_preview", [])
    if preview:
        lines.append(f"receipts_preview(last {receipt_preview_limit}):")
        for item in preview:
            lines.append(
                "- "
                + " | ".join(
                    [
                        str(item.get("receipt_id")),
                        str(item.get("phase")),
                        str(item.get("event")),
                        str(item.get("summary")),
                        str(item.get("created_at")),
                    ]
                )
            )

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
            }
            receipts_preview.append(receipt_preview)

        if isinstance(state_data, dict):
            last_receipt = state_data.get("last_receipt")
            if isinstance(last_receipt, dict) and isinstance(last_receipt.get("path"), str):
                expected_last = campaign_dir / last_receipt["path"]
                if not expected_last.exists():
                    warnings.append(
                        "state last_receipt path does not exist on disk: "
                        f"{last_receipt['path']}"
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

    payload = {
        "ok": not errors,
        "campaign_dir": str(campaign_dir),
        "adapter": mandate_data.get("adapter") if isinstance(mandate_data, dict) else None,
        "state": state_data,
        "receipts_total": len(receipt_files),
        "receipts_preview": receipts_preview,
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
