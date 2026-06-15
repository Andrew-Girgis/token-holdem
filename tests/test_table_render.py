from app import _start_game
from token_holdem.render import DEALER_BUTTON_COORDS, SEAT_COORDS, table_html


def test_table_layout_constants_are_eight_seat_maps():
    assert SEAT_COORDS == {
        0: (50, 82),
        1: (23, 78),
        2: (8, 54),
        3: (18, 24),
        4: (50, 12),
        5: (82, 24),
        6: (92, 54),
        7: (77, 78),
    }
    assert DEALER_BUTTON_COORDS == {
        0: (50, 70),
        1: (30, 69),
        2: (20, 54),
        3: (28, 32),
        4: (50, 24),
        5: (72, 32),
        6: (80, 54),
        7: (70, 69),
    }


def test_play_mode_renders_human_plus_seven_llm_seats():
    session = _start_game("Tester", 100, "play")
    assert session.game is not None

    html = table_html(session.game)

    assert len(session.game.players) == 8
    assert session.game.players[0].is_human is True
    assert html.count('class="seat seat-') == 8
    assert 'class="seat seat-0 human-seat' in html
    for slot in range(1, 8):
        assert f'class="seat seat-{slot} llm-seat' in html
    assert 'class="dealer-button"' in html
    assert 'class="center-hud"' in html
    assert 'class="community card-row"' in html
    assert "Pot " in html
    assert "Current actor" in html


def test_dealer_button_uses_slot_coordinates():
    session = _start_game("Tester", 100, "play")
    assert session.game is not None
    session.game.dealer_index = 0

    html = table_html(session.game)

    assert "--dealer-x: 50%; --dealer-y: 70%;" in html
