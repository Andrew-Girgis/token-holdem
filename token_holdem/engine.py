from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from token_holdem.cards import cards_label, new_deck
from token_holdem.evaluator import best_players, hand_summary
from token_holdem.logging_utils import get_logger, log_event


logger = get_logger("token_holdem.engine")


STARTING_STACK = 1_000
SMALL_BLIND = 10
BIG_BLIND = 20


class Street(StrEnum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    COMPLETE = "complete"


@dataclass
class PlayerState:
    id: str
    name: str
    stack: int = STARTING_STACK
    hole_cards: list[str] = field(default_factory=list)
    folded: bool = False
    all_in: bool = False
    bet: int = 0
    contributed: int = 0
    is_human: bool = False


@dataclass
class HandResult:
    winners: list[str]
    pot: int
    board: list[str]
    hand_name: str
    deltas: dict[str, int]
    summary: str
    showdown: dict[str, str] = field(default_factory=dict)
    pot_awards: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GameState:
    players: list[PlayerState]
    dealer_index: int = 0
    small_blind: int = SMALL_BLIND
    big_blind: int = BIG_BLIND
    seed: int | None = None
    session_id: str = ""
    hand_id: str = ""
    orbit_id: str = ""
    deck: list[str] = field(default_factory=list)
    community_cards: list[str] = field(default_factory=list)
    street: Street = Street.PREFLOP
    current_bet: int = 0
    current_player_index: int = 0
    small_blind_index: int | None = None
    big_blind_index: int | None = None
    last_raise: int = BIG_BLIND
    action_log: list[str] = field(default_factory=list)
    acted_player_ids: set[str] = field(default_factory=set)
    result: HandResult | None = None
    starting_stacks: dict[str, int] = field(default_factory=dict)

    def start_hand(self) -> None:
        self.deck = new_deck(self.seed)
        self.community_cards = []
        self.street = Street.PREFLOP
        self.current_bet = self.big_blind
        self.last_raise = self.big_blind
        self.action_log = []
        self.acted_player_ids = set()
        self.result = None
        self.starting_stacks = {player.id: player.stack for player in self.players}
        for player in self.players:
            player.hole_cards = [self.deck.pop(), self.deck.pop()]
            player.folded = False
            player.all_in = False
            player.bet = 0
            player.contributed = 0

        if len(self.active_players()) < 2:
            raise ValueError("At least two players with chips are required")

        sb_index = self.dealer_index if len(self.active_players()) == 2 else self.next_active_index(self.dealer_index)
        bb_index = self.next_active_index(sb_index)
        self.small_blind_index = sb_index
        self.big_blind_index = bb_index
        self.post_blind(sb_index, self.small_blind, "small blind")
        self.post_blind(bb_index, self.big_blind, "big blind")
        self.current_player_index = self.next_active_index(bb_index)
        log_event(
            logger,
            "hand_started",
            seed=self.seed,
            session_id=self.session_id,
            hand_id=self.hand_id,
            orbit_id=self.orbit_id,
            players=[player.name for player in self.players],
            button=self.players[self.dealer_index].name,
            small_blind=self.players[sb_index].name,
            big_blind=self.players[bb_index].name,
            pot=self.pot(),
        )

    def active_players(self) -> list[PlayerState]:
        return [player for player in self.players if player.stack > 0 or player.contributed > 0]

    def live_players(self) -> list[PlayerState]:
        return [player for player in self.players if not player.folded]

    def actionable_players(self) -> list[PlayerState]:
        return [player for player in self.live_players() if not player.all_in and player.stack > 0]

    def player(self, player_id: str) -> PlayerState:
        return next(player for player in self.players if player.id == player_id)

    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def pot(self) -> int:
        return sum(player.contributed for player in self.players)

    def amount_to_call(self, player: PlayerState) -> int:
        return max(0, self.current_bet - player.bet)

    def legal_actions(self, player_id: str | None = None) -> dict[str, Any]:
        player = self.player(player_id) if player_id else self.current_player()
        to_call = min(self.amount_to_call(player), player.stack)
        actions: list[str] = []
        if to_call == 0:
            actions.append("check")
        else:
            actions.extend(["fold", "call"])
        if player.stack > to_call:
            actions.append("raise")
        if player.stack > 0:
            actions.append("all_in")

        min_raise_to = self.current_bet + self.last_raise
        min_raise_amount = max(0, min_raise_to - player.bet)
        half_pot = to_call + max(self.big_blind, self.pot() // 2)
        pot_raise = to_call + max(self.big_blind, self.pot())
        presets = {
            "min": min(player.stack, max(min_raise_amount, to_call + self.big_blind)),
            "half_pot": min(player.stack, max(half_pot, min_raise_amount)),
            "pot": min(player.stack, max(pot_raise, min_raise_amount)),
            "all_in": player.stack,
        }
        if "raise" not in actions:
            presets = {"all_in": player.stack}
        return {"actions": actions, "to_call": to_call, "raise_presets": presets}

    def apply_action(self, action: str, amount: int = 0) -> None:
        if self.street in {Street.SHOWDOWN, Street.COMPLETE} or self.result:
            return
        player = self.current_player()
        legal = self.legal_actions(player.id)
        requested_action = action
        requested_amount = amount
        action = self._repair_action(action, amount, legal)
        amount = self._repair_amount(action, amount, legal)
        log_event(
            logger,
            "action_applied",
            player=player.name,
            street=self.street.value,
            requested_action=requested_action,
            requested_amount=requested_amount,
            action=action,
            amount=amount,
            legal=legal,
            session_id=self.session_id,
            hand_id=self.hand_id,
            orbit_id=self.orbit_id,
            pot_before=self.pot(),
            stack_before=player.stack,
        )

        if action == "fold":
            player.folded = True
            self.acted_player_ids.add(player.id)
            self.action_log.append(f"{player.name} folds")
        elif action == "check":
            self.acted_player_ids.add(player.id)
            self.action_log.append(f"{player.name} checks")
        elif action == "call":
            paid = self.take_chips(player, legal["to_call"])
            self.acted_player_ids.add(player.id)
            self.action_log.append(f"{player.name} calls {paid}")
        elif action == "raise":
            previous_bet = player.bet
            previous_current_bet = self.current_bet
            paid = self.take_chips(player, amount)
            self.current_bet = max(self.current_bet, player.bet)
            self.last_raise = max(self.big_blind, self.current_bet - previous_bet)
            self.acted_player_ids = {player.id}
            if previous_current_bet == 0:
                self.action_log.append(f"{player.name} bets {paid}")
            else:
                self.action_log.append(f"{player.name} raises to {player.bet}")
        elif action == "all_in":
            previous_bet = player.bet
            previous_current_bet = self.current_bet
            paid = self.take_chips(player, player.stack)
            if player.bet > self.current_bet:
                self.current_bet = player.bet
                self.last_raise = max(self.big_blind, self.current_bet - previous_bet)
                self.acted_player_ids = {player.id}
            else:
                self.acted_player_ids.add(player.id)
            if player.bet > previous_current_bet:
                self.action_log.append(f"{player.name} jams for {paid} more ({player.bet} total)")
            else:
                self.action_log.append(f"{player.name} calls all-in for {paid}")

        self.advance_after_action()

    def post_blind(self, index: int, amount: int, label: str) -> None:
        player = self.players[index]
        paid = self.take_chips(player, amount)
        self.action_log.append(f"{player.name} posts {label} {paid}")

    def take_chips(self, player: PlayerState, amount: int) -> int:
        paid = min(max(0, amount), player.stack)
        player.stack -= paid
        player.bet += paid
        player.contributed += paid
        if player.stack == 0:
            player.all_in = True
        return paid

    def advance_after_action(self) -> None:
        if len(self.live_players()) == 1:
            self.finish_without_showdown()
            return
        if self.betting_round_complete():
            self.advance_street()
            return
        self.current_player_index = self.next_actionable_index(self.current_player_index)

    def betting_round_complete(self) -> bool:
        actionable = self.actionable_players()
        if not actionable:
            return True
        return all(player.bet == self.current_bet and player.id in self.acted_player_ids for player in actionable)

    def advance_street(self) -> None:
        for player in self.players:
            player.bet = 0
        self.acted_player_ids = set()
        self.current_bet = 0
        self.last_raise = self.big_blind
        if self.street == Street.PREFLOP:
            self.community_cards.extend([self.deck.pop(), self.deck.pop(), self.deck.pop()])
            self.street = Street.FLOP
            self.action_log.append(f"Flop: {cards_label(self.community_cards)}")
        elif self.street == Street.FLOP:
            self.community_cards.append(self.deck.pop())
            self.street = Street.TURN
            self.action_log.append(f"Turn: {cards_label(self.community_cards)}")
        elif self.street == Street.TURN:
            self.community_cards.append(self.deck.pop())
            self.street = Street.RIVER
            self.action_log.append(f"River: {cards_label(self.community_cards)}")
        elif self.street == Street.RIVER:
            self.finish_showdown()
            return
        if not self.actionable_players():
            self.advance_street()
            return
        self.current_player_index = self.next_actionable_index(self.dealer_index)

    def finish_without_showdown(self) -> None:
        winner = self.live_players()[0]
        pot = self.pot()
        winner.stack += pot
        self.street = Street.COMPLETE
        self._set_result([winner.id], pot, "No showdown", f"{winner.name} wins {pot} after everyone else folds.")

    def finish_showdown(self) -> None:
        live_players = self.live_players()
        contenders = {player.id: player.hole_cards for player in live_players}
        winners, _score, hand_name = best_players(contenders, self.community_cards)
        showdown = {player.id: hand_summary(player.hole_cards, self.community_cards)[2] for player in self.live_players()}
        pot = self.pot()
        awards = self._award_showdown_pots()
        result_winners = []
        for award in awards:
            for player_id in award["winners"]:
                if player_id not in result_winners:
                    result_winners.append(player_id)
        for award in awards:
            share = award["amount"] // len(award["winners"])
            remainder = award["amount"] % len(award["winners"])
            for idx, player_id in enumerate(award["winners"]):
                self.player(player_id).stack += share + (1 if idx < remainder else 0)
        names = ", ".join(self.player(player_id).name for player_id in winners)
        self.street = Street.COMPLETE
        summary = f"{names} win {pot} with {hand_name}."
        if len(awards) > 1 or set(awards[0]["winners"]) != set(winners):
            parts = []
            for award in awards:
                award_names = ", ".join(self.player(player_id).name for player_id in award["winners"])
                parts.append(f"{award_names} win {award['amount']} with {award['hand_name']}")
            summary = "Side pots: " + "; ".join(parts) + "."
        self._set_result(result_winners or winners, pot, hand_name, summary, showdown=showdown, pot_awards=awards)

    def _award_showdown_pots(self) -> list[dict[str, Any]]:
        awards: list[dict[str, Any]] = []
        previous_level = 0
        levels = sorted({player.contributed for player in self.players if player.contributed > 0})
        for level in levels:
            contributors = [player for player in self.players if player.contributed >= level]
            amount = (level - previous_level) * len(contributors)
            eligible = [player for player in contributors if not player.folded]
            previous_level = level
            if amount <= 0 or not eligible:
                continue
            contenders = {player.id: player.hole_cards for player in eligible}
            winners, _score, hand_name = best_players(contenders, self.community_cards)
            awards.append({"amount": amount, "winners": winners, "hand_name": hand_name})
        return awards

    def _set_result(self, winners: list[str], pot: int, hand_name: str, summary: str, showdown: dict[str, str] | None = None, pot_awards: list[dict[str, Any]] | None = None) -> None:
        deltas = {player.id: player.stack - self.starting_stacks[player.id] for player in self.players}
        self.result = HandResult(winners=winners, pot=pot, board=list(self.community_cards), hand_name=hand_name, deltas=deltas, summary=summary, showdown=showdown or {}, pot_awards=pot_awards or [])
        self.action_log.append(summary)
        log_event(
            logger,
            "hand_completed",
            winners=winners,
            session_id=self.session_id,
            hand_id=self.hand_id,
            orbit_id=self.orbit_id,
            pot=pot,
            hand_name=hand_name,
            board=self.community_cards,
            deltas=deltas,
            showdown=showdown or {},
            pot_awards=pot_awards or [],
            summary=summary,
        )

    def next_active_index(self, start_index: int) -> int:
        return self._next_index(start_index, lambda player: player.stack > 0)

    def next_actionable_index(self, start_index: int) -> int:
        return self._next_index(start_index, lambda player: not player.folded and not player.all_in and player.stack > 0)

    def _next_index(self, start_index: int, predicate) -> int:
        for offset in range(1, len(self.players) + 1):
            idx = (start_index + offset) % len(self.players)
            if predicate(self.players[idx]):
                return idx
        return start_index

    def _repair_action(self, action: str, amount: int, legal: dict[str, Any]) -> str:
        action = (action or "").lower().strip()
        if action in legal["actions"]:
            return action
        if legal["to_call"] == 0:
            return "check"
        if "call" in legal["actions"]:
            return "call"
        return "fold"

    def _repair_amount(self, action: str, amount: int, legal: dict[str, Any]) -> int:
        if action != "raise":
            return 0
        presets = legal["raise_presets"]
        legal_amounts = [value for key, value in presets.items() if key != "all_in" and value > legal["to_call"]]
        if not legal_amounts:
            return 0
        if amount <= 0:
            return min(legal_amounts)
        return min(legal_amounts, key=lambda value: abs(value - amount))


def make_players(names: list[str], human_name: str | None = None) -> list[PlayerState]:
    players: list[PlayerState] = []
    if human_name:
        players.append(PlayerState(id="human", name=human_name, is_human=True))
    for idx, name in enumerate(names):
        players.append(PlayerState(id=f"ai_{idx}", name=name))
    return players
