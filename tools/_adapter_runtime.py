from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from _runtime_lib import format_receipt_id, now_iso

PHASE_FORWARD_DEFAULT = {
    "INTAKE": "EXPLORE",
    "EXPLORE": "EVALUATE",
    "EVALUATE": "SYNTHESIZE",
    "SYNTHESIZE": "GATE",
    "GATE": "DELIVER",
    "DELIVER": "CLOSED",
}

STEAMER_PHASE_MAP = {
    "INTAKE": "mandate-intake",
    "EXPLORE": "idea-scout",
    "EVALUATE": "fast-triage+deep-validation",
    "SYNTHESIZE": "card-synthesis+shadow-packaging",
    "GATE": "operator-gate",
    "DELIVER": "shadow-reviewable-packet",
    "CLOSED": "campaign-closed",
}
OPENCLAW_MEM_PHASE_MAP = {
    "INTAKE": "source-signal-intake",
    "EXPLORE": "failure-clustering",
    "EVALUATE": "root-cause-packaging",
    "SYNTHESIZE": "next-experiment-proposal",
    "GATE": "operator-decision-packet",
    "DELIVER": "dev-decision-packet",
    "CLOSED": "campaign-closed",
}
STEAMER_PHASES_REQUIRING_ACTIVE_ITEM = {"EVALUATE", "SYNTHESIZE", "GATE", "DELIVER"}

WorkerContextPack = dict[str, Any]
WorkerResult = dict[str, Any]
MandateNormalizer = Callable[[dict[str, Any]], dict[str, Any]]
ContextEnricher = Callable[[WorkerContextPack], dict[str, Any] | None]
WorkerCallable = Callable[[WorkerContextPack, int], WorkerResult]
InspectHook = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None]


@dataclass(frozen=True)
class RuntimeAdapter:
    adapter_id: str
    display_name: str
    worker: WorkerCallable
    normalize_mandate: MandateNormalizer | None = None
    enrich_context: ContextEnricher | None = None
    inspect_hook: InspectHook | None = None


class AdapterResolutionError(ValueError):
    pass


def _default_normalize_mandate(mandate: dict[str, Any]) -> dict[str, Any]:
    return mandate


def _dedupe_items(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        deduped.append(item)
        seen.add(item)
    return deduped


def _queue_with_selected(queue: list[str], selected: str | None) -> list[str]:
    clean_queue = [item for item in queue if isinstance(item, str) and item.strip()]
    if isinstance(selected, str) and selected.strip():
        clean_queue = [selected, *clean_queue]
    return _dedupe_items(clean_queue)


def _steamer_work_item_context(
    *,
    selected_item: str | None,
    selection_reason: str,
    decision: str,
    queue_before: list[str],
    queue_after: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": selected_item,
        "selection_reason": selection_reason,
        "decision": decision,
        "queue_before_len": len(queue_before),
        "queue_after_len": len(queue_after),
        "queue_before_head": queue_before[0] if queue_before else None,
        "queue_after_head": queue_after[0] if queue_after else None,
    }
    if isinstance(extra, dict):
        payload.update(extra)
    return payload


def _steamer_queue_artifact(
    *,
    phase: str,
    selected_item: str | None,
    item_queue: list[str],
    selection_reason: str,
) -> dict[str, Any]:
    return {
        "path": "artifacts/steamer/candidate-queue.json",
        "payload": {
            "phase": phase,
            "active_item_id": selected_item,
            "item_queue": item_queue,
            "selection_reason": selection_reason,
            "updated_at": now_iso(),
        },
        "summary": "candidate queue snapshot",
    }


def _steamer_trace_artifact(
    *,
    receipt_index: int,
    event: str,
    phase_before: str,
    phase_after: str,
    status_before: str,
    status_after: str,
    summary: str,
    work_item_context: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "path": f"artifacts/steamer/shadow-proof/{receipt_index:03d}_{event}.json",
        "payload": {
            "event": event,
            "phase_before": phase_before,
            "phase_after": phase_after,
            "status_before": status_before,
            "status_after": status_after,
            "summary": summary,
            "work_item": work_item_context,
            "created_at": now_iso(),
        },
        "summary": "shadow-proof step trace",
    }


def _steamer_idea_scout_note_artifact(
    *,
    selected_item: str,
    mandate_id: str,
    selection_reason: str,
) -> dict[str, Any]:
    content = "\n".join(
        [
            f"# Steamer idea-scout note — {selected_item}",
            "",
            f"- mandate_id: {mandate_id}",
            "- phase: EXPLORE",
            f"- selection_reason: {selection_reason}",
            "- scout_disposition: move candidate to EVALUATE for bounded fast-triage",
            "- evidence_stub: waiting for replay/backtest evidence in follow-up phase",
            "",
        ]
    )
    return {
        "path": f"artifacts/steamer/idea-scout/{selected_item}.md",
        "format": "text",
        "content": content,
        "summary": "idea-scout domain note",
    }


def _steamer_gate_replay_artifact(
    *,
    receipt_index: int,
    selected_item: str,
    decision: str,
    note: str | None,
    phase_after: str,
    status_after: str,
) -> dict[str, Any]:
    return {
        "path": (
            "artifacts/steamer/gate-replay/"
            f"{receipt_index:03d}_{selected_item}_{decision}.json"
        ),
        "payload": {
            "candidate_id": selected_item,
            "operator_decision": decision,
            "operator_note": note,
            "phase_before": "GATE",
            "status_before": "OPERATOR_GATE",
            "phase_after": phase_after,
            "status_after": status_after,
            "recorded_at": now_iso(),
        },
        "summary": "operator gate decision replay receipt",
    }


def _build_result(
    *,
    result_type: str,
    context_pack: WorkerContextPack,
    receipt_index: int,
    event: str,
    summary: str,
    artifact_refs: list[str],
    phase_for_receipt: str,
    state_patch: dict[str, Any],
    wakeup: dict[str, Any] | None,
    next_phase_hint: str,
    work_item_context: dict[str, Any] | None = None,
    artifact_materializations: list[dict[str, Any]] | None = None,
) -> WorkerResult:
    state = context_pack["campaign_state"]
    mandate = context_pack["mandate"]
    receipt_id = format_receipt_id(receipt_index, event)
    receipt_rel_path = f"receipts/{receipt_id}.json"

    normalized_materializations: list[dict[str, Any]] = []
    materialized_paths: list[str] = []
    for item in artifact_materializations or []:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            continue

        format_value = item.get("format", "json")
        if not isinstance(format_value, str) or not format_value.strip():
            continue
        materialization_format = format_value.strip().lower()
        if materialization_format not in {"json", "text"}:
            continue

        normalized = {
            "path": path.strip(),
            "format": materialization_format,
        }
        if materialization_format == "text":
            content = item.get("content")
            if not isinstance(content, str) or not content.strip():
                continue
            normalized["content"] = content
        else:
            normalized["payload"] = item.get("payload")

        summary_field = item.get("summary")
        if isinstance(summary_field, str) and summary_field.strip():
            normalized["summary"] = summary_field.strip()
        normalized_materializations.append(normalized)
        materialized_paths.append(normalized["path"])

    artifact_refs_full = _dedupe_items([*artifact_refs, *materialized_paths])

    patch = dict(state_patch)
    patch["last_receipt"] = {"path": receipt_rel_path, "summary": summary}
    patch["wakeup"] = wakeup if wakeup is not None else {"needed": False, "reason": None}

    receipt_payload = {
        "receipt_id": receipt_id,
        "campaign_id": state["campaign_id"],
        "mandate_id": mandate["mandate_id"],
        "phase": phase_for_receipt,
        "event": event,
        "summary": summary,
        "artifact_refs": artifact_refs_full,
        "created_at": now_iso(),
    }
    if isinstance(work_item_context, dict):
        receipt_payload["work_item"] = work_item_context

    return {
        "result_type": result_type,
        "artifact_refs": artifact_refs_full,
        "state_patch": patch,
        "receipt": receipt_payload,
        "artifact_materializations": normalized_materializations,
        "next_phase_hint": next_phase_hint,
        "wakeup": patch["wakeup"],
    }


def _cycle_budget_block(
    context_pack: WorkerContextPack,
    receipt_index: int,
    *,
    adapter_id: str,
    dispatch_path: str,
) -> WorkerResult:
    state = context_pack["campaign_state"]
    current_phase = state["phase"]
    summary = (
        f"campaign blocked: cycle budget exhausted "
        f"(dispatch={dispatch_path}, adapter={adapter_id})"
    )
    return _build_result(
        result_type="BLOCK",
        context_pack=context_pack,
        receipt_index=receipt_index,
        event="cycle_budget_exhausted",
        summary=summary,
        artifact_refs=["CAMPAIGN_STATE.json"],
        phase_for_receipt=current_phase,
        state_patch={"status": "BLOCKED"},
        wakeup={"needed": True, "reason": "cycle_budget_exhausted"},
        next_phase_hint=current_phase,
    )


def run_linear_phase_worker(
    context_pack: WorkerContextPack,
    receipt_index: int,
    *,
    adapter_id: str,
    dispatch_path: str,
) -> WorkerResult:
    state = context_pack["campaign_state"]
    current_phase = state["phase"]

    if state["cycle_budget"] <= 0 and current_phase not in {"DELIVER", "CLOSED"}:
        return _cycle_budget_block(
            context_pack,
            receipt_index,
            adapter_id=adapter_id,
            dispatch_path=dispatch_path,
        )

    next_phase = PHASE_FORWARD_DEFAULT.get(current_phase, "CLOSED")
    next_status = "CLOSED" if next_phase == "CLOSED" else "ACTIVE"
    wakeup = {"needed": False, "reason": None}
    if next_phase == "DELIVER":
        wakeup = {"needed": True, "reason": "delivery_ready"}

    summary = (
        f"advanced campaign one bounded step: {current_phase} -> {next_phase} "
        f"(dispatch={dispatch_path}, adapter={adapter_id})"
    )
    return _build_result(
        result_type="DELIVER" if next_phase == "DELIVER" else "ADVANCE",
        context_pack=context_pack,
        receipt_index=receipt_index,
        event=f"phase_advanced_{current_phase.lower()}_to_{next_phase.lower()}",
        summary=summary,
        artifact_refs=["CAMPAIGN_STATE.json"],
        phase_for_receipt=next_phase,
        state_patch={
            "phase": next_phase,
            "status": next_status,
            "cycle_budget": max(0, state["cycle_budget"] - 1),
        },
        wakeup=wakeup,
        next_phase_hint=next_phase,
    )



def _openclaw_mem_work_item_context(
    *,
    selected_item: str | None,
    selection_reason: str,
    decision: str,
    queue_before: list[str],
    queue_after: list[str],
    phase_map: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": selected_item,
        "selection_reason": selection_reason,
        "decision": decision,
        "phase_map": phase_map,
        "queue_before_len": len(queue_before),
        "queue_after_len": len(queue_after),
        "queue_before_head": queue_before[0] if queue_before else None,
        "queue_after_head": queue_after[0] if queue_after else None,
    }
    if isinstance(extra, dict):
        payload.update(extra)
    return payload


def _openclaw_mem_trace_artifact(
    *,
    receipt_index: int,
    event: str,
    phase_before: str,
    phase_after: str,
    status_before: str,
    status_after: str,
    summary: str,
    work_item_context: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "path": f"artifacts/openclaw-mem/trace/{receipt_index:03d}_{event}.json",
        "payload": {
            "event": event,
            "phase_before": phase_before,
            "phase_after": phase_after,
            "status_before": status_before,
            "status_after": status_after,
            "summary": summary,
            "work_item": work_item_context,
            "created_at": now_iso(),
        },
        "summary": "openclaw-mem step trace",
    }


def _openclaw_mem_likely_pointer(value: str) -> bool:
    lowered = value.lower()
    return (
        "/" in value
        or value.startswith(".")
        or value.startswith("~")
        or value.startswith("/")
        or lowered.endswith((".md", ".json", ".yaml", ".yml", ".txt", ".log"))
    )


def _openclaw_mem_collect_source_pointers(mandate: dict[str, Any]) -> list[str]:
    pointers: list[str] = []
    scope = mandate.get("scope")
    if isinstance(scope, dict):
        scope_in = scope.get("in")
        if isinstance(scope_in, list):
            for item in scope_in:
                if isinstance(item, str) and item.strip() and _openclaw_mem_likely_pointer(item.strip()):
                    pointers.append(item.strip())

    work_items = mandate.get("work_items")
    if isinstance(work_items, list):
        for item in work_items:
            if isinstance(item, str):
                value = item.strip()
                if value and _openclaw_mem_likely_pointer(value):
                    pointers.append(value)
            elif isinstance(item, dict):
                for raw_value in item.values():
                    if not isinstance(raw_value, str):
                        continue
                    value = raw_value.strip()
                    if not value or value.startswith("<fill:"):
                        continue
                    if _openclaw_mem_likely_pointer(value):
                        pointers.append(value)

    deduped = _dedupe_items(pointers)
    constraints = mandate.get("constraints")
    max_items = 20
    if isinstance(constraints, dict):
        raw_max_items = constraints.get("max_cluster_items")
        if isinstance(raw_max_items, int) and raw_max_items > 0:
            max_items = raw_max_items
    return deduped[:max_items]


def _openclaw_mem_read_pointer_snapshot(pointer: str) -> dict[str, Any]:
    raw_pointer = pointer.strip()
    path = Path(raw_pointer).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()

    file_exists = path.exists() and path.is_file()
    sample_lines: list[str] = []
    keyword_hits: dict[str, int] = {}
    signal_keywords = (
        "error",
        "fail",
        "blocked",
        "hold",
        "timeout",
        "drift",
        "regression",
        "missing",
        "insufficient",
        "evidence",
        "proposal",
        "action",
        "gate",
    )

    if file_exists:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
        if text:
            non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
            sample_lines = non_empty_lines[:6]
            lowered = text.lower()
            for keyword in signal_keywords:
                count = lowered.count(keyword)
                if count > 0:
                    keyword_hits[keyword] = count

    return {
        "pointer": raw_pointer,
        "resolved_path": str(path),
        "file_exists": file_exists,
        "sample_lines": sample_lines,
        "keyword_hits": keyword_hits,
        "keyword_hit_total": sum(keyword_hits.values()),
    }


def _openclaw_mem_signal_pack(mandate: dict[str, Any]) -> dict[str, Any]:
    source_pointers = _openclaw_mem_collect_source_pointers(mandate)
    snapshots = [_openclaw_mem_read_pointer_snapshot(pointer) for pointer in source_pointers]

    clusters: list[dict[str, Any]] = []
    for index, snapshot in enumerate(snapshots, start=1):
        top_signals = sorted(
            snapshot["keyword_hits"].items(),
            key=lambda pair: pair[1],
            reverse=True,
        )[:3]
        clusters.append(
            {
                "cluster_id": f"m1-cluster-{index:02d}",
                "source_pointer": snapshot["pointer"],
                "resolved_path": snapshot["resolved_path"],
                "file_exists": snapshot["file_exists"],
                "observed_signals": [name for name, _ in top_signals],
                "sample_lines": snapshot["sample_lines"][:3],
            }
        )

    existing_count = sum(1 for item in snapshots if item["file_exists"])
    hit_count = sum(1 for item in snapshots if item["keyword_hit_total"] > 0)

    root_cause_candidates: list[dict[str, Any]] = [
        {
            "candidate_id": "rc-01-pointer-structure",
            "hypothesis": "source pointers are too coarse and need bounded per-phase packet artifacts",
            "confidence": "high" if existing_count >= 3 else "medium",
            "evidence_refs": [item["pointer"] for item in snapshots[:2]],
        },
        {
            "candidate_id": "rc-02-traceability-gap",
            "hypothesis": "phase receipts need explicit failure-cluster to proposal linkage for operator decisions",
            "confidence": "high" if hit_count >= 2 else "medium",
            "evidence_refs": [item["pointer"] for item in snapshots[1:3]],
        },
        {
            "candidate_id": "rc-03-gate-threshold-proof",
            "hypothesis": "packet-depth + actionability thresholds need explicit proof artifacts in the run bundle",
            "confidence": "medium",
            "evidence_refs": [item["pointer"] for item in snapshots[-2:]],
        },
    ]

    constraints = mandate.get("constraints")
    max_root_causes = 3
    if isinstance(constraints, dict):
        raw_max_root_causes = constraints.get("max_root_cause_candidates")
        if isinstance(raw_max_root_causes, int) and raw_max_root_causes > 0:
            max_root_causes = raw_max_root_causes
    root_cause_candidates = root_cause_candidates[:max_root_causes]

    proposal_actionability = "high" if existing_count >= 3 and hit_count >= 2 else "medium"
    proposal_acceptance = "accept" if proposal_actionability == "high" else "defer"

    packet_depth_score = min(
        10,
        2
        + min(3, len(clusters))
        + min(2, len(root_cause_candidates))
        + (2 if proposal_actionability == "high" else 1)
        + (1 if existing_count >= 3 else 0),
    )
    if packet_depth_score >= 7:
        packet_depth_verdict = "high"
    elif packet_depth_score >= 5:
        packet_depth_verdict = "medium"
    else:
        packet_depth_verdict = "low"

    first_live_acceptance_gate = (
        "ready-for-live"
        if packet_depth_score >= 7 and packet_depth_verdict == "high" and proposal_actionability == "high"
        else "hold"
    )

    root_cause_confidence = "high" if existing_count >= 3 and hit_count >= 2 else "medium"

    proposal_packet = {
        "proposal_id": f"{mandate['mandate_id']}-next-slice-01",
        "title": "Raise SL-M1 packet depth with explicit cluster->cause->experiment trace",
        "bounded_scope": {
            "max_cluster_items": len(clusters),
            "max_root_cause_candidates": len(root_cause_candidates),
            "timebox_minutes": (constraints or {}).get("mandate_timebox_minutes", 60)
            if isinstance(constraints, dict)
            else 60,
        },
        "next_experiment": {
            "name": "run one richer SL-M1 bundle and validate ready-for-live gate",
            "steps": [
                "materialize failure-cluster brief from bounded pointers",
                "materialize root-cause candidate pack with confidence labels",
                "materialize one next-experiment proposal with expected outcome and rollback note",
                "validate telemetry summary against schema + ready-for-live acceptance rules",
            ],
            "expected_outcome": "one reviewable dev-decision packet that can be accepted without extra context stitching",
        },
        "operator_gate_recommendation": proposal_acceptance,
    }

    packet_quality = {
        "packet_depth_score": packet_depth_score,
        "packet_depth_verdict": packet_depth_verdict,
        "proposal_actionability": proposal_actionability,
        "proposal_acceptance": proposal_acceptance,
        "first_live_acceptance_gate": first_live_acceptance_gate,
        "root_cause_confidence": root_cause_confidence,
        "quality_rationale": {
            "source_pointer_count": len(source_pointers),
            "source_file_exists_count": existing_count,
            "signal_hit_pointer_count": hit_count,
            "failure_cluster_count": len(clusters),
            "root_cause_candidate_count": len(root_cause_candidates),
        },
    }

    return {
        "source_pointers": source_pointers,
        "snapshots": snapshots,
        "clusters": clusters,
        "root_cause_candidates": root_cause_candidates,
        "proposal_packet": proposal_packet,
        "packet_quality": packet_quality,
    }


def _openclaw_mem_next_experiment_markdown(mandate_id: str, signal_pack: dict[str, Any]) -> str:
    proposal_packet = signal_pack["proposal_packet"]
    packet_quality = signal_pack["packet_quality"]
    steps = proposal_packet["next_experiment"]["steps"]
    step_lines = "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    return "\n".join(
        [
            f"# openclaw-mem next experiment proposal — {mandate_id}",
            "",
            f"- proposal_id: {proposal_packet['proposal_id']}",
            f"- recommendation: {proposal_packet['operator_gate_recommendation']}",
            f"- packet_depth_score: {packet_quality['packet_depth_score']}",
            f"- packet_depth_verdict: {packet_quality['packet_depth_verdict']}",
            f"- first_live_acceptance_gate: {packet_quality['first_live_acceptance_gate']}",
            "",
            "## bounded next steps",
            step_lines,
            "",
            f"expected_outcome: {proposal_packet['next_experiment']['expected_outcome']}",
            "",
        ]
    )


def run_openclaw_mem_phase_worker(
    context_pack: WorkerContextPack,
    receipt_index: int,
) -> WorkerResult:
    state = context_pack["campaign_state"]
    mandate = context_pack["mandate"]
    current_phase = state["phase"]

    if state["cycle_budget"] <= 0 and current_phase not in {"DELIVER", "CLOSED"}:
        return _cycle_budget_block(
            context_pack,
            receipt_index,
            adapter_id="openclaw-mem",
            dispatch_path="adapter",
        )

    signal_pack = _openclaw_mem_signal_pack(mandate)

    queue_before = [item for item in state.get("item_queue", []) if isinstance(item, str) and item.strip()]
    if queue_before:
        queue_seed = queue_before
    else:
        queue_seed = [cluster["cluster_id"] for cluster in signal_pack["clusters"]]

    selected = state.get("active_item_id")
    if not isinstance(selected, str) or not selected.strip():
        selected = queue_seed[0] if queue_seed else None

    queue_after = _queue_with_selected(queue_seed, selected)
    next_phase = PHASE_FORWARD_DEFAULT.get(current_phase, "CLOSED")
    next_status = "CLOSED" if next_phase == "CLOSED" else "ACTIVE"
    wakeup = {"needed": next_phase == "DELIVER", "reason": "delivery_ready" if next_phase == "DELIVER" else None}

    selection_reason = "queue_head" if queue_before else "seeded_from_source_pointers"
    decision = f"openclaw_mem_{current_phase.lower()}"
    work_item_context = _openclaw_mem_work_item_context(
        selected_item=selected,
        selection_reason=selection_reason,
        decision=decision,
        queue_before=queue_before,
        queue_after=queue_after,
        phase_map=OPENCLAW_MEM_PHASE_MAP.get(current_phase, "unknown"),
        extra={
            "source_pointer_count": len(signal_pack["source_pointers"]),
            "failure_cluster_count": len(signal_pack["clusters"]),
        },
    )

    summary = (
        f"openclaw-mem bounded step: {current_phase} -> {next_phase} "
        f"(signals={len(signal_pack['source_pointers'])}, clusters={len(signal_pack['clusters'])})"
    )
    event = f"openclaw_mem_{current_phase.lower()}_to_{next_phase.lower()}"

    artifacts: list[dict[str, Any]] = []
    artifact_refs = ["CAMPAIGN_STATE.json"]

    if current_phase == "INTAKE":
        artifacts.append(
            {
                "path": "artifacts/openclaw-mem/mandate-intake.json",
                "payload": {
                    "mandate_id": mandate["mandate_id"],
                    "source_pointers": signal_pack["source_pointers"],
                    "cluster_seed_ids": [cluster["cluster_id"] for cluster in signal_pack["clusters"]],
                    "constraints": mandate.get("constraints"),
                    "captured_at": now_iso(),
                },
                "summary": "openclaw-mem source signal intake",
            }
        )
    elif current_phase == "EXPLORE":
        artifacts.append(
            {
                "path": "artifacts/openclaw-mem/failure-cluster.json",
                "payload": {
                    "mandate_id": mandate["mandate_id"],
                    "clusters": signal_pack["clusters"],
                    "captured_at": now_iso(),
                },
                "summary": "openclaw-mem failure cluster brief",
            }
        )
    elif current_phase == "EVALUATE":
        artifacts.append(
            {
                "path": "artifacts/openclaw-mem/root-cause-candidates.json",
                "payload": {
                    "mandate_id": mandate["mandate_id"],
                    "root_cause_candidates": signal_pack["root_cause_candidates"],
                    "captured_at": now_iso(),
                },
                "summary": "openclaw-mem root-cause candidate pack",
            }
        )
    elif current_phase == "SYNTHESIZE":
        artifacts.append(
            {
                "path": "artifacts/openclaw-mem/next-experiment-proposal.md",
                "format": "text",
                "content": _openclaw_mem_next_experiment_markdown(mandate["mandate_id"], signal_pack),
                "summary": "openclaw-mem next experiment proposal",
            }
        )
    elif current_phase == "GATE":
        artifacts.append(
            {
                "path": "artifacts/openclaw-mem/operator-gate-packet.json",
                "payload": {
                    "mandate_id": mandate["mandate_id"],
                    "proposal_packet": signal_pack["proposal_packet"],
                    "packet_quality": signal_pack["packet_quality"],
                    "captured_at": now_iso(),
                },
                "summary": "openclaw-mem operator gate packet",
            }
        )
    elif current_phase == "DELIVER":
        queue_after = []
        selected = None
        next_status = "CLOSED"
        wakeup = {"needed": False, "reason": None}
        work_item_context = dict(work_item_context)
        work_item_context["id"] = None
        work_item_context["queue_after_len"] = 0
        work_item_context["queue_after_head"] = None
        artifacts.extend(
            [
                {
                    "path": "artifacts/openclaw-mem/dev-decision-packet.json",
                    "payload": {
                        "mandate_id": mandate["mandate_id"],
                        "objective": mandate.get("objective"),
                        "source_pointers": signal_pack["source_pointers"],
                        "failure_clusters": signal_pack["clusters"],
                        "root_cause_candidates": signal_pack["root_cause_candidates"],
                        "proposal_packet": signal_pack["proposal_packet"],
                        "packet_quality": signal_pack["packet_quality"],
                        "delivered_at": now_iso(),
                    },
                    "summary": "openclaw-mem dev-decision packet",
                },
                {
                    "path": "artifacts/openclaw-mem/packet-quality-assessment.json",
                    "payload": signal_pack["packet_quality"],
                    "summary": "openclaw-mem packet-depth + readiness assessment",
                },
            ]
        )

    artifacts.append(
        _openclaw_mem_trace_artifact(
            receipt_index=receipt_index,
            event=event,
            phase_before=current_phase,
            phase_after=next_phase,
            status_before=state.get("status", "ACTIVE"),
            status_after=next_status,
            summary=summary,
            work_item_context=work_item_context,
        )
    )

    result_type = "DELIVER" if next_phase == "DELIVER" else "ADVANCE"
    artifact_refs.extend(item["path"] for item in artifacts if isinstance(item, dict) and isinstance(item.get("path"), str))
    return _build_result(
        result_type=result_type,
        context_pack=context_pack,
        receipt_index=receipt_index,
        event=event,
        summary=summary,
        artifact_refs=artifact_refs,
        phase_for_receipt=next_phase,
        state_patch={
            "phase": next_phase,
            "status": next_status,
            "active_item_id": selected,
            "item_queue": queue_after,
            "cycle_budget": max(0, state["cycle_budget"] - 1),
        },
        wakeup=wakeup,
        next_phase_hint=next_phase,
        work_item_context=work_item_context,
        artifact_materializations=artifacts,
    )


def _build_openclaw_mem_adapter() -> RuntimeAdapter:
    def _enrich_context(context_pack: WorkerContextPack) -> dict[str, Any]:
        state = context_pack["campaign_state"]
        mandate = context_pack["mandate"]
        return {
            "adapter_id": "openclaw-mem",
            "dispatch_path": "adapter",
            "phase_map": OPENCLAW_MEM_PHASE_MAP,
            "queue_len": len(state.get("item_queue") or []),
            "source_pointer_count": len(_openclaw_mem_collect_source_pointers(mandate)),
        }

    return RuntimeAdapter(
        adapter_id="openclaw-mem",
        display_name="openclaw-mem dev-decision adapter",
        worker=run_openclaw_mem_phase_worker,
        normalize_mandate=_default_normalize_mandate,
        enrich_context=_enrich_context,
        inspect_hook=None,
    )


def _steamer_seed_candidates(mandate: dict[str, Any], state: dict[str, Any]) -> list[str]:
    queue = [item for item in state.get("item_queue", []) if isinstance(item, str) and item.strip()]
    if queue:
        return queue

    configured: list[str] = []
    for key in ("work_items", "steamer_candidates", "seed_candidates"):
        value = mandate.get(key)
        if isinstance(value, list):
            configured.extend(
                item.strip() for item in value if isinstance(item, str) and item.strip()
            )

    if configured:
        return _dedupe_items(configured)

    mandate_id = mandate["mandate_id"]
    return [f"{mandate_id}-candidate-001"]


def _steamer_block_no_candidate(
    context_pack: WorkerContextPack,
    receipt_index: int,
    *,
    phase: str,
) -> WorkerResult:
    state = context_pack["campaign_state"]
    queue_before = [item for item in state.get("item_queue", []) if isinstance(item, str) and item.strip()]
    work_item_context = _steamer_work_item_context(
        selected_item=None,
        selection_reason="queue_empty",
        decision="blocked_no_candidate_available",
        queue_before=queue_before,
        queue_after=queue_before,
    )
    summary = "steamer worker blocked: no candidate available for bounded step"
    event = "steamer_no_candidate_available"
    return _build_result(
        result_type="BLOCK",
        context_pack=context_pack,
        receipt_index=receipt_index,
        event=event,
        summary=summary,
        artifact_refs=[
            "CAMPAIGN_STATE.json",
            "artifacts/steamer/idea-scout/queue-empty.json",
        ],
        phase_for_receipt=phase,
        state_patch={"status": "BLOCKED"},
        wakeup={"needed": True, "reason": "steamer_no_candidate_available"},
        next_phase_hint=phase,
        work_item_context=work_item_context,
        artifact_materializations=[
            _steamer_queue_artifact(
                phase=phase,
                selected_item=None,
                item_queue=queue_before,
                selection_reason="queue_empty",
            ),
            _steamer_trace_artifact(
                receipt_index=receipt_index,
                event=event,
                phase_before=phase,
                phase_after=phase,
                status_before=state.get("status", "ACTIVE"),
                status_after="BLOCKED",
                summary=summary,
                work_item_context=work_item_context,
            ),
        ],
    )


def _steamer_resume_retry_explore(
    context_pack: WorkerContextPack,
    receipt_index: int,
    *,
    cycle_budget_next: int,
) -> WorkerResult | None:
    state = context_pack["campaign_state"]
    mandate = context_pack["mandate"]

    if not bool(context_pack.get("resume_requested")):
        return None

    if state.get("status") != "BLOCKED":
        return None

    wakeup = state.get("wakeup")
    reason = wakeup.get("reason") if isinstance(wakeup, dict) else None
    if reason != "steamer_no_candidate_available":
        return None

    queue_before = [item for item in state.get("item_queue", []) if isinstance(item, str) and item.strip()]
    reseeded_queue = _steamer_seed_candidates(mandate, state)
    if not reseeded_queue:
        return None

    selected = reseeded_queue[0]
    queue_after = _queue_with_selected(reseeded_queue, selected)
    selection_reason = "resume_reseeded_queue_head"
    work_item_context = _steamer_work_item_context(
        selected_item=selected,
        selection_reason=selection_reason,
        decision="retry_idea_scout_after_resume_recovery",
        queue_before=queue_before,
        queue_after=queue_after,
    )

    summary = (
        "steamer resume recovered blocked explore state "
        f"(reason={reason}) by reseeding {len(reseeded_queue)} candidate(s); "
        f"retried idea-scout for {selected}"
    )
    event = "steamer_resume_retry_idea_scout"
    idea_scout_note = _steamer_idea_scout_note_artifact(
        selected_item=selected,
        mandate_id=mandate["mandate_id"],
        selection_reason=selection_reason,
    )
    return _build_result(
        result_type="ADVANCE",
        context_pack=context_pack,
        receipt_index=receipt_index,
        event=event,
        summary=summary,
        artifact_refs=[
            "CAMPAIGN_STATE.json",
            "artifacts/steamer/recovery/resume-no-candidate.json",
            "artifacts/steamer/candidate-queue.json",
            f"artifacts/steamer/idea-scout/{selected}.md",
        ],
        phase_for_receipt="EVALUATE",
        state_patch={
            "phase": "EVALUATE",
            "status": "ACTIVE",
            "active_item_id": selected,
            "item_queue": queue_after,
            "cycle_budget": cycle_budget_next,
        },
        wakeup={"needed": False, "reason": None},
        next_phase_hint="EVALUATE",
        work_item_context=work_item_context,
        artifact_materializations=[
            idea_scout_note,
            _steamer_queue_artifact(
                phase="EVALUATE",
                selected_item=selected,
                item_queue=queue_after,
                selection_reason=selection_reason,
            ),
            _steamer_trace_artifact(
                receipt_index=receipt_index,
                event=event,
                phase_before="EXPLORE",
                phase_after="EVALUATE",
                status_before=state.get("status", "BLOCKED"),
                status_after="ACTIVE",
                summary=summary,
                work_item_context=work_item_context,
            ),
        ],
    )


def _steamer_resume_recover_evaluate_to_explore(
    context_pack: WorkerContextPack,
    receipt_index: int,
    *,
    cycle_budget_next: int,
) -> WorkerResult | None:
    state = context_pack["campaign_state"]
    mandate = context_pack["mandate"]

    if not bool(context_pack.get("resume_requested")):
        return None

    if state.get("status") != "BLOCKED":
        return None

    wakeup = state.get("wakeup")
    reason = wakeup.get("reason") if isinstance(wakeup, dict) else None
    if reason != "steamer_no_candidate_available":
        return None

    queue_before = [item for item in state.get("item_queue", []) if isinstance(item, str) and item.strip()]
    if queue_before:
        return None

    back_budget = state.get("back_transitions_remaining")
    if not isinstance(back_budget, int) or back_budget <= 0:
        return None

    reseeded_queue = _steamer_seed_candidates(mandate, state)
    if not reseeded_queue:
        return None

    selected = reseeded_queue[0]
    queue_after = _queue_with_selected(reseeded_queue, selected)
    selection_reason = "resume_reseeded_evaluate_queue_head"
    work_item_context = _steamer_work_item_context(
        selected_item=selected,
        selection_reason=selection_reason,
        decision="resume_recovered_evaluate_missing_candidate_context",
        queue_before=queue_before,
        queue_after=queue_after,
        extra={"next_item_id": selected},
    )

    summary = (
        "steamer resume recovered blocked evaluate state "
        f"(reason={reason}) by reseeding {len(reseeded_queue)} candidate(s); "
        f"back-shifted to EXPLORE for idea-scout retry on {selected}"
    )
    event = "steamer_resume_recover_evaluate_to_explore"
    return _build_result(
        result_type="ADVANCE",
        context_pack=context_pack,
        receipt_index=receipt_index,
        event=event,
        summary=summary,
        artifact_refs=[
            "CAMPAIGN_STATE.json",
            "artifacts/steamer/recovery/resume-evaluate-no-candidate.json",
            "artifacts/steamer/candidate-queue.json",
        ],
        phase_for_receipt="EXPLORE",
        state_patch={
            "phase": "EXPLORE",
            "status": "ACTIVE",
            "active_item_id": selected,
            "item_queue": queue_after,
            "cycle_budget": cycle_budget_next,
            "back_transitions_remaining": back_budget - 1,
        },
        wakeup={"needed": False, "reason": None},
        next_phase_hint="EXPLORE",
        work_item_context=work_item_context,
        artifact_materializations=[
            _steamer_queue_artifact(
                phase="EXPLORE",
                selected_item=selected,
                item_queue=queue_after,
                selection_reason=selection_reason,
            ),
            _steamer_trace_artifact(
                receipt_index=receipt_index,
                event=event,
                phase_before="EVALUATE",
                phase_after="EXPLORE",
                status_before=state.get("status", "BLOCKED"),
                status_after="ACTIVE",
                summary=summary,
                work_item_context=work_item_context,
            ),
        ],
    )

def _append_drift_finding(
    findings: list[dict[str, str]],
    *,
    severity: str,
    code: str,
    message: str,
) -> None:
    findings.append({"severity": severity, "code": code, "message": message})


def _summarize_drift(findings: list[dict[str, str]]) -> str:
    critical_count = sum(1 for item in findings if item["severity"] == "critical")
    warning_count = sum(1 for item in findings if item["severity"] == "warning")
    note_count = sum(1 for item in findings if item["severity"] == "note")
    if critical_count == 0 and warning_count == 0 and note_count == 0:
        return "no adapter-domain drift detected"
    parts: list[str] = []
    if critical_count:
        parts.append(f"critical={critical_count}")
    if warning_count:
        parts.append(f"warning={warning_count}")
    if note_count:
        parts.append(f"note={note_count}")
    return ", ".join(parts)


def _drift_status_from_findings(findings: list[dict[str, str]]) -> str:
    if any(item["severity"] == "critical" for item in findings):
        return "critical"
    if any(item["severity"] == "warning" for item in findings):
        return "warning"
    return "clean"


def _steamer_inspect_hook(state: dict[str, Any], inspect_context: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    phase = state.get("phase")
    status = state.get("status")
    active_item = state.get("active_item_id") if isinstance(state.get("active_item_id"), str) else None
    queue = [item for item in state.get("item_queue", []) if isinstance(item, str) and item.strip()]
    wakeup = state.get("wakeup") if isinstance(state.get("wakeup"), dict) else {}
    wakeup_reason = wakeup.get("reason")
    mandate = inspect_context.get("mandate") if isinstance(inspect_context.get("mandate"), dict) else {}
    constraints = mandate.get("constraints") if isinstance(mandate.get("constraints"), dict) else {}
    control_scenario = mandate.get("control_scenario") if isinstance(mandate.get("control_scenario"), str) else None
    seeded_blocked_evaluate_fixture = (
        constraints.get("control_lane_only") is True
        and control_scenario == "resume-evaluate-recovery-seeded"
        and phase == "EVALUATE"
        and status == "BLOCKED"
        and wakeup_reason == "steamer_no_candidate_available"
        and not active_item
        and not queue
    )

    if phase not in STEAMER_PHASE_MAP:
        _append_drift_finding(
            findings,
            severity="critical",
            code="unknown_phase",
            message=f"state phase {phase!r} is not mapped in steamer adapter phase map",
        )

    if phase in STEAMER_PHASES_REQUIRING_ACTIVE_ITEM and not active_item:
        if seeded_blocked_evaluate_fixture:
            _append_drift_finding(
                findings,
                severity="note",
                code="seeded_blocked_evaluate_fixture",
                message=(
                    "seeded control scenario resume-evaluate-recovery-seeded intentionally captures "
                    "BLOCKED(EVALUATE, active_item_id=null, queue_empty) before the bounded --resume "
                    "back-shift; do not treat this as live adapter drift"
                ),
            )
        else:
            _append_drift_finding(
                findings,
                severity="critical",
                code="missing_active_item",
                message=f"phase {phase} requires active_item_id but state has null",
            )

    if active_item and queue and active_item not in queue:
        _append_drift_finding(
            findings,
            severity="warning",
            code="active_item_not_in_queue",
            message=(
                f"active_item_id={active_item} is not present in item_queue; "
                "state and candidate queue may be out of sync"
            ),
        )

    if status == "BLOCKED":
        if wakeup_reason == "steamer_no_candidate_available" and (active_item is not None or queue):
            _append_drift_finding(
                findings,
                severity="warning",
                code="blocked_no_candidate_inconsistent",
                message=(
                    "state says no candidate is available, but active_item_id/item_queue still contains candidates"
                ),
            )
        elif wakeup_reason == "cycle_budget_exhausted" and state.get("cycle_budget", 0) > 0:
            _append_drift_finding(
                findings,
                severity="warning",
                code="budget_reason_inconsistent",
                message=(
                    "state wakeup reason says cycle budget exhausted but cycle_budget is still positive"
                ),
            )

    if status == "OPERATOR_GATE":
        if phase != "GATE":
            _append_drift_finding(
                findings,
                severity="critical",
                code="operator_gate_phase_mismatch",
                message=f"status OPERATOR_GATE requires phase GATE, got phase={phase}",
            )
        if wakeup_reason != "steamer_shadow_review_gate":
            _append_drift_finding(
                findings,
                severity="warning",
                code="operator_gate_reason_mismatch",
                message=(
                    "status OPERATOR_GATE is set without wakeup.reason=steamer_shadow_review_gate"
                ),
            )

    last_receipt_payload = inspect_context.get("last_receipt_payload")
    if isinstance(last_receipt_payload, dict):
        receipt_phase = last_receipt_payload.get("phase")
        if isinstance(receipt_phase, str) and isinstance(phase, str) and receipt_phase != phase:
            _append_drift_finding(
                findings,
                severity="critical",
                code="last_receipt_phase_mismatch",
                message=(
                    f"state phase={phase} but last receipt phase={receipt_phase}; "
                    "campaign state may be out of sync with durable receipt history"
                ),
            )

        artifact_refs = last_receipt_payload.get("artifact_refs")
        work_item_payload = (
            last_receipt_payload.get("work_item")
            if isinstance(last_receipt_payload.get("work_item"), dict)
            else None
        )
        work_item_item_refs: set[str] = set()
        if isinstance(work_item_payload, dict):
            for key in ("id", "next_item_id", "queue_after_head"):
                value = work_item_payload.get(key)
                if isinstance(value, str) and value.strip():
                    work_item_item_refs.add(value)

        if active_item:
            if work_item_item_refs:
                if active_item not in work_item_item_refs:
                    _append_drift_finding(
                        findings,
                        severity="warning",
                        code="last_receipt_active_item_mismatch",
                        message=(
                            "last steamer receipt work_item context does not reference current "
                            "active_item_id; operator should confirm resume/rotation flow"
                        ),
                    )
            elif isinstance(artifact_refs, list):
                steamer_refs = [
                    ref
                    for ref in artifact_refs
                    if isinstance(ref, str) and "artifacts/steamer/" in ref
                ]
                if steamer_refs and not any(active_item in ref for ref in steamer_refs):
                    _append_drift_finding(
                        findings,
                        severity="warning",
                        code="last_receipt_active_item_mismatch",
                        message=(
                            "last steamer receipt artifacts do not reference current active_item_id; "
                            "operator should confirm resume/rotation flow"
                        ),
                    )

    return {
        "status": _drift_status_from_findings(findings),
        "summary": _summarize_drift(findings),
        "phase_map_value": STEAMER_PHASE_MAP.get(phase),
        "findings": findings,
    }


def run_steamer_phase_worker(context_pack: WorkerContextPack, receipt_index: int) -> WorkerResult:
    state = context_pack["campaign_state"]
    mandate = context_pack["mandate"]
    current_phase = state["phase"]

    if state["cycle_budget"] <= 0 and current_phase not in {"DELIVER", "CLOSED"}:
        return _cycle_budget_block(
            context_pack,
            receipt_index,
            adapter_id="steamer",
            dispatch_path="adapter",
        )

    cycle_budget_next = max(0, state["cycle_budget"] - 1)
    queue_before = [item for item in state.get("item_queue", []) if isinstance(item, str) and item.strip()]
    active_item = state.get("active_item_id") if isinstance(state.get("active_item_id"), str) else None

    if current_phase == "INTAKE":
        seeded_queue = _steamer_seed_candidates(mandate, state)
        selected = active_item or seeded_queue[0]
        selection_reason = "state_active_item" if active_item else "seeded_queue_head"
        queue_after = _queue_with_selected(seeded_queue, selected)
        summary = (
            f"steamer mandate-intake seeded {len(seeded_queue)} candidate(s); "
            f"selected {selected} for idea-scout"
        )
        event = "steamer_mandate_intake_completed"
        work_item_context = _steamer_work_item_context(
            selected_item=selected,
            selection_reason=selection_reason,
            decision="seed_candidates_for_idea_scout",
            queue_before=queue_before,
            queue_after=queue_after,
        )
        return _build_result(
            result_type="ADVANCE",
            context_pack=context_pack,
            receipt_index=receipt_index,
            event=event,
            summary=summary,
            artifact_refs=[
                "MANDATE.yaml",
                "CAMPAIGN_STATE.json",
                "adapters/steamer/phase-mapping.md",
                "artifacts/steamer/mandate-intake.json",
                "artifacts/steamer/candidate-queue.json",
            ],
            phase_for_receipt="EXPLORE",
            state_patch={
                "phase": "EXPLORE",
                "status": "ACTIVE",
                "active_item_id": selected,
                "item_queue": queue_after,
                "cycle_budget": cycle_budget_next,
            },
            wakeup={"needed": False, "reason": None},
            next_phase_hint="EXPLORE",
            work_item_context=work_item_context,
            artifact_materializations=[
                _steamer_queue_artifact(
                    phase="EXPLORE",
                    selected_item=selected,
                    item_queue=queue_after,
                    selection_reason=selection_reason,
                ),
                _steamer_trace_artifact(
                    receipt_index=receipt_index,
                    event=event,
                    phase_before="INTAKE",
                    phase_after="EXPLORE",
                    status_before=state.get("status", "ACTIVE"),
                    status_after="ACTIVE",
                    summary=summary,
                    work_item_context=work_item_context,
                ),
            ],
        )

    if current_phase == "EXPLORE":
        if active_item:
            selected = active_item
            selection_reason = "state_active_item"
        elif queue_before:
            selected = queue_before[0]
            selection_reason = "item_queue_head"
        else:
            selected = None
            selection_reason = "queue_empty"

        if selected is None:
            resumed = _steamer_resume_retry_explore(
                context_pack,
                receipt_index,
                cycle_budget_next=cycle_budget_next,
            )
            if resumed is not None:
                return resumed
            return _steamer_block_no_candidate(context_pack, receipt_index, phase=current_phase)

        queue_after = _queue_with_selected(queue_before, selected)
        summary = f"steamer idea-scout produced a scoped candidate sketch for {selected}"
        event = "steamer_idea_scout_completed"
        idea_scout_note = _steamer_idea_scout_note_artifact(
            selected_item=selected,
            mandate_id=mandate["mandate_id"],
            selection_reason=selection_reason,
        )
        work_item_context = _steamer_work_item_context(
            selected_item=selected,
            selection_reason=selection_reason,
            decision="idea_scout_completed",
            queue_before=queue_before,
            queue_after=queue_after,
        )
        return _build_result(
            result_type="ADVANCE",
            context_pack=context_pack,
            receipt_index=receipt_index,
            event=event,
            summary=summary,
            artifact_refs=[
                "CAMPAIGN_STATE.json",
                f"artifacts/steamer/idea-scout/{selected}.md",
                "artifacts/steamer/candidate-queue.json",
            ],
            phase_for_receipt="EVALUATE",
            state_patch={
                "phase": "EVALUATE",
                "status": "ACTIVE",
                "active_item_id": selected,
                "item_queue": queue_after,
                "cycle_budget": cycle_budget_next,
            },
            wakeup={"needed": False, "reason": None},
            next_phase_hint="EVALUATE",
            work_item_context=work_item_context,
            artifact_materializations=[
                idea_scout_note,
                _steamer_queue_artifact(
                    phase="EVALUATE",
                    selected_item=selected,
                    item_queue=queue_after,
                    selection_reason=selection_reason,
                ),
                _steamer_trace_artifact(
                    receipt_index=receipt_index,
                    event=event,
                    phase_before="EXPLORE",
                    phase_after="EVALUATE",
                    status_before=state.get("status", "ACTIVE"),
                    status_after="ACTIVE",
                    summary=summary,
                    work_item_context=work_item_context,
                ),
            ],
        )

    if current_phase == "EVALUATE":
        if active_item:
            selected = active_item
            selection_reason = "state_active_item"
        elif queue_before:
            selected = queue_before[0]
            selection_reason = "item_queue_head"
        else:
            selected = None
            selection_reason = "queue_empty"

        if selected is None:
            resumed = _steamer_resume_recover_evaluate_to_explore(
                context_pack,
                receipt_index,
                cycle_budget_next=cycle_budget_next,
            )
            if resumed is not None:
                return resumed
            return _steamer_block_no_candidate(context_pack, receipt_index, phase=current_phase)

        if len(queue_before) > 1 and state.get("back_transitions_remaining", 0) > 0:
            next_candidate = queue_before[1]
            queue_after = _queue_with_selected(queue_before[1:], next_candidate)
            summary = (
                f"steamer fast-triage marked {selected} as evidence-insufficient; "
                f"rotate to {next_candidate} for another explore pass"
            )
            event = "steamer_fast_triage_requests_more_explore"
            work_item_context = _steamer_work_item_context(
                selected_item=selected,
                selection_reason=selection_reason,
                decision="fast_triage_rotate_to_next_candidate",
                queue_before=queue_before,
                queue_after=queue_after,
                extra={"next_item_id": next_candidate},
            )
            return _build_result(
                result_type="ADVANCE",
                context_pack=context_pack,
                receipt_index=receipt_index,
                event=event,
                summary=summary,
                artifact_refs=[
                    "CAMPAIGN_STATE.json",
                    f"artifacts/steamer/replay/fast-triage-{selected}.json",
                    "artifacts/steamer/candidate-queue.json",
                ],
                phase_for_receipt="EXPLORE",
                state_patch={
                    "phase": "EXPLORE",
                    "status": "ACTIVE",
                    "active_item_id": next_candidate,
                    "item_queue": queue_after,
                    "cycle_budget": cycle_budget_next,
                    "back_transitions_remaining": state["back_transitions_remaining"] - 1,
                },
                wakeup={"needed": False, "reason": None},
                next_phase_hint="EXPLORE",
                work_item_context=work_item_context,
                artifact_materializations=[
                    _steamer_queue_artifact(
                        phase="EXPLORE",
                        selected_item=next_candidate,
                        item_queue=queue_after,
                        selection_reason="rotate_queue_next_candidate",
                    ),
                    _steamer_trace_artifact(
                        receipt_index=receipt_index,
                        event=event,
                        phase_before="EVALUATE",
                        phase_after="EXPLORE",
                        status_before=state.get("status", "ACTIVE"),
                        status_after="ACTIVE",
                        summary=summary,
                        work_item_context=work_item_context,
                    ),
                ],
            )

        queue_after = _queue_with_selected(queue_before, selected)
        summary = f"steamer deep-validation accepted {selected} for card synthesis"
        event = "steamer_deep_validation_completed"
        work_item_context = _steamer_work_item_context(
            selected_item=selected,
            selection_reason=selection_reason,
            decision="deep_validation_accepted_for_synthesis",
            queue_before=queue_before,
            queue_after=queue_after,
        )
        return _build_result(
            result_type="ADVANCE",
            context_pack=context_pack,
            receipt_index=receipt_index,
            event=event,
            summary=summary,
            artifact_refs=[
                "CAMPAIGN_STATE.json",
                f"artifacts/steamer/replay/deep-validation-{selected}.json",
                f"artifacts/steamer/candidate-card/{selected}.md",
            ],
            phase_for_receipt="SYNTHESIZE",
            state_patch={
                "phase": "SYNTHESIZE",
                "status": "ACTIVE",
                "active_item_id": selected,
                "item_queue": queue_after,
                "cycle_budget": cycle_budget_next,
            },
            wakeup={"needed": False, "reason": None},
            next_phase_hint="SYNTHESIZE",
            work_item_context=work_item_context,
            artifact_materializations=[
                _steamer_queue_artifact(
                    phase="SYNTHESIZE",
                    selected_item=selected,
                    item_queue=queue_after,
                    selection_reason=selection_reason,
                ),
                _steamer_trace_artifact(
                    receipt_index=receipt_index,
                    event=event,
                    phase_before="EVALUATE",
                    phase_after="SYNTHESIZE",
                    status_before=state.get("status", "ACTIVE"),
                    status_after="ACTIVE",
                    summary=summary,
                    work_item_context=work_item_context,
                ),
            ],
        )

    if current_phase == "SYNTHESIZE":
        if active_item:
            selected = active_item
            selection_reason = "state_active_item"
        elif queue_before:
            selected = queue_before[0]
            selection_reason = "item_queue_head"
        else:
            return _steamer_block_no_candidate(context_pack, receipt_index, phase=current_phase)

        queue_after = _queue_with_selected(queue_before, selected)
        summary = f"steamer card-synthesis packaged {selected} for operator gate review"
        event = "steamer_card_synthesis_completed"
        work_item_context = _steamer_work_item_context(
            selected_item=selected,
            selection_reason=selection_reason,
            decision="card_synthesis_packaged_for_gate",
            queue_before=queue_before,
            queue_after=queue_after,
        )
        return _build_result(
            result_type="ADVANCE",
            context_pack=context_pack,
            receipt_index=receipt_index,
            event=event,
            summary=summary,
            artifact_refs=[
                "CAMPAIGN_STATE.json",
                f"artifacts/steamer/candidate-card/{selected}.md",
                f"artifacts/steamer/shadow-packet/{selected}.md",
            ],
            phase_for_receipt="GATE",
            state_patch={
                "phase": "GATE",
                "status": "ACTIVE",
                "active_item_id": selected,
                "item_queue": queue_after,
                "cycle_budget": cycle_budget_next,
            },
            wakeup={"needed": False, "reason": None},
            next_phase_hint="GATE",
            work_item_context=work_item_context,
            artifact_materializations=[
                _steamer_queue_artifact(
                    phase="GATE",
                    selected_item=selected,
                    item_queue=queue_after,
                    selection_reason=selection_reason,
                ),
                _steamer_trace_artifact(
                    receipt_index=receipt_index,
                    event=event,
                    phase_before="SYNTHESIZE",
                    phase_after="GATE",
                    status_before=state.get("status", "ACTIVE"),
                    status_after="ACTIVE",
                    summary=summary,
                    work_item_context=work_item_context,
                ),
            ],
        )

    if current_phase == "GATE":
        replay_decision_raw = context_pack.get("replay_decision")
        replay_decision = (
            replay_decision_raw.strip()
            if isinstance(replay_decision_raw, str) and replay_decision_raw.strip()
            else None
        )
        replay_note_raw = context_pack.get("replay_note")
        replay_note = (
            replay_note_raw.strip()
            if isinstance(replay_note_raw, str) and replay_note_raw.strip()
            else None
        )

        if state.get("status") == "OPERATOR_GATE" and replay_decision in {
            "approve_shadow_review",
            "reject_shadow_review",
        }:
            if active_item:
                selected = active_item
                selection_reason = "state_active_item"
            elif queue_before:
                selected = queue_before[0]
                selection_reason = "item_queue_head"
            else:
                return _steamer_block_no_candidate(context_pack, receipt_index, phase=current_phase)

            queue_after = _queue_with_selected(queue_before, selected)
            if replay_decision == "approve_shadow_review":
                summary = (
                    "steamer operator-gate decision replayed: "
                    f"approve_shadow_review for {selected}; campaign can move to DELIVER"
                )
                decision_code = "operator_gate_replay_approved_shadow_review"
                phase_after = "DELIVER"
                status_after = "ACTIVE"
            else:
                summary = (
                    "steamer operator-gate decision replayed: "
                    f"reject_shadow_review for {selected}; campaign closed without delivery"
                )
                decision_code = "operator_gate_replay_rejected_shadow_review"
                phase_after = "CLOSED"
                status_after = "CLOSED"

            event = "steamer_operator_gate_decision_replayed"
            work_item_context = _steamer_work_item_context(
                selected_item=selected,
                selection_reason=selection_reason,
                decision=decision_code,
                queue_before=queue_before,
                queue_after=queue_after,
                extra={
                    "operator_decision": replay_decision,
                    "operator_note": replay_note,
                },
            )
            gate_replay_artifact = _steamer_gate_replay_artifact(
                receipt_index=receipt_index,
                selected_item=selected,
                decision=replay_decision,
                note=replay_note,
                phase_after=phase_after,
                status_after=status_after,
            )
            return _build_result(
                result_type="ADVANCE",
                context_pack=context_pack,
                receipt_index=receipt_index,
                event=event,
                summary=summary,
                artifact_refs=[
                    "CAMPAIGN_STATE.json",
                    f"artifacts/steamer/gates/shadow-review-request-{selected}.md",
                    f"artifacts/steamer/candidate-card/{selected}.md",
                    gate_replay_artifact["path"],
                ],
                phase_for_receipt=phase_after,
                state_patch={
                    "phase": phase_after,
                    "status": status_after,
                    "active_item_id": selected,
                    "item_queue": queue_after,
                    "cycle_budget": cycle_budget_next,
                },
                wakeup={"needed": False, "reason": None},
                next_phase_hint=phase_after,
                work_item_context=work_item_context,
                artifact_materializations=[
                    _steamer_queue_artifact(
                        phase=phase_after,
                        selected_item=selected,
                        item_queue=queue_after,
                        selection_reason=selection_reason,
                    ),
                    gate_replay_artifact,
                    _steamer_trace_artifact(
                        receipt_index=receipt_index,
                        event=event,
                        phase_before="GATE",
                        phase_after=phase_after,
                        status_before=state.get("status", "OPERATOR_GATE"),
                        status_after=status_after,
                        summary=summary,
                        work_item_context=work_item_context,
                    ),
                ],
            )

        if active_item:
            selected = active_item
            selection_reason = "state_active_item"
        elif queue_before:
            selected = queue_before[0]
            selection_reason = "item_queue_head"
        else:
            return _steamer_block_no_candidate(context_pack, receipt_index, phase=current_phase)

        queue_after = _queue_with_selected(queue_before, selected)
        summary = (
            f"steamer operator-gate required: promotion_to_shadow_review for {selected} "
            "needs explicit operator decision"
        )
        event = "steamer_operator_gate_shadow_review_required"
        work_item_context = _steamer_work_item_context(
            selected_item=selected,
            selection_reason=selection_reason,
            decision="operator_gate_shadow_review_required",
            queue_before=queue_before,
            queue_after=queue_after,
        )
        return _build_result(
            result_type="ESCALATE",
            context_pack=context_pack,
            receipt_index=receipt_index,
            event=event,
            summary=summary,
            artifact_refs=[
                "CAMPAIGN_STATE.json",
                f"artifacts/steamer/gates/shadow-review-request-{selected}.md",
                f"artifacts/steamer/candidate-card/{selected}.md",
            ],
            phase_for_receipt="GATE",
            state_patch={
                "phase": "GATE",
                "status": "OPERATOR_GATE",
                "active_item_id": selected,
                "item_queue": queue_after,
                "cycle_budget": cycle_budget_next,
            },
            wakeup={"needed": True, "reason": "steamer_shadow_review_gate"},
            next_phase_hint="GATE",
            work_item_context=work_item_context,
            artifact_materializations=[
                _steamer_queue_artifact(
                    phase="GATE",
                    selected_item=selected,
                    item_queue=queue_after,
                    selection_reason=selection_reason,
                ),
                _steamer_trace_artifact(
                    receipt_index=receipt_index,
                    event=event,
                    phase_before="GATE",
                    phase_after="GATE",
                    status_before=state.get("status", "ACTIVE"),
                    status_after="OPERATOR_GATE",
                    summary=summary,
                    work_item_context=work_item_context,
                ),
            ],
        )

    if current_phase == "DELIVER":
        if active_item:
            selected = active_item
            selection_reason = "state_active_item"
        elif queue_before:
            selected = queue_before[0]
            selection_reason = "item_queue_head"
        else:
            selected = None
            selection_reason = "delivery_without_item_context"

        queue_after = _queue_with_selected(queue_before, selected)
        summary = "steamer delivery packet acknowledged; campaign moved to CLOSED"
        event = "steamer_delivery_packet_closed"
        work_item_context = _steamer_work_item_context(
            selected_item=selected,
            selection_reason=selection_reason,
            decision="delivery_packet_acknowledged_and_closed",
            queue_before=queue_before,
            queue_after=queue_after,
        )
        return _build_result(
            result_type="ADVANCE",
            context_pack=context_pack,
            receipt_index=receipt_index,
            event=event,
            summary=summary,
            artifact_refs=["CAMPAIGN_STATE.json", "artifacts/steamer/delivery-packet.md"],
            phase_for_receipt="CLOSED",
            state_patch={
                "phase": "CLOSED",
                "status": "CLOSED",
                "item_queue": queue_after,
                "cycle_budget": cycle_budget_next,
            },
            wakeup={"needed": False, "reason": None},
            next_phase_hint="CLOSED",
            work_item_context=work_item_context,
            artifact_materializations=[
                _steamer_queue_artifact(
                    phase="CLOSED",
                    selected_item=selected,
                    item_queue=queue_after,
                    selection_reason=selection_reason,
                ),
                _steamer_trace_artifact(
                    receipt_index=receipt_index,
                    event=event,
                    phase_before="DELIVER",
                    phase_after="CLOSED",
                    status_before=state.get("status", "ACTIVE"),
                    status_after="CLOSED",
                    summary=summary,
                    work_item_context=work_item_context,
                ),
            ],
        )

    return run_linear_phase_worker(
        context_pack,
        receipt_index,
        adapter_id="steamer",
        dispatch_path="adapter-fallback",
    )

def _build_linear_adapter(adapter_id: str, display_name: str, dispatch_path: str) -> RuntimeAdapter:
    def _worker(context_pack: WorkerContextPack, receipt_index: int) -> WorkerResult:
        return run_linear_phase_worker(
            context_pack,
            receipt_index,
            adapter_id=adapter_id,
            dispatch_path=dispatch_path,
        )

    def _enrich_context(_: WorkerContextPack) -> dict[str, Any]:
        return {
            "adapter_id": adapter_id,
            "dispatch_path": dispatch_path,
        }

    return RuntimeAdapter(
        adapter_id=adapter_id,
        display_name=display_name,
        worker=_worker,
        normalize_mandate=_default_normalize_mandate,
        enrich_context=_enrich_context,
        inspect_hook=None,
    )


def _build_steamer_adapter() -> RuntimeAdapter:
    def _enrich_context(context_pack: WorkerContextPack) -> dict[str, Any]:
        state = context_pack["campaign_state"]
        return {
            "adapter_id": "steamer",
            "dispatch_path": "adapter",
            "phase_map": STEAMER_PHASE_MAP,
            "queue_len": len(state.get("item_queue") or []),
        }

    return RuntimeAdapter(
        adapter_id="steamer",
        display_name="Steamer executable adapter",
        worker=run_steamer_phase_worker,
        normalize_mandate=_default_normalize_mandate,
        enrich_context=_enrich_context,
        inspect_hook=_steamer_inspect_hook,
    )


RUNTIME_ADAPTER_REGISTRY: dict[str, RuntimeAdapter] = {
    "steamer": _build_steamer_adapter(),
    "content-production": _build_linear_adapter(
        "content-production", "Content production adapter", "adapter"
    ),
    "openclaw-mem": _build_openclaw_mem_adapter(),
}

STUB_RUNTIME_ADAPTER = _build_linear_adapter("stub", "Stub fallback adapter", "stub")


def resolve_runtime_adapter(adapter_id: str, *, allow_stub_fallback: bool = False) -> RuntimeAdapter:
    adapter = RUNTIME_ADAPTER_REGISTRY.get(adapter_id)
    if adapter is not None:
        return adapter

    if allow_stub_fallback:
        return STUB_RUNTIME_ADAPTER

    raise AdapterResolutionError(
        f"runtime adapter not found for adapter_id={adapter_id!r}; "
        "register it in tools/_adapter_runtime.py or run with --dispatch-mode stub"
    )
