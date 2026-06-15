from __future__ import annotations

from collections import Counter
from itertools import combinations

from treys import Card, Evaluator


_EVALUATOR = Evaluator()
_RANK_VALUES = {rank: idx for idx, rank in enumerate("23456789TJQKA", start=2)}
_RANK_NAMES = {
    "2": "twos",
    "3": "threes",
    "4": "fours",
    "5": "fives",
    "6": "sixes",
    "7": "sevens",
    "8": "eights",
    "9": "nines",
    "T": "tens",
    "J": "jacks",
    "Q": "queens",
    "K": "kings",
    "A": "aces",
}
_HIGH_CARD_NAMES = {
    "2": "deuce",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
    "T": "ten",
    "J": "jack",
    "Q": "queen",
    "K": "king",
    "A": "ace",
}


def score_hand(hole_cards: list[str], community_cards: list[str]) -> int:
    return _EVALUATOR.evaluate(
        [Card.new(card) for card in community_cards],
        [Card.new(card) for card in hole_cards],
    )


def _rank_value(rank: str) -> int:
    return _RANK_VALUES[rank]


def hand_class(score: int) -> str:
    return _EVALUATOR.class_to_string(_EVALUATOR.get_rank_class(score))


def hand_summary(hole_cards: list[str], community_cards: list[str]) -> tuple[int, str, str]:
    score = score_hand(hole_cards, community_cards)
    class_name = hand_class(score)
    return score, class_name, describe_best_hand(hole_cards, community_cards)


def describe_best_hand(hole_cards: list[str], community_cards: list[str]) -> str:
    cards = hole_cards + community_cards
    best_five = min(combinations(cards, 5), key=lambda hand: score_hand([], list(hand)))
    class_name = hand_class(score_hand([], list(best_five)))
    ranks = [card[0] for card in best_five]
    counts = Counter(ranks)
    ordered_ranks = sorted(counts, key=lambda rank: (_RANK_VALUES[rank], counts[rank]), reverse=True)

    if class_name == "High Card":
        return f"High Card, {_HIGH_CARD_NAMES[ordered_ranks[0]]} high"
    if class_name == "Pair":
        pair = max((rank for rank, count in counts.items() if count == 2), key=_rank_value)
        kicker = max((rank for rank, count in counts.items() if count == 1), key=_rank_value)
        return f"Pair, {_RANK_NAMES[pair]}, {_HIGH_CARD_NAMES[kicker]} kicker"
    if class_name == "Two Pair":
        pairs = sorted((rank for rank, count in counts.items() if count == 2), key=_rank_value, reverse=True)
        kicker = next(rank for rank, count in counts.items() if count == 1)
        return f"Two Pair, {_RANK_NAMES[pairs[0]]} and {_RANK_NAMES[pairs[1]]}, {_HIGH_CARD_NAMES[kicker]} kicker"
    if class_name == "Three of a Kind":
        trips = max((rank for rank, count in counts.items() if count == 3), key=_rank_value)
        kicker = max((rank for rank, count in counts.items() if count == 1), key=_rank_value)
        return f"Three of a Kind, {_RANK_NAMES[trips]}, {_HIGH_CARD_NAMES[kicker]} kicker"
    if class_name == "Straight":
        return f"Straight, {_HIGH_CARD_NAMES[_straight_high(ranks)]} high"
    if class_name == "Flush":
        return f"Flush, {_HIGH_CARD_NAMES[ordered_ranks[0]]} high"
    if class_name == "Full House":
        trips = max((rank for rank, count in counts.items() if count == 3), key=_rank_value)
        pair = max((rank for rank, count in counts.items() if count == 2), key=_rank_value)
        return f"Full House, {_RANK_NAMES[trips]} over {_RANK_NAMES[pair]}"
    if class_name == "Four of a Kind":
        quads = next(rank for rank, count in counts.items() if count == 4)
        kicker = next(rank for rank, count in counts.items() if count == 1)
        return f"Four of a Kind, {_RANK_NAMES[quads]}, {_HIGH_CARD_NAMES[kicker]} kicker"
    if class_name == "Straight Flush":
        return f"Straight Flush, {_HIGH_CARD_NAMES[_straight_high(ranks)]} high"
    return class_name


def _straight_high(ranks: list[str]) -> str:
    values = {_RANK_VALUES[rank] for rank in ranks}
    if values == {14, 5, 4, 3, 2}:
        return "5"
    high_value = max(values)
    return next(rank for rank, value in _RANK_VALUES.items() if value == high_value)


def best_players(player_cards: dict[str, list[str]], community_cards: list[str]) -> tuple[list[str], int, str]:
    scores = {player_id: score_hand(cards, community_cards) for player_id, cards in player_cards.items()}
    best_score = min(scores.values())
    winners = [player_id for player_id, score in scores.items() if score == best_score]
    return winners, best_score, hand_class(best_score)
