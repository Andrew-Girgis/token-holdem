from __future__ import annotations

import random

RANKS = "23456789TJQKA"
SUITS = "shdc"
SUIT_SYMBOLS = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
RED_SUITS = {"h", "d"}


def new_deck(seed: int | None = None) -> list[str]:
    deck = [rank + suit for suit in SUITS for rank in RANKS]
    rng = random.Random(seed)
    rng.shuffle(deck)
    return deck


def card_label(card: str) -> str:
    return f"{card[0]}{SUIT_SYMBOLS[card[1]]}"


def cards_label(cards: list[str]) -> str:
    return " ".join(card_label(card) for card in cards) if cards else "-"


def card_html(card: str, hidden: bool = False) -> str:
    if hidden:
        return '<span class="card hidden-card">??</span>'
    suit = card[1]
    color = " red-card" if suit in RED_SUITS else ""
    return f'<span class="card{color}">{card_label(card)}</span>'


def cards_html(cards: list[str], hidden: bool = False) -> str:
    return "".join(card_html(card, hidden=hidden) for card in cards)
