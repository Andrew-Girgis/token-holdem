from token_holdem.leaderboard import Leaderboard


def test_leaderboard_records_profit_based_stats(tmp_path):
    db = tmp_path / "leaderboard.sqlite3"
    board = Leaderboard(db)
    board.ensure_player("p1", "Player One", "model", "model/a")
    board.ensure_player("p2", "Player Two", "model", "model/b")

    board.record_hand(
        "arena",
        120,
        "AS KS QS JS TS",
        ["p1"],
        {"p1": 60, "p2": -60},
        {"p1": "Player One", "p2": "Player Two"},
        "Player One wins.",
    )

    rows = board.rows()
    assert rows[0].name == "Player One"
    assert rows[0].wins == 1
    assert rows[0].net_profit == 60
    assert rows[1].losses == 1
    assert board.hall_of_fame()[0]["key"] == "largest_pot"
