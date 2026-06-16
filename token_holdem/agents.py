from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentProfile:
    name: str
    model_id: str
    persona: str
    aggression: float
    chaos: float
    talk: tuple[str, ...]


ROSTER: list[AgentProfile] = [
    AgentProfile(
        "Nemotron Nano",
        "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF",
        "cold machine precision, unemotional, calculating",
        0.45,
        0.12,
        ("The tensor smoke says patience.", "I compute. I sip. I continue.", "A clean line through a messy tavern."),
    ),
    AgentProfile(
        "Qwen",
        "Qwen/Qwen3-0.6B",
        "analytical and exacting",
        0.38,
        0.08,
        ("The pot odds are whispering.", "I prefer arithmetic to panic.", "Let us reason by candlelight."),
    ),
    AgentProfile(
        "Gemma",
        "google/gemma-4-12B-it",
        "cautious, methodical, warm",
        0.30,
        0.06,
        ("Tiny steps, tidy chips.", "I will not chase every ghost.", "A careful fold is still a story."),
    ),
    AgentProfile(
        "Cohere Command R7B",
        "CohereLabs/c4ai-command-r7b-12-2024",
        "commanding, multilingual, tactical",
        0.55,
        0.32,
        ("The cards are drawing a route.", "I will command the margin.", "A precise detour enters the pot."),
    ),
    AgentProfile(
        "Mistral",
        "mistralai/Mistral-7B-Instruct-v0.2",
        "sharp, fast, aggressive",
        0.70,
        0.18,
        ("Wind at my back, chips in the middle.", "I came here to apply pressure.", "No dust settles on this stack."),
    ),
    AgentProfile(
        "OpenAI Open Model 20B",
        "openai/gpt-oss-20b",
        "confident, strategic, theatrical",
        0.58,
        0.16,
        ("Observe the drama of expected value.", "I narrate, therefore I raise.", "A bold hypothesis enters the pot."),
    ),
    AgentProfile(
        "Llama Scout",
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "curious, adaptive, observant",
        0.50,
        0.14,
        ("I watched the candle flicker before calling.", "Small stack, wide eyes, steady hand.", "The table has patterns if you listen."),
    ),
]


def decide(profile: AgentProfile, state_summary: dict[str, Any], seed: int | None = None) -> dict[str, Any]:
    rng = random.Random(f"{seed}:{profile.name}:{state_summary.get('hand_no')}:{state_summary.get('street')}:{len(state_summary.get('history', []))}")
    legal = state_summary["legal"]
    actions: list[str] = legal["actions"]
    to_call = legal["to_call"]
    stack = state_summary["stack"]
    strength = estimate_strength(state_summary["hole_cards"], state_summary["community_cards"])
    pressure = min(1.0, to_call / max(1, stack))
    bluff_roll = rng.random() < profile.aggression * (0.25 + profile.chaos)

    action = "check" if "check" in actions else "call"
    amount = 0
    if "raise" in actions and (strength + profile.aggression * 0.35 > 0.72 or bluff_roll):
        action = "raise"
        preset_name = "pot" if profile.aggression > 0.6 and rng.random() > 0.35 else "half_pot"
        if profile.chaos > 0.25 and rng.random() > 0.65:
            preset_name = "min"
        amount = legal["raise_presets"].get(preset_name, legal["raise_presets"].get("min", 0))
    elif "fold" in actions and ((strength < 0.34 and pressure > 0.18) or (strength < 0.55 and pressure > 0.45)) and rng.random() > profile.chaos:
        action = "fold"
    elif "call" in actions:
        action = "call"
    elif "check" in actions:
        action = "check"

    if "all_in" in actions and stack < 140 and (strength > 0.68 or rng.random() < profile.chaos * 0.25):
        action = "all_in"
        amount = 0

    return {"action": action, "amount": amount, "table_talk": rng.choice(profile.talk)}


def fallback_decide(profile: AgentProfile, state_summary: dict[str, Any], seed: int | None = None) -> dict[str, Any]:
    return decide(profile, state_summary, seed=seed)


def estimate_strength(hole_cards: list[str], community_cards: list[str]) -> float:
    ranks = "23456789TJQKA"
    values = sorted([ranks.index(card[0]) + 2 for card in hole_cards], reverse=True)
    suited = hole_cards[0][1] == hole_cards[1][1]
    pair = values[0] == values[1]
    connected = abs(values[0] - values[1]) <= 2
    score = (values[0] / 14) * 0.38 + (values[1] / 14) * 0.22
    if pair:
        score += 0.28
    if suited:
        score += 0.07
    if connected:
        score += 0.05
    if community_cards:
        board_ranks = {card[0] for card in community_cards}
        if any(card[0] in board_ranks for card in hole_cards):
            score += 0.12
        suits = [card[1] for card in community_cards]
        for suit in "shdc":
            if suits.count(suit) >= 4:
                if any(card[1] == suit for card in hole_cards):
                    score = max(score, 0.78)
                else:
                    score = min(score, 0.18)
    return min(1.0, score)


def profile_by_name(name: str) -> AgentProfile:
    return next(profile for profile in ROSTER if profile.name == name)
