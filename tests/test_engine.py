from token_holdem.engine import GameState, PlayerState, Street, make_players
from token_holdem.evaluator import best_players, describe_best_hand


def test_hand_starts_with_blinds_and_hole_cards():
    game = GameState(players=make_players(["A", "B", "C"]), seed=7)
    game.start_hand()

    assert game.street == Street.PREFLOP
    assert game.pot() == 30
    assert all(len(player.hole_cards) == 2 for player in game.players)
    assert game.current_player().name == "A"


def test_fold_awards_pot_without_showdown():
    game = GameState(players=make_players(["A", "B"]), seed=1)
    game.start_hand()

    game.apply_action("fold")

    assert game.result is not None
    assert game.result.pot == 30
    assert game.result.winners == ["ai_1"]
    assert game.street == Street.COMPLETE


def test_all_in_advances_to_showdown():
    game = GameState(players=make_players(["A", "B"]), seed=3)
    game.start_hand()

    game.apply_action("all_in")
    game.apply_action("all_in")

    assert game.result is not None
    assert game.street == Street.COMPLETE
    assert len(game.community_cards) == 5
    assert sum(game.result.deltas.values()) == 0


def test_new_street_requires_each_actionable_player_to_act():
    game = GameState(players=make_players(["A", "B", "C"]), seed=11)
    game.start_hand()

    # Preflop: A calls, B calls small blind completion, C checks big blind.
    game.apply_action("call")
    game.apply_action("call")
    game.apply_action("check")

    assert game.street == Street.FLOP
    assert len(game.community_cards) == 3
    assert game.result is None

    # One player checking on the flop must not auto-run turn/river/showdown.
    game.apply_action("check")

    assert game.street == Street.FLOP
    assert len(game.community_cards) == 3
    assert game.result is None


def test_qwen_beats_human_with_tens_and_eights_over_tens_and_sevens():
    board = ["Tc", "8c", "7h", "6d", "Td"]
    contenders = {
        "human": ["6h", "7d"],
        "qwen": ["8h", "Kc"],
    }

    winners, _score, hand_name = best_players(contenders, board)

    assert winners == ["qwen"]
    assert hand_name == "Two Pair"
    assert describe_best_hand(contenders["human"], board) == "Two Pair, tens and sevens, eight kicker"
    assert describe_best_hand(contenders["qwen"], board) == "Two Pair, tens and eights, king kicker"


def test_showdown_awards_side_pots_by_contribution_level():
    players = [
        PlayerState(id="short", name="Short", stack=0, hole_cards=["Jh", "Td"], all_in=True, contributed=100),
        PlayerState(id="deep_a", name="Deep A", stack=0, hole_cards=["Ac", "Ad"], all_in=True, contributed=300),
        PlayerState(id="deep_b", name="Deep B", stack=0, hole_cards=["Kc", "Kh"], all_in=True, contributed=300),
    ]
    game = GameState(players=players)
    game.community_cards = ["As", "Kd", "Qh", "2c", "3d"]
    game.starting_stacks = {player.id: 0 for player in players}

    game.finish_showdown()

    assert game.result is not None
    assert game.result.pot == 700
    assert game.player("short").stack == 300
    assert game.player("deep_a").stack == 400
    assert game.player("deep_b").stack == 0
    assert game.result.winners == ["short", "deep_a"]
    assert game.result.pot_awards == [
        {"amount": 300, "winners": ["short"], "hand_name": "Straight"},
        {"amount": 400, "winners": ["deep_a"], "hand_name": "Three of a Kind"},
    ]
