from app import _start_game, _start_next_cash_hand, action_handler, start_play_with_runtime


def test_cash_hand_preserves_stacks_and_rotates_button():
    session = _start_game("Tester", 100, "play")
    assert session.game is not None
    assert session.game.hand_id.endswith("-h001")
    assert session.game.orbit_id.endswith("-o01")
    original_button = session.game.dealer_index
    session.game.players[0].stack = 400

    session = _start_next_cash_hand(session, 100, "Tester")

    assert session.game is not None
    assert session.game.session_id == session.session_id
    assert session.game.hand_id.endswith("-h002")
    assert session.game.orbit_id.endswith("-o01")
    assert session.game.players[0].stack <= 400
    assert session.game.dealer_index != original_button


def test_busted_human_requires_rebuy_before_next_cash_hand():
    session = _start_game("Tester", 100, "play")
    assert session.game is not None
    session.game.players[0].stack = 0

    session = _start_next_cash_hand(session, 100, "Tester")

    assert session.stopped is True
    assert "needs a rebuy" in session.chats[-1]


def test_action_handler_yields_full_gradio_outputs():
    session = list(start_play_with_runtime("Tester", 100))[-1][0]
    outputs = list(action_handler("call")(session))

    assert outputs
    assert all(len(output) == 15 for output in outputs)
    assert "Qwen/Qwen3" not in outputs[-1][2]
    assert "[local_model]" not in outputs[-1][2]
