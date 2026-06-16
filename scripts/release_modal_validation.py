from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "logs" / "token_holdem.jsonl"


@dataclass
class ModelEvidence:
    model_id: str
    loads: bool = False
    generates: bool = False
    json_valid: bool = False
    legal_action: bool = False
    action_applied: bool = False
    full_hand: bool = False
    arena_verified: bool = False
    fallback_used: bool = False
    failures: list[str] = field(default_factory=list)
    latencies: list[float] = field(default_factory=list)


def _run(command: list[str], *, enabled: bool = True) -> None:
    if not enabled:
        return
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def _log_offset() -> int:
    if not LOG_FILE.exists():
        return 0
    return LOG_FILE.stat().st_size


def _read_new_logs(offset: int) -> list[dict[str, Any]]:
    if not LOG_FILE.exists():
        return []
    rows: list[dict[str, Any]] = []
    with LOG_FILE.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _run_direct_roster_decisions() -> None:
    from token_holdem.agents import ROSTER
    from token_holdem.model_runtime import ModalRuntime

    runtime = ModalRuntime()
    legal = {
        "actions": ["fold", "call", "raise", "all_in"],
        "to_call": 20,
        "raise_presets": {"min": 40, "half_pot": 80, "pot": 140, "all_in": 1000},
    }
    for idx, profile in enumerate(ROSTER, start=1):
        state = {
            "hand_no": idx,
            "street": "preflop",
            "hole_cards": ["As", "Kd"],
            "community_cards": [],
            "stack": 1000,
            "pot": 30,
            "legal": legal,
            "history": ["small blind posts 10", "big blind posts 20"],
            "recent_chats": [],
            "seed": 9100 + idx,
            "session_id": "release-direct",
            "hand_id": f"release-direct-h{idx:03d}",
            "orbit_id": "release-direct-o01",
        }
        started = time.perf_counter()
        result = runtime.decide(profile, state)
        elapsed = time.perf_counter() - started
        print(
            json.dumps(
                {
                    "stage": "direct_decision",
                    "model": profile.name,
                    "model_id": profile.model_id,
                    "source": result.source,
                    "status": result.status,
                    "decision": result.decision,
                    "elapsed_seconds": round(elapsed, 3),
                },
                default=str,
            ),
            flush=True,
        )


def _run_arena(hands: int, seed: int) -> None:
    from app import run_arena

    for _ in run_arena(seed, hands):
        pass


def _parse_evidence(rows: list[dict[str, Any]]) -> dict[str, ModelEvidence]:
    from token_holdem.agents import ROSTER
    from token_holdem.model_runtime import SUPPORTED_TRANSFORMERS_MODELS

    evidence = {
        profile.name: ModelEvidence(SUPPORTED_TRANSFORMERS_MODELS.get(profile.name, profile.model_id))
        for profile in ROSTER
    }
    pending: dict[tuple[str, str, str, str], list[datetime]] = {}
    completed_hands = {row.get("hand_id") for row in rows if row.get("message") == "hand_completed"}

    for row in rows:
        player = row.get("player")
        if player not in evidence:
            continue
        item = evidence[player]
        message = row.get("message")
        key = (row.get("session_id", ""), row.get("hand_id", ""), row.get("orbit_id", ""), player)

        if message == "model_runtime_modal_call_started":
            item.loads = True
            try:
                pending.setdefault(key, []).append(datetime.strptime(row["time"], "%Y-%m-%dT%H:%M:%S%z"))
            except (KeyError, ValueError):
                pass
        elif message == "model_runtime_modal_success":
            item.loads = True
            item.generates = True
            item.json_valid = True
            item.legal_action = row.get("action") is not None
            if row.get("hand_id") in completed_hands:
                item.full_hand = True
            raw_text = str(row.get("raw_text", ""))
            if "used persona fallback" in raw_text:
                item.fallback_used = True
            if "repair=" in raw_text:
                item.failures.append("repair prompt used")
            starts = pending.get(key) or []
            if starts:
                try:
                    ended = datetime.strptime(row["time"], "%Y-%m-%dT%H:%M:%S%z")
                    item.latencies.append((ended - starts.pop(0)).total_seconds())
                except (KeyError, ValueError):
                    pass
        elif message == "model_runtime_modal_failed":
            item.failures.append(str(row.get("error", "Modal failure"))[:240])
        elif message == "ai_decision":
            if row.get("source") == "modal_model":
                item.arena_verified = row.get("session_id") not in {"release-direct", "test-session"}
        elif message == "action_applied":
            item.action_applied = True
            if row.get("hand_id") in completed_hands:
                item.full_hand = True
        elif message == "ai_decision_blocked":
            item.failures.append(str(row.get("error", "decision blocked"))[:240])
        elif message in {"model_runtime_partial_fallback", "model_runtime_deterministic_dev"}:
            item.fallback_used = True

    return evidence


def _write_report(evidence: dict[str, ModelEvidence], rows: list[dict[str, Any]], path: Path) -> None:
    completed = [row for row in rows if row.get("message") == "hand_completed"]
    payload = {
        "generated_at": datetime.now().isoformat(),
        "completed_hands": len(completed),
        "models": {
            name: {
                "model_id": item.model_id,
                "loads": item.loads,
                "generates": item.generates,
                "json_valid": item.json_valid,
                "legal_action": item.legal_action,
                "action_applied": item.action_applied,
                "full_hand": item.full_hand,
                "arena_verified": item.arena_verified,
                "fallback_used": item.fallback_used,
                "latency_avg_seconds": round(sum(item.latencies) / len(item.latencies), 3) if item.latencies else None,
                "latency_max_seconds": max(item.latencies) if item.latencies else None,
                "failures": item.failures,
            }
            for name, item in evidence.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=True), flush=True)


def _assert_release_ready(evidence: dict[str, ModelEvidence], rows: list[dict[str, Any]]) -> None:
    failures: list[str] = []
    if not any(row.get("message") == "hand_completed" for row in rows):
        failures.append("No AI Arena hand completed.")
    for name, item in evidence.items():
        for field_name in ("loads", "generates", "json_valid", "legal_action", "action_applied", "full_hand", "arena_verified"):
            if not getattr(item, field_name):
                failures.append(f"{name}: missing {field_name}")
        if item.fallback_used:
            failures.append(f"{name}: fallback used")
        if item.failures:
            failures.append(f"{name}: failures: {'; '.join(item.failures)}")
    if failures:
        raise SystemExit("Release validation failed:\n" + "\n".join(f"- {failure}" for failure in failures))


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy and validate Token Hold'em Modal release readiness.")
    parser.add_argument("--deploy", action="store_true", help="Run modal deploy before validation.")
    parser.add_argument("--setup-cache", action="store_true", help="Pre-download enabled model snapshots.")
    parser.add_argument("--warmup", action="store_true", help="Warm all enabled Modal model workers.")
    parser.add_argument("--skip-direct", action="store_true", help="Skip direct per-model Modal decisions.")
    parser.add_argument("--skip-arena", action="store_true", help="Skip AI Arena validation.")
    parser.add_argument("--arena-hands", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--report", type=Path, default=Path("logs/release_modal_validation.json"))
    args = parser.parse_args()

    os.environ["USE_MODAL_INFERENCE"] = "true"

    _run(["uv", "run", "modal", "deploy", "modal_inference.py"], enabled=args.deploy)
    _run(["uv", "run", "modal", "run", "modal_inference.py::setup_cache"], enabled=args.setup_cache)
    _run(["uv", "run", "modal", "run", "modal_inference.py::warmup_demo"], enabled=args.warmup)

    offset = _log_offset()
    if not args.skip_direct:
        _run_direct_roster_decisions()
    if not args.skip_arena:
        _run_arena(args.arena_hands, args.seed)

    rows = _read_new_logs(offset)
    evidence = _parse_evidence(rows)
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    _write_report(evidence, rows, report_path)
    _assert_release_ready(evidence, rows)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
