from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    yaml = None

TZ = ZoneInfo("Asia/Taipei")
KERNEL_REQUIRED_FIELDS = {
    "mandate_id",
    "objective",
    "adapter",
    "scope",
    "constraints",
    "authority",
    "escalation",
    "success_criteria",
    "ttl_days",
    "delivery_shape",
}
ALLOWED_ADAPTER_BUDGET_KEYS = {"cycle_budget", "back_transitions_remaining"}
WORKER_STATE_PATCH_ALLOWED_FIELDS = {
    "phase",
    "status",
    "active_item_id",
    "item_queue",
    "cycle_budget",
    "back_transitions_remaining",
    "wakeup",
    "last_receipt",
}
RECEIPT_REQUIRED_FIELDS = {
    "receipt_id",
    "campaign_id",
    "mandate_id",
    "phase",
    "event",
    "summary",
    "artifact_refs",
    "created_at",
}
CAMPAIGN_STATE_REQUIRED_FIELDS = {
    "campaign_id",
    "mandate_id",
    "phase",
    "status",
    "active_item_id",
    "item_queue",
    "cycle_budget",
    "back_transitions_remaining",
    "wakeup",
    "last_receipt",
    "updated_at",
}
VALID_PHASES = {"INTAKE", "EXPLORE", "EVALUATE", "SYNTHESIZE", "GATE", "DELIVER", "CLOSED"}
VALID_STATUSES = {"ACTIVE", "BLOCKED", "OPERATOR_GATE", "CLOSED"}
WORKER_RESULT_TYPES = {"ADVANCE", "BLOCK", "ESCALATE", "FAIL", "DELIVER"}
PHASE_TRANSITION_RULES = {
    "INTAKE": {"forward": {"EXPLORE"}, "back": set()},
    "EXPLORE": {"forward": {"EVALUATE"}, "back": set()},
    "EVALUATE": {"forward": {"SYNTHESIZE"}, "back": {"EXPLORE"}},
    "SYNTHESIZE": {"forward": {"GATE"}, "back": set()},
    "GATE": {"forward": {"DELIVER", "CLOSED"}, "back": {"EVALUATE"}},
    "DELIVER": {"forward": {"CLOSED"}, "back": set()},
    "CLOSED": {"forward": set(), "back": set()},
}
RESULT_TYPE_TRANSITION_SEMANTICS = {
    "ADVANCE": {"forward", "back"},
    "BLOCK": {"retry"},
    "ESCALATE": {"retry", "forward", "back"},
    "FAIL": {"retry", "back", "forward"},
    "DELIVER": {"forward"},
}
DEFAULT_PHASE = "INTAKE"
DEFAULT_STATUS = "ACTIVE"
DEFAULT_CYCLE_BUDGET = 8
DEFAULT_BACK_TRANSITIONS = 1


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]
    mandate: dict[str, Any] | None = None
    framework_root: Path | None = None


def framework_root_from_script(script_path: str | Path) -> Path:
    return Path(script_path).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(tz=TZ).isoformat(timespec="seconds")


def _ensure_pyyaml() -> Any:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required for mandate runtime tools. Install with: python3 -m pip install pyyaml"
        )
    return yaml


def _is_iso_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def load_yaml(path: Path) -> Any:
    parser = _ensure_pyyaml()
    text = path.read_text(encoding="utf-8")
    data = parser.safe_load(text)
    if data is None:
        return {}
    return data


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def dump_json_atomic(path: Path, data: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    dump_json(tmp_path, data)
    tmp_path.replace(path)


def validate_mandate_file(path: Path, framework_root: Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not path.exists():
        return ValidationResult(False, [f"mandate file not found: {path}"], [], None, framework_root)

    try:
        data = load_yaml(path)
    except Exception as exc:
        return ValidationResult(False, [f"failed to parse YAML: {exc}"], [], None, framework_root)

    if not isinstance(data, dict):
        return ValidationResult(False, ["mandate must be a YAML mapping/object"], [], None, framework_root)

    missing = sorted(KERNEL_REQUIRED_FIELDS - set(data.keys()))
    if missing:
        errors.append(f"missing required kernel fields: {', '.join(missing)}")

    mandate_id = data.get("mandate_id")
    if not isinstance(mandate_id, str) or not mandate_id.strip():
        errors.append("mandate_id must be a non-empty string")
    elif not re.fullmatch(r"[a-zA-Z0-9._-]+", mandate_id):
        errors.append("mandate_id must match [a-zA-Z0-9._-]+")

    objective = data.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        errors.append("objective must be a non-empty string")

    adapter = data.get("adapter")
    if not isinstance(adapter, str) or not adapter.strip():
        errors.append("adapter must be a non-empty string")
    else:
        adapter_dir = framework_root / "adapters" / adapter
        if not adapter_dir.exists() or not adapter_dir.is_dir():
            errors.append(f"adapter directory not found: adapters/{adapter}")

    scope = data.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be a mapping/object")
    else:
        for key in ("in", "out"):
            if key in scope and not isinstance(scope[key], list):
                errors.append(f"scope.{key} must be a list when present")

    if not isinstance(data.get("constraints"), dict):
        errors.append("constraints must be a mapping/object")

    authority = data.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority must be a mapping/object")
    else:
        autonomous = authority.get("autonomous")
        requires_gate = authority.get("requires_gate")
        if not isinstance(autonomous, list) or not autonomous:
            errors.append("authority.autonomous must be a non-empty list")
        if not isinstance(requires_gate, list) or not requires_gate:
            errors.append("authority.requires_gate must be a non-empty list")

    escalation = data.get("escalation")
    if not isinstance(escalation, dict):
        errors.append("escalation must be a mapping/object")
    else:
        gate_conditions = escalation.get("gate_conditions")
        timeout_days = escalation.get("operator_gate_timeout_days")
        if not isinstance(gate_conditions, list) or not gate_conditions:
            errors.append("escalation.gate_conditions must be a non-empty list")
        if not isinstance(timeout_days, int) or timeout_days <= 0:
            errors.append("escalation.operator_gate_timeout_days must be a positive integer")

    success = data.get("success_criteria")
    if not isinstance(success, list) or not success:
        errors.append("success_criteria must be a non-empty list")

    ttl_days = data.get("ttl_days")
    if not isinstance(ttl_days, int) or ttl_days <= 0:
        errors.append("ttl_days must be a positive integer")

    delivery_shape = data.get("delivery_shape")
    if not isinstance(delivery_shape, str) or not delivery_shape.strip():
        errors.append("delivery_shape must be a non-empty string")

    extra_fields = sorted(set(data.keys()) - KERNEL_REQUIRED_FIELDS)
    if extra_fields:
        warnings.append(
            "opaque adapter/root extension fields present (not kernel-validated): " + ", ".join(extra_fields)
        )

    return ValidationResult(not errors, errors, warnings, data, framework_root)


def load_adapter_defaults(framework_root: Path, adapter: str) -> dict[str, int]:
    defaults_path = framework_root / "adapters" / adapter / "defaults.yaml"
    if not defaults_path.exists():
        return {}
    data = load_yaml(defaults_path)
    if not isinstance(data, dict):
        raise ValueError(f"adapter defaults must be a mapping: {defaults_path}")
    unknown = set(data.keys()) - ALLOWED_ADAPTER_BUDGET_KEYS
    if unknown:
        raise ValueError(
            f"adapter defaults may only override {sorted(ALLOWED_ADAPTER_BUDGET_KEYS)}; got {sorted(unknown)}"
        )
    for key, value in data.items():
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"adapter default {key} must be a non-negative integer")
    return data


def build_initial_state(mandate: dict[str, Any], adapter_defaults: dict[str, int]) -> dict[str, Any]:
    return {
        "campaign_id": mandate["mandate_id"],
        "mandate_id": mandate["mandate_id"],
        "phase": DEFAULT_PHASE,
        "status": DEFAULT_STATUS,
        "active_item_id": None,
        "item_queue": [],
        "cycle_budget": adapter_defaults.get("cycle_budget", DEFAULT_CYCLE_BUDGET),
        "back_transitions_remaining": adapter_defaults.get(
            "back_transitions_remaining", DEFAULT_BACK_TRANSITIONS
        ),
        "wakeup": {"needed": False, "reason": None},
        "last_receipt": {
            "path": "receipts/000_campaign_created.json",
            "summary": "campaign initialized from validated mandate",
        },
        "updated_at": now_iso(),
    }


def build_initial_receipt(mandate: dict[str, Any]) -> dict[str, Any]:
    return {
        "receipt_id": "000_campaign_created",
        "campaign_id": mandate["mandate_id"],
        "mandate_id": mandate["mandate_id"],
        "phase": DEFAULT_PHASE,
        "event": "campaign_created",
        "summary": "campaign initialized from validated mandate",
        "artifact_refs": ["MANDATE.yaml", "CAMPAIGN_STATE.json"],
        "created_at": now_iso(),
    }


def validate_campaign_state(state: Any) -> list[str]:
    if not isinstance(state, dict):
        return ["campaign state must be a JSON object"]

    errors: list[str] = []
    missing = sorted(CAMPAIGN_STATE_REQUIRED_FIELDS - set(state.keys()))
    if missing:
        errors.append(f"campaign state missing required fields: {', '.join(missing)}")

    campaign_id = state.get("campaign_id")
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        errors.append("campaign_state.campaign_id must be a non-empty string")

    mandate_id = state.get("mandate_id")
    if not isinstance(mandate_id, str) or not mandate_id.strip():
        errors.append("campaign_state.mandate_id must be a non-empty string")

    phase = state.get("phase")
    if not isinstance(phase, str) or phase not in VALID_PHASES:
        errors.append(f"campaign_state.phase must be one of {sorted(VALID_PHASES)}")

    status = state.get("status")
    if not isinstance(status, str) or status not in VALID_STATUSES:
        errors.append(f"campaign_state.status must be one of {sorted(VALID_STATUSES)}")

    active_item_id = state.get("active_item_id")
    if active_item_id is not None and not isinstance(active_item_id, str):
        errors.append("campaign_state.active_item_id must be null or string")

    if not isinstance(state.get("item_queue"), list):
        errors.append("campaign_state.item_queue must be a list")

    for budget_key in ("cycle_budget", "back_transitions_remaining"):
        value = state.get(budget_key)
        if not isinstance(value, int) or value < 0:
            errors.append(f"campaign_state.{budget_key} must be a non-negative integer")

    wakeup = state.get("wakeup")
    errors.extend(_validate_wakeup_shape(wakeup, "campaign_state.wakeup"))

    last_receipt = state.get("last_receipt")
    errors.extend(_validate_last_receipt_shape(last_receipt, "campaign_state.last_receipt"))

    if not _is_iso_datetime(state.get("updated_at")):
        errors.append("campaign_state.updated_at must be an ISO datetime string")

    return errors


def _validate_wakeup_shape(value: Any, field_name: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{field_name} must be an object"]
    if not isinstance(value.get("needed"), bool):
        errors.append(f"{field_name}.needed must be boolean")
    reason = value.get("reason")
    if reason is not None and not isinstance(reason, str):
        errors.append(f"{field_name}.reason must be null or string")
    return errors


def _validate_last_receipt_shape(value: Any, field_name: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{field_name} must be an object"]
    path = value.get("path")
    summary = value.get("summary")
    if path is not None and not isinstance(path, str):
        errors.append(f"{field_name}.path must be null or string")
    if not isinstance(summary, str) or not summary.strip():
        errors.append(f"{field_name}.summary must be a non-empty string")
    return errors


def ensure_valid_campaign_state(state: Any) -> None:
    errors = validate_campaign_state(state)
    if errors:
        raise ValueError("; ".join(errors))


def validate_worker_state_patch(patch: Any) -> list[str]:
    if not isinstance(patch, dict):
        return ["worker state_patch must be an object"]

    errors: list[str] = []
    if not patch:
        errors.append("worker state_patch must not be empty")

    unknown = sorted(set(patch.keys()) - WORKER_STATE_PATCH_ALLOWED_FIELDS)
    if unknown:
        errors.append(
            "worker state_patch contains disallowed keys: "
            + ", ".join(unknown)
            + f" (allowed: {sorted(WORKER_STATE_PATCH_ALLOWED_FIELDS)})"
        )

    if "phase" in patch:
        phase = patch["phase"]
        if not isinstance(phase, str) or phase not in VALID_PHASES:
            errors.append(f"worker state_patch.phase must be one of {sorted(VALID_PHASES)}")

    if "status" in patch:
        status = patch["status"]
        if not isinstance(status, str) or status not in VALID_STATUSES:
            errors.append(f"worker state_patch.status must be one of {sorted(VALID_STATUSES)}")

    if "active_item_id" in patch:
        active_item_id = patch["active_item_id"]
        if active_item_id is not None and not isinstance(active_item_id, str):
            errors.append("worker state_patch.active_item_id must be null or string")

    if "item_queue" in patch and not isinstance(patch["item_queue"], list):
        errors.append("worker state_patch.item_queue must be a list")

    for budget_key in ("cycle_budget", "back_transitions_remaining"):
        if budget_key in patch:
            value = patch[budget_key]
            if not isinstance(value, int) or value < 0:
                errors.append(f"worker state_patch.{budget_key} must be a non-negative integer")

    if "wakeup" in patch:
        errors.extend(_validate_wakeup_shape(patch["wakeup"], "worker state_patch.wakeup"))

    if "last_receipt" in patch:
        errors.extend(
            _validate_last_receipt_shape(patch["last_receipt"], "worker state_patch.last_receipt")
        )

    return errors


def ensure_valid_worker_state_patch(patch: Any) -> None:
    errors = validate_worker_state_patch(patch)
    if errors:
        raise ValueError("; ".join(errors))


def classify_phase_transition(before_phase: str, after_phase: str) -> str | None:
    if before_phase == after_phase:
        return "retry"

    rules = PHASE_TRANSITION_RULES.get(before_phase)
    if not rules:
        return None

    if after_phase in rules["forward"]:
        return "forward"
    if after_phase in rules["back"]:
        return "back"
    return None


def validate_phase_transition_semantics(
    *,
    previous_state: dict[str, Any],
    state_patch: dict[str, Any],
    result_type: str,
) -> list[str]:
    errors: list[str] = []

    before_phase = previous_state.get("phase")
    after_phase = state_patch.get("phase", before_phase)
    after_status = state_patch.get("status", previous_state.get("status"))

    transition_kind = classify_phase_transition(before_phase, after_phase)
    if transition_kind is None:
        return [f"invalid phase transition: {before_phase} -> {after_phase}"]

    allowed = RESULT_TYPE_TRANSITION_SEMANTICS.get(result_type, set())
    if transition_kind not in allowed:
        errors.append(
            f"worker result_type={result_type} disallows {transition_kind} transition ({before_phase} -> {after_phase})"
        )

    if result_type == "BLOCK" and after_status != "BLOCKED":
        errors.append("BLOCK results must set state_patch.status=BLOCKED")

    if result_type == "ESCALATE":
        if after_status != "OPERATOR_GATE":
            errors.append("ESCALATE results must set state_patch.status=OPERATOR_GATE")
        if after_phase not in {before_phase, "GATE"}:
            errors.append("ESCALATE results may only keep phase or move phase to GATE")

    if result_type == "DELIVER" and after_phase not in {"DELIVER", "CLOSED"}:
        errors.append("DELIVER results must move phase to DELIVER or CLOSED")

    if result_type == "FAIL" and transition_kind == "forward" and after_phase != "CLOSED":
        errors.append("FAIL results may only forward-transition to CLOSED")

    if after_phase == "CLOSED" and after_status != "CLOSED":
        errors.append("phase CLOSED requires state_patch.status=CLOSED")

    back_budget_before = previous_state.get("back_transitions_remaining")
    if isinstance(back_budget_before, int):
        if transition_kind == "back":
            if back_budget_before <= 0:
                errors.append("phase back-transition requires positive back_transitions_remaining budget")
            back_budget_after = state_patch.get("back_transitions_remaining")
            if back_budget_after is None:
                errors.append(
                    "phase back-transition must include state_patch.back_transitions_remaining decrement"
                )
            elif back_budget_after != back_budget_before - 1:
                errors.append(
                    "phase back-transition must decrement back_transitions_remaining by exactly 1 "
                    f"(before={back_budget_before}, after={back_budget_after})"
                )
        elif "back_transitions_remaining" in state_patch:
            if state_patch["back_transitions_remaining"] != back_budget_before:
                errors.append("back_transitions_remaining may only change during a back-transition")

    return errors


def ensure_valid_phase_transition_semantics(
    *,
    previous_state: dict[str, Any],
    state_patch: dict[str, Any],
    result_type: str,
) -> None:
    errors = validate_phase_transition_semantics(
        previous_state=previous_state,
        state_patch=state_patch,
        result_type=result_type,
    )
    if errors:
        raise ValueError("; ".join(errors))


def validate_receipt_record(
    receipt: Any,
    expected_campaign_id: str | None = None,
    expected_mandate_id: str | None = None,
) -> list[str]:
    if not isinstance(receipt, dict):
        return ["receipt must be an object"]

    errors: list[str] = []
    missing = sorted(RECEIPT_REQUIRED_FIELDS - set(receipt.keys()))
    if missing:
        errors.append(f"receipt missing required fields: {', '.join(missing)}")

    for field in ("receipt_id", "campaign_id", "mandate_id", "event", "summary"):
        value = receipt.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"receipt.{field} must be a non-empty string")

    phase = receipt.get("phase")
    if not isinstance(phase, str) or phase not in VALID_PHASES:
        errors.append(f"receipt.phase must be one of {sorted(VALID_PHASES)}")

    artifact_refs = receipt.get("artifact_refs")
    if not isinstance(artifact_refs, list):
        errors.append("receipt.artifact_refs must be a list")
    else:
        if any(not isinstance(item, str) or not item.strip() for item in artifact_refs):
            errors.append("receipt.artifact_refs must only contain non-empty strings")

    if not _is_iso_datetime(receipt.get("created_at")):
        errors.append("receipt.created_at must be an ISO datetime string")

    if expected_campaign_id and receipt.get("campaign_id") != expected_campaign_id:
        errors.append(
            f"receipt.campaign_id mismatch: expected {expected_campaign_id}, got {receipt.get('campaign_id')}"
        )

    if expected_mandate_id and receipt.get("mandate_id") != expected_mandate_id:
        errors.append(
            f"receipt.mandate_id mismatch: expected {expected_mandate_id}, got {receipt.get('mandate_id')}"
        )

    return errors


def ensure_valid_receipt_record(
    receipt: Any,
    expected_campaign_id: str | None = None,
    expected_mandate_id: str | None = None,
) -> None:
    errors = validate_receipt_record(receipt, expected_campaign_id, expected_mandate_id)
    if errors:
        raise ValueError("; ".join(errors))


def apply_state_patch(state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    updated = dict(state)
    updated.update(patch)
    updated["updated_at"] = now_iso()
    return updated


def next_receipt_index(receipts_dir: Path) -> int:
    max_index = -1
    for path in receipts_dir.glob("*.json"):
        match = re.match(r"^(\d{3})_", path.name)
        if not match:
            continue
        max_index = max(max_index, int(match.group(1)))
    return max_index + 1


def format_receipt_id(index: int, event: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", event.lower()).strip("_")
    slug = slug or "event"
    return f"{index:03d}_{slug}"


def list_receipt_files(receipts_dir: Path) -> list[Path]:
    if not receipts_dir.exists() or not receipts_dir.is_dir():
        return []
    return sorted(path for path in receipts_dir.iterdir() if path.suffix == ".json")


def read_receipts_tail(receipts_dir: Path, limit: int = 5) -> list[dict[str, Any]]:
    files = list_receipt_files(receipts_dir)
    if limit >= 0:
        files = files[-limit:] if limit > 0 else []

    out: list[dict[str, Any]] = []
    for path in files:
        payload = load_json(path)
        if isinstance(payload, dict):
            payload = dict(payload)
            payload["_path"] = str(path)
            out.append(payload)
    return out
