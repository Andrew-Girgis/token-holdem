from __future__ import annotations

import gc
import json
import random
import re
from dataclasses import dataclass
from typing import Any

from token_holdem.agents import AgentProfile, estimate_strength, fallback_decide
from token_holdem.logging_utils import get_logger, log_event


logger = get_logger("token_holdem.model_runtime")


SUPPORTED_TRANSFORMERS_MODELS = {
    "Nemotron Nano": "Qwen/Qwen3-0.6B",
    "Qwen": "Qwen/Qwen3-0.6B",
    "Gemma": "Qwen/Qwen3-0.6B",
    "Cohere North Mini": "Qwen/Qwen3-0.6B",
    "Mistral": "Qwen/Qwen3-0.6B",
    "OpenAI Open Model 20B": "Qwen/Qwen3-0.6B",
}


@dataclass
class RuntimeDecision:
    decision: dict[str, Any]
    source: str
    status: str


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
- amount: zero unless action is raise; for raise use one raise preset value
- reasoning_hint: brief private poker reason

Do not include public table talk here. Do not include examples. If facing a large all-in with a weak hand, fold.
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
    text = re.sub(r"\s+", " ", text).strip(" -,:;.")
    text = re.split(r"(?<=[.!?])\s+", text)[0].strip(" -,:;.")
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


class TransformersRuntime:
    def __init__(self, max_new_tokens: int = 96):
        self.max_new_tokens = max_new_tokens

    def decide(self, profile: AgentProfile, state_summary: dict[str, Any]) -> RuntimeDecision:
        model_id = SUPPORTED_TRANSFORMERS_MODELS.get(profile.name)
        if not model_id:
            decision = apply_poker_sanity_guard(fallback_decide(profile, state_summary, seed=state_summary.get("seed")), state_summary)
            decision["table_talk"] = template_table_talk(profile, decision["action"], state_summary)
            log_event(logger, "model_runtime_unsupported", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name)
            return RuntimeDecision(
                decision,
                "fallback",
                f"No local Transformers mapping for {profile.name}",
            )
        try:
            decision = self._generate(model_id, profile, state_summary)
        except Exception as exc:  # noqa: BLE001 - runtime fallback must catch model/load failures.
            decision = apply_poker_sanity_guard(fallback_decide(profile, state_summary, seed=state_summary.get("seed")), state_summary)
            decision["table_talk"] = template_table_talk(profile, decision["action"], state_summary)
            log_event(logger, "model_runtime_failed", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, error_type=exc.__class__.__name__, error=str(exc))
            return RuntimeDecision(
                decision,
                "fallback",
                f"Model failed: {exc.__class__.__name__}: {exc}",
            )
        log_event(logger, "model_runtime_success", session_id=state_summary.get("session_id", ""), hand_id=state_summary.get("hand_id", ""), orbit_id=state_summary.get("orbit_id", ""), player=profile.name, model_id=model_id, action=decision.get("action"), amount=decision.get("amount"))
        return RuntimeDecision(decision, "local_model", model_id)

    def _generate(self, model_id: str, profile: AgentProfile, state_summary: dict[str, Any]) -> dict[str, Any]:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype="auto",
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
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
        used_decision_fallback = decision is None
        if decision is None:
            decision = apply_poker_sanity_guard(fallback_decide(profile, state_summary, seed=state_summary.get("seed")), state_summary)
        talk = self._generate_table_talk(model, tokenizer, profile, decision["action"], state_summary)
        decision["table_talk"] = finalize_table_talk(profile, decision["action"], talk, state_summary)
        if used_decision_fallback:
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
