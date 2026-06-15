from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from token_holdem.logging_utils import get_logger, log_event


DB_PATH = Path("token_holdem.sqlite3")
logger = get_logger("token_holdem.leaderboard")


@dataclass
class LeaderboardRow:
    name: str
    kind: str
    model_id: str
    title: str
    bankroll: int
    hands_played: int
    wins: int
    losses: int
    pushes: int
    biggest_pot_won: int
    net_profit: int
    average_profit: float


class Leaderboard:
    def __init__(self, path: Path | str = DB_PATH):
        self.path = Path(path)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                create table if not exists players (
                    id text primary key,
                    display_name text not null,
                    kind text not null,
                    model_id text not null default '',
                    persona text not null default '',
                    created_at text not null default current_timestamp
                );
                create table if not exists stats (
                    player_id text primary key references players(id),
                    bankroll integer not null default 1000,
                    hands_played integer not null default 0,
                    wins integer not null default 0,
                    losses integer not null default 0,
                    pushes integer not null default 0,
                    biggest_pot_won integer not null default 0,
                    net_profit integer not null default 0,
                    current_streak integer not null default 0,
                    longest_winning_streak integer not null default 0,
                    largest_comeback integer not null default 0
                );
                create table if not exists hands (
                    id integer primary key autoincrement,
                    mode text not null,
                    pot integer not null,
                    board text not null,
                    winners text not null,
                    summary text not null,
                    created_at text not null default current_timestamp
                );
                create table if not exists hall_of_fame (
                    key text primary key,
                    player_id text not null,
                    value integer not null,
                    label text not null,
                    updated_at text not null default current_timestamp
                );
                """
            )

    def ensure_player(self, player_id: str, name: str, kind: str, model_id: str = "", persona: str = "") -> None:
        with self.connect() as conn:
            conn.execute(
                "insert or ignore into players(id, display_name, kind, model_id, persona) values (?, ?, ?, ?, ?)",
                (player_id, name, kind, model_id, persona),
            )
            conn.execute("insert or ignore into stats(player_id) values (?)", (player_id,))

    def record_hand(
        self,
        mode: str,
        pot: int,
        board: str,
        winners: list[str],
        deltas: dict[str, int],
        names: dict[str, str],
        summary: str,
        session_id: str = "",
        hand_id: str = "",
        orbit_id: str = "",
    ) -> None:
        log_event(logger, "leaderboard_record_hand", mode=mode, session_id=session_id, hand_id=hand_id, orbit_id=orbit_id, pot=pot, board=board, winners=winners, deltas=deltas, summary=summary)
        with self.connect() as conn:
            conn.execute(
                "insert into hands(mode, pot, board, winners, summary) values (?, ?, ?, ?, ?)",
                (mode, pot, board, ",".join(winners), summary),
            )
            for player_id, delta in deltas.items():
                conn.execute(
                    "insert or ignore into players(id, display_name, kind) values (?, ?, ?)",
                    (player_id, names[player_id], "human" if player_id == "human" else "model"),
                )
                conn.execute("insert or ignore into stats(player_id) values (?)", (player_id,))
                won_pot = pot if player_id in winners else 0
                win = 1 if delta > 0 else 0
                loss = 1 if delta < 0 else 0
                push = 1 if delta == 0 else 0
                conn.execute(
                    """
                    update stats
                    set bankroll = bankroll + ?,
                        hands_played = hands_played + 1,
                        wins = wins + ?,
                        losses = losses + ?,
                        pushes = pushes + ?,
                        biggest_pot_won = max(biggest_pot_won, ?),
                        net_profit = net_profit + ?,
                        current_streak = case when ? > 0 then current_streak + 1 else 0 end,
                        longest_winning_streak = max(longest_winning_streak, case when ? > 0 then current_streak + 1 else longest_winning_streak end),
                        largest_comeback = min(largest_comeback, ?)
                    where player_id = ?
                    """,
                    (delta, win, loss, push, won_pot, delta, delta, delta, delta, player_id),
                )
            self._update_hall(conn, "largest_pot", winners[0], pot, f"Largest pot: {pot} won by {names[winners[0]]}")

    def _update_hall(self, conn: sqlite3.Connection, key: str, player_id: str, value: int, label: str) -> None:
        existing = conn.execute("select value from hall_of_fame where key = ?", (key,)).fetchone()
        if existing is None or value > existing["value"]:
            conn.execute(
                "insert or replace into hall_of_fame(key, player_id, value, label, updated_at) values (?, ?, ?, ?, current_timestamp)",
                (key, player_id, value, label),
            )

    def rows(self) -> list[LeaderboardRow]:
        with self.connect() as conn:
            records = conn.execute(
                """
                select p.display_name, p.kind, p.model_id, s.*
                from stats s join players p on p.id = s.player_id
                order by s.net_profit desc, s.bankroll desc, s.wins desc
                """
            ).fetchall()
        return [
            LeaderboardRow(
                name=row["display_name"],
                kind=row["kind"],
                model_id=row["model_id"],
                title=title_for(row),
                bankroll=row["bankroll"],
                hands_played=row["hands_played"],
                wins=row["wins"],
                losses=row["losses"],
                pushes=row["pushes"],
                biggest_pot_won=row["biggest_pot_won"],
                net_profit=row["net_profit"],
                average_profit=(row["net_profit"] / row["hands_played"]) if row["hands_played"] else 0.0,
            )
            for row in records
        ]

    def hall_of_fame(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute("select * from hall_of_fame order by value desc"))


def title_for(row: sqlite3.Row) -> str:
    if row["biggest_pot_won"] >= 600:
        return "Chip Destroyer"
    if row["wins"] >= 3 and row["losses"] == 0:
        return "Silent Assassin"
    if row["losses"] > row["wins"] * 2 and row["hands_played"] >= 3:
        return "Chaos Goblin"
    if row["net_profit"] > 0:
        return "River Regular"
    return "Tavern Newcomer"
