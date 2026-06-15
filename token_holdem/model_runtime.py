from __future__ import annotations

import gc
import json
import os
import random
import re
from dataclasses import dataclass
from typing import Any, Protocol

from token_holdem.agents import AgentProfile, ROSTER, estimate_strength, fallback_decide
from token_holdem.logging_utils import get_logger, log_event


logger = get_logger("token_holdem.model_runtime")


SUPPORTED_TRANSFORMERS_MODELS = {
    "Nemotron Nano": "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF",
    "Qwen": "Qwen/Qwen3-0.6B",
    "Gemma": "google/gemma-4-12B-it",
    "Cohere Command R7B": "CohereLabs/c4ai-command-r7b-12-2024",
    "Mistral": "mistralai/Mistral-7B-Instruct-v0.2",
    "OpenAI Open Model 20B": "openai/gpt-oss-20b",
    "Llama Scout": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
}

DEFAULT_MODAL_DISABLED_MODEL_NAMES: set[str] = set()
DEFAULT_MODAL_MODEL_NAMES = set(SUPPORTED_TRANSFORMERS_MODELS) - DEFAULT_MODAL_DISABLED_MODEL_NAMES
MULTIMODAL_MODAL_MODEL_IDS = {"google/gemma-4-12B-it"}
MODAL_WORKER_CLASS_BY_FAMILY = {
    "causal": "CausalModelWorker",
    "heavy_causal": "HeavyCausalModelWorker",
    "multimodal": "MultimodalModelWorker",
    "gguf": "GgufModelWorker",
}
DEFAULT_MODAL_TIMEOUT_SECONDS = 300.0


@dataclass
class RuntimeDecision:
    decision: dict[str, Any]
    source: str
    status: str


class ModelRuntimeUnavailable(RuntimeError):
    """Raised when a model-enabled hand cannot get a real model decision."""


class InferenceRuntime(Protocol):
    def decide(self, profile: AgentProfile, state_summary: dict[str, Any]) -> RuntimeDecision:
        ...


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def persona_fallback_decision(profile: AgentProfile, state_summary: dict[str, Any], status: str, source: str = "fallback") -> RuntimeDecision:
    decision = apply_poker_sanity_guard(fallback_decide(profile, state_summary, seed=state_summary.get("seed")), state_summary)
    decision["table_talk"] = template_table_talk(profile, decision["action"], state_summary)
    return RuntimeDecision(decision, source, status)


def deterministic_fallback_enabled() -> bool:
    return env_flag("TOKEN_HOLDEM_ALLOW_DETERMINISTIC_BOTS")


def configured_modal_model_names(configured: str | None = None) -> set[str]:
    configured = os.getenv("TOKEN_HOLDEM_MODAL_MODEL_NAMES") if configured is None else configured
    if configured is None or configured.strip().lower() in {"", "default"}:
        return set(DEFAULT_MODAL_MODEL_NAMES)
    if configured.strip().lower() in {"all", "*"}:
        return {profile.name for profile in ROSTER}
    return {name.strip() for name in configured.split(",") if name.strip()}


def model_runtime_statuses(enabled_names: set[str] | None = None) -> list[dict[str, str]]:
    enabled_names = enabled_names if enabled_names is not None else configured_modal_model_names()
    rows: list[dict[str, str]] = []
    for profile in ROSTER:
        model_id = SUPPORTED_TRANSFORMERS_MODELS.get(profile.name, profile.model_id)
        if profile.name not in enabled_names:
            state = "disabled"
            note = "Not included in TOKEN_HOLDEM_MODAL_MODEL_NAMES."
        elif requires_gguf_runtime(model_id):
            state = "active through Modal warm GGUF worker"
            note = "A parameterized Modal class loads this GGUF once per warm model worker with llama.cpp."
        elif model_id in MULTIMODAL_MODAL_MODEL_IDS:
            state = "active through Modal warm multimodal worker"
            note = "A parameterized Modal class loads this model once per warm model worker."
        else:
            state = "active through Modal warm Transformers worker"
            note = "A parameterized Modal class loads this model once per warm model worker."
        rows.append({"name": profile.name, "model_id": model_id, "state": state, "note": note})
    return rows


def build_prompt(profile: AgentProfile, state_summary: dict[str, Any]) -> str:
    legal = state_summary["legal"]
    return f"""You are {profile.name}, a poker regular in Token Hold'em.
Persona: {profile.persona}.

You are playing Texas Hold'em. The game engine enforces all rules. Choose exactly one legal action.
Return a single JSON object and nothing else.

Visible state:
- Hole cards: {state_summary['hole_cards']}
- Community cards: {state_summary['community_cards']}
- Stack: {state_summary['stack']}
- Pot: {state_summary['pot']}
- Amount to call: {legal['to_call']}
- Legal actions: {legal['actions']}
- Raise presets: {legal['raise_presets']}
- Recent betting history: {state_summary.get('history', [])[-8:]}

JSON keys:
- action: one of {legal['actions']}
- amount: 0 unless action is raise or all_in
    - for raise, amount must exactly equal one value from raise_presets
    - for all_in, amount must equal your full stack
- reasoning_hint: brief private poker reason

If facing a large all-in with a weak hand, fold.
Do not include public table talk here. Do not include examples.
Respond now with exactly one valid JSON object and no surrounding text.
"""


def build_table_talk_prompt(profile: AgentProfile, final_action: str, state_summary: dict[str, Any]) -> str:
    mood = {
        "fold": "slipping away from a smoky tale",
        "check": "waiting by the candle",
        "call": "staying curious at the table",
        "raise": "turning up the tavern pressure",
        "all_in": "making the whole room hold its breath",
    }.get(final_action, "watching the table")
    return f"""You are {profile.name} at a cozy tavern poker table.
Persona: {profile.persona}.

Your private mood is: {mood}.
Recent public lines to avoid repeating: {state_summary.get('recent_chats', [])[-8:]}

Write exactly one original in-world sentence. No JSON. No labels. No quotes.

Style rules:
- Tavern poker banter, light hints, playful needling.
- No chip amounts, no numbers, no action names like fold/check/call/raise/all-in.
- Do not mention exact cards.
- Do not explain strategy.
- Keep it under twelve words.
"""


def parse_model_json(text: str) -> dict[str, Any] | None:
    for value in parse_model_json_candidates(text):
        return value
    return None


def parse_model_json_candidates(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    for idx, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    return candidates


def validate_decision(raw: dict[str, Any] | None, legal: dict[str, Any]) -> dict[str, Any] | None:
    if not raw:
        return None
    action = str(raw.get("action", "")).lower().strip().replace("-", "_")
    aliases = {"allin": "all_in", "all-in": "all_in", "bet": "raise"}
    action = aliases.get(action, action)
    if action not in legal["actions"]:
        return None
    amount = raw.get("amount", 0)
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        amount = 0
    if action == "raise":
        presets = [value for key, value in legal["raise_presets"].items() if key != "all_in"]
        if not presets:
            return None
        amount = min(presets, key=lambda value: abs(value - amount)) if amount else min(presets)
    elif action == "all_in":
        amount = int(legal.get("stack") or legal.get("raise_presets", {}).get("all_in") or amount or 0)
    else:
        amount = 0
    table_talk = sanitize_table_talk(str(raw.get("table_talk", "The cards clink like tiny mugs.")))
    reasoning_hint = re.sub(r"\s+", " ", str(raw.get("reasoning_hint", ""))).strip()[:240]
    return {"action": action, "amount": amount, "reasoning_hint": reasoning_hint, "table_talk": table_talk or "The cards clink like tiny mugs."}


def sanitize_table_talk(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    leaked_markers = (
        "json",
        "markdown",
        "schema",
        "answer:",
        "one short line",
        "one short sentence",
        "short cozy",
        "poker banter",
        "table talk",
        "first sentence",
        "must be",
        "return only",
        "your response",
        "this response",
        "let me know",
        "what your",
        "your name",
        "name is",
        "wearing",
        "make sure",
        "don't mention",
        "do not mention",
        "think carefully",
        "correct action",
        "best move",
        "the user wants",
        "if you choose",
        "valid action",
        "legal action",
        "```",
        "{",
        "}",
        "\"action\"",
        "\"table_talk\"",
    )
    lowered = text.lower()
    if any(marker in lowered for marker in leaked_markers):
        return ""
    text = re.sub(r"\b\d+[kK]?\b", "", text)
    text = re.sub(r"\b(fold|folding|check|checking|call|calling|called|raise|raising|raised|all[-_ ]?in)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bI\s*(am|'m)?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bI'll\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^['’]m\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[2-9TJQKA][shdc♠♥♦♣]\b", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -,:;.\"'“”‘’")
    text = re.split(r"(?<=[.!?])\s+", text)[0].strip(" -,:;.\"'“”‘’")
    if not text or len(text.split()) < 3:
        return ""
    return text[:140]


def template_table_talk(profile: AgentProfile, action: str, state_summary: dict[str, Any] | None = None) -> str:
    by_action = {
        "fold": ["Too much smoke in that story for me.", "I will let that ghost pass by.", "My mug says patience tonight.", "The floorboards say this path is cursed.", "I prefer my cloak unsinged."],
        "check": ["The candle can burn a little longer.", "I will keep my chips warm for now.", "Let us see what the tavern whispers next.", "The room may speak before I do.", "No need to rattle the rafters yet."],
        "call": ["I am curious enough to stay by the fire.", "That tale is worth hearing out.", "I will keep you company on this road.", "The smoke has not scared me off.", "Pour another moment of suspense."],
        "raise": ["Let us put a little thunder in the room.", "The rafters could use a shake.", "I smell a story worth testing.", "The candlelight just leaned forward.", "A little pressure seasons the stew."],
        "all_in": ["The whole tavern gets to hear this one.", "No more sipping from tiny cups.", "Either the dragon wakes or I do.", "The bard should ready a louder verse.", "Every candle just stood at attention."],
    }
    options = by_action.get(action, ["The chips clink and the candles listen."])
    recent = set(state_summary.get("recent_chats", [])) if state_summary else set()
    available = [line for line in options if f"{profile.name}: {line}" not in recent and line not in recent] or options
    key = ""
    if state_summary:
        key = f":{state_summary.get('seed')}:{state_summary.get('street')}:{len(state_summary.get('history', []))}:{len(state_summary.get('recent_chats', []))}"
    rng = random.Random(f"{profile.name}:{action}{key}")
    return rng.choice(available)


def finalize_table_talk(profile: AgentProfile, action: str, text: str, state_summary: dict[str, Any] | None = None) -> str:
    talk = sanitize_table_talk(text)
    recent = set(state_summary.get("recent_chats", [])) if state_summary else set()
    if talk and f"{profile.name}: {talk}" not in recent and talk not in recent:
        return talk
    return template_table_talk(profile, action, state_summary)


def first_valid_decision(text: str, legal: dict[str, Any]) -> dict[str, Any] | None:
    for raw in parse_model_json_candidates(text):
        decision = validate_decision(raw, legal)
        if decision is not None:
            return decision
    return None


def apply_poker_sanity_guard(decision: dict[str, Any], state_summary: dict[str, Any]) -> dict[str, Any]:
    legal = state_summary["legal"]
    to_call = legal["to_call"]
    pot = state_summary["pot"]
    strength = estimate_strength(state_summary["hole_cards"], state_summary["community_cards"])
    price = to_call / max(1, pot + to_call)
    if decision["action"] in {"call", "all_in"} and "fold" in legal["actions"] and to_call >= max(120, pot * 2) and strength < 0.62:
        return {"action": "fold", "amount": 0, "reasoning_hint": "weak hand versus oversized all-in", "table_talk": "The all-in is too steep for these tavern cards."}
    if decision["action"] == "call" and "fold" in legal["actions"] and price > 0.42 and strength < 0.52:
        return {"action": "fold", "amount": 0, "reasoning_hint": "price too high for estimated strength", "table_talk": "The price is too smoky for this hand."}
    if decision["action"] in {"raise", "all_in"} and to_call == 0 and strength < 0.35:
        return {"action": "check", "amount": 0, "reasoning_hint": "weak hand with free option", "table_talk": "No need to wake the dragon just yet."}
    return decision


def safe_action(legal: dict[str, Any]) -> dict[str, Any]:
    if "check" in legal["actions"]:
        action = "check"
    elif "call" in legal["actions"]:
        action = "call"
    else:
        action = "fold"
    return {"action": action, "amount": 0, "table_talk": "A thoughtful pause settles over the tavern."}


def requires_gguf_runtime(model_id: str) -> bool:
    return "gguf" in model_id.lower()


def modal_runtime_family(model_id: str) -> str:
    if requires_gguf_runtime(model_id):
        return "gguf"
    if model_id == "openai/gpt-oss-20b":
        return "heavy_causal"
    if model_id in MULTIMODAL_MODAL_MODEL_IDS:
        return "multimodal"
    return "causal"


def modal_worker_class_name(model_id: str) -> str:
    return MODAL_WORKER_CLASS_BY_FAMILY[modal_runtime_family(model_id)]


class LocalRuntime:
    def __init__(self, max_new_tokens: int = 96, allow_fallback: bool | None = None):
        self.max_new_tokens = max_new_tokens
        self.allow_downloads = env_flag("TOKEN_HOLDEM_ALLOW_MODEL_DOWNLOADS")
        self.allow_fallback = deterministic_fallback_enabled() if allow_fallback is None else allow_fallback

    def decide(self, profile: AgentProfile, state_summary: dict[str, Any]) -> RuntimeDecision:
        model_id = SUPPORTED_TRANSFORMERS_MODELS.get(profile.name)
        if not model_id:
            log_event(logger, "model_runtime_unsupported", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name)
            return self._fallback_or_raise(profile, state_summary, f"No local Transformers mapping for {profile.name}")
        if requires_gguf_runtime(model_id):
            log_event(logger, "model_runtime_unsupported", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, model_id=model_id, reason="gguf_requires_llamacpp")
            return self._fallback_or_raise(profile, state_summary, f"{model_id} requires a GGUF/llama.cpp runtime; local runtime cannot call it")
        try:
            decision = self._generate(model_id, profile, state_summary)
        except Exception as exc:  # noqa: BLE001 - converted to a visible model-unavailable state.
            log_event(logger, "model_runtime_failed", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, error_type=exc.__class__.__name__, error=str(exc))
            return self._fallback_or_raise(profile, state_summary, f"Model failed: {exc.__class__.__name__}: {exc}")
        used_action_fallback = bool(decision.pop("_runtime_action_fallback", False))
        if used_action_fallback:
            log_event(logger, "model_runtime_partial_fallback", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, model_id=model_id, reason="invalid_decision_json", action=decision.get("action"), amount=decision.get("amount"))
            if self.allow_fallback:
                return RuntimeDecision(decision, "local_model_partial_fallback", f"{model_id}; invalid decision JSON, used persona fallback action")
            raise ModelRuntimeUnavailable(f"{profile.name}: local model returned invalid decision JSON")
        log_event(logger, "model_runtime_success", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, model_id=model_id, action=decision.get("action"), amount=decision.get("amount"))
        return RuntimeDecision(decision, "local_model", model_id)

    def _fallback_or_raise(self, profile: AgentProfile, state_summary: dict[str, Any], status: str) -> RuntimeDecision:
        if self.allow_fallback:
            return persona_fallback_decision(profile, state_summary, status)
        raise ModelRuntimeUnavailable(f"{profile.name}: {status}")

    def _generate(self, model_id: str, profile: AgentProfile, state_summary: dict[str, Any]) -> dict[str, Any]:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, local_files_only=not self.allow_downloads)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype="auto",
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            local_files_only=not self.allow_downloads,
        )
        prompt = build_prompt(profile, state_summary)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = tokenizer.decode(output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
        decision = first_valid_decision(generated, state_summary["legal"])
        decision = apply_poker_sanity_guard(decision, state_summary) if decision is not None else None
        log_event(logger, "model_runtime_generated", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), model_id=model_id, raw_text=generated[:500], parsed=decision, valid=decision is not None)
        if decision is None:
            if not self.allow_fallback:
                raise ModelRuntimeUnavailable(f"{profile.name}: local model returned invalid decision JSON")
            decision = apply_poker_sanity_guard(fallback_decide(profile, state_summary, seed=state_summary.get("seed")), state_summary)
            decision["_runtime_action_fallback"] = True
        talk = self._generate_table_talk(model, tokenizer, profile, decision["action"], state_summary)
        decision["table_talk"] = finalize_table_talk(profile, decision["action"], talk, state_summary)
        if decision.get("_runtime_action_fallback"):
            decision["reasoning_hint"] = "model decision JSON invalid; used persona fallback action with generated banter"
        del model
        del tokenizer
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return decision

    def _generate_table_talk(self, model, tokenizer, profile: AgentProfile, final_action: str, state_summary: dict[str, Any]) -> str:
        import torch

        prompt = build_table_talk_prompt(profile, final_action, state_summary)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=48,
                do_sample=True,
                temperature=0.9,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = tokenizer.decode(output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
        raw = parse_model_json(generated)
        talk = sanitize_table_talk(str(raw.get("table_talk", ""))) if raw else sanitize_table_talk(generated)
        log_event(logger, "model_table_talk_generated", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, final_action=final_action, raw_text=generated[:300], table_talk=talk)
        return talk


class DeterministicDevRuntime:
    def decide(self, profile: AgentProfile, state_summary: dict[str, Any]) -> RuntimeDecision:
        decision = apply_poker_sanity_guard(fallback_decide(profile, state_summary, seed=state_summary.get("seed")), state_summary)
        decision["table_talk"] = template_table_talk(profile, decision["action"], state_summary)
        log_event(
            logger,
            "model_runtime_deterministic_dev",
            session_id=state_summary.get("session_id", ""),
            hand_id=state_summary.get("hand_id", ""),
            orbit_id=state_summary.get("orbit_id", ""),
            player=profile.name,
            action=decision.get("action"),
            amount=decision.get("amount"),
        )
        return RuntimeDecision(decision, "deterministic_dev", "TOKEN_HOLDEM_ALLOW_DETERMINISTIC_BOTS=1")


class ModalRuntime:
    def __init__(
        self,
        local_runtime: InferenceRuntime | None = None,
        *,
        app_name: str | None = None,
        function_name: str = "run_agent_decision",
        timeout_seconds: float | None = None,
        enabled_model_names: set[str] | None = None,
        remote_function: Any | None = None,
        remote_workers: dict[str, Any] | None = None,
    ):
        self.local_runtime = local_runtime or LocalRuntime()
        self.app_name = app_name or os.getenv("TOKEN_HOLDEM_MODAL_APP_NAME", "token-holdem-inference")
        self.function_name = function_name
        self.timeout_seconds = timeout_seconds or float(os.getenv("TOKEN_HOLDEM_MODAL_TIMEOUT_SECONDS", str(DEFAULT_MODAL_TIMEOUT_SECONDS)))
        self.enabled_model_names = enabled_model_names if enabled_model_names is not None else configured_modal_model_names()
        self._remote_function = remote_function
        self._remote_workers = remote_workers or {}

    def decide(self, profile: AgentProfile, state_summary: dict[str, Any]) -> RuntimeDecision:
        if profile.name not in self.enabled_model_names:
            message = f"{profile.name} is disabled by TOKEN_HOLDEM_MODAL_MODEL_NAMES"
            log_event(logger, "model_runtime_modal_disabled", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, model_id=profile.model_id, reason=message)
            raise ModelRuntimeUnavailable(message)
        model_id = SUPPORTED_TRANSFORMERS_MODELS.get(profile.name, profile.model_id)
        worker_class = modal_worker_class_name(model_id)
        try:
            log_event(logger, "model_runtime_modal_call_started", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, model_id=model_id, app_name=self.app_name, worker_class=worker_class)
            response = self._call_remote(profile, model_id, state_summary)
        except Exception as exc:  # noqa: BLE001 - converted to a visible model-unavailable state.
            log_event(logger, "model_runtime_modal_failed", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, model_id=model_id, error_type=exc.__class__.__name__, error=str(exc))
            raise ModelRuntimeUnavailable(f"{profile.name}: Modal inference unavailable: {exc.__class__.__name__}: {exc}") from exc
        if response.get("error"):
            log_event(logger, "model_runtime_modal_failed", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, model_id=model_id, error=response["error"], raw_text=str(response.get("raw_model_output", ""))[:500])
            raise ModelRuntimeUnavailable(f"{profile.name}: Modal inference returned an error: {response['error']}")
        decision = validate_decision(
            {
                "action": response.get("action"),
                "amount": response.get("bet_amount"),
                "reasoning_hint": response.get("explanation", ""),
                "table_talk": response.get("commentary", ""),
            },
            state_summary["legal"],
        )
        if decision is None:
            log_event(logger, "model_runtime_modal_failed", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, model_id=model_id, error="invalid_remote_decision", raw_text=str(response.get("raw_model_output", ""))[:500])
            raise ModelRuntimeUnavailable(f"{profile.name}: Modal inference returned an invalid decision")
        decision = apply_poker_sanity_guard(decision, state_summary)
        decision["table_talk"] = finalize_table_talk(profile, decision["action"], decision.get("table_talk", ""), state_summary)
        log_event(logger, "model_runtime_modal_success", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, model_id=model_id, action=decision.get("action"), amount=decision.get("amount"), raw_text=str(response.get("raw_model_output", ""))[:500])
        return RuntimeDecision(decision, "modal_model", model_id)

    def _call_remote(self, profile: AgentProfile, model_id: str, state_summary: dict[str, Any]) -> dict[str, Any]:
        if self._remote_function is not None:
            return self._call_legacy_remote_function(profile, model_id, state_summary)
        worker_class_name = modal_worker_class_name(model_id)
        worker_cls = self._remote_workers.get(worker_class_name) or self._lookup_remote_worker_class(worker_class_name)
        worker = worker_cls(model_id=model_id)
        call = worker.decide.spawn(
            state_summary,
            profile.name,
            profile.persona,
            state_summary["legal"],
            build_prompt(profile, state_summary),
        )
        response = call.get(timeout=self.timeout_seconds)
        if not isinstance(response, dict):
            raise TypeError(f"Expected Modal response dict, got {type(response).__name__}")
        return response

    def _call_legacy_remote_function(self, profile: AgentProfile, model_id: str, state_summary: dict[str, Any]) -> dict[str, Any]:
        remote_function = self._remote_function or self._lookup_remote_function()
        call = remote_function.spawn(
            state_summary,
            profile.name,
            profile.persona,
            model_id,
            state_summary["legal"],
            build_prompt(profile, state_summary),
        )
        response = call.get(timeout=self.timeout_seconds)
        if not isinstance(response, dict):
            raise TypeError(f"Expected Modal response dict, got {type(response).__name__}")
        return response

    def _lookup_remote_worker_class(self, worker_class_name: str) -> Any:
        import modal

        worker_cls = modal.Cls.from_name(self.app_name, worker_class_name)
        self._remote_workers[worker_class_name] = worker_cls
        return worker_cls

    def _lookup_remote_function(self) -> Any:
        import modal

        self._remote_function = modal.Function.from_name(self.app_name, self.function_name)
        return self._remote_function


TransformersRuntime = LocalRuntime


def get_model_runtime() -> InferenceRuntime:
    if deterministic_fallback_enabled() and not env_flag("USE_MODAL_INFERENCE"):
        return DeterministicDevRuntime()
    local_runtime = LocalRuntime()
    if env_flag("USE_MODAL_INFERENCE"):
        return ModalRuntime(local_runtime=local_runtime)
    return local_runtime
