from __future__ import annotations

from html import escape

from token_holdem.cards import cards_html, cards_label
from token_holdem.engine import GameState
from token_holdem.leaderboard import LeaderboardRow


def table_html(game: GameState | None, reveal_all: bool = False) -> str:
    if game is None:
        return '<div class="empty-table">Pull up a chair. The table is waiting.</div>'
    seats = []
    current_id = game.current_player().id if not game.result else ""
    for player in game.players:
        hidden = not reveal_all and not player.is_human and not game.result
        active = " active-seat" if player.id == current_id else ""
        folded = " folded-seat" if player.folded else ""
        idx = game.players.index(player)
        badges = []
        if idx == game.dealer_index:
            badges.append("BTN")
        if idx == game.small_blind_index:
            badges.append("SB")
        if idx == game.big_blind_index:
            badges.append("BB")
        badge_html = "".join(f'<span class="seat-badge">{badge}</span>' for badge in badges)
        cards = cards_html(player.hole_cards, hidden=hidden)
        seats.append(
            f"""
            <div class="seat{active}{folded}">
              <div class="avatar">{escape(player.name[:2]).upper()}</div>
              <div class="seat-name">{escape(player.name)} {badge_html}</div>
              <div class="seat-stack">{player.stack} chips</div>
              <div class="seat-cards">{cards}</div>
            </div>
            """
        )
    return f"""
    <div class="token-table">
      <div class="board">
        <div class="pot">Pot: {game.pot()}</div>
        <div class="street">{escape(game.street.value.title())} · Hand {escape(game.hand_id or '-')} · Orbit {escape(game.orbit_id or '-')}</div>
        <div class="community">{cards_html(game.community_cards)}</div>
      </div>
      <div class="seats">{''.join(seats)}</div>
    </div>
    """


def log_markdown(game: GameState | None, chats: list[str] | None = None) -> str:
    if game is None:
        return "No hand yet."
    lines = [f"**Board:** `{cards_label(game.community_cards)}`", ""]
    lines.extend(f"- {line}" for line in game.action_log[-18:])
    if chats:
        lines.append("")
        lines.append("**Table Talk**")
        lines.extend(f"- {chat}" for chat in chats[-10:])
    return "\n".join(lines)


def leaderboard_markdown(rows: list[LeaderboardRow]) -> str:
    if not rows:
        return "No hands recorded yet."
    header = "| Rank | Player | Title | Bankroll | W-L-P | Hands | Biggest Pot | Net | Avg/Hand |\n|---:|---|---|---:|---:|---:|---:|---:|---:|"
    body = []
    for idx, row in enumerate(rows, 1):
        body.append(
            f"| {idx} | {row.name} | {row.title} | {row.bankroll} | {row.wins}-{row.losses}-{row.pushes} | {row.hands_played} | {row.biggest_pot_won} | {row.net_profit} | {row.average_profit:.1f} |"
        )
    return "\n".join([header, *body])


def hall_markdown(records) -> str:
    if not records:
        return "No legends carved into the tavern wall yet."
    return "\n".join(f"- **{record['key'].replace('_', ' ').title()}**: {record['label']}" for record in records)


CSS = """
:root { color-scheme: dark; }
.gradio-container { background: #120b17 !important; color: #f8e8c8 !important; }
.app-title { text-align: center; padding: 20px; border: 3px solid #6f3f1f; background: linear-gradient(180deg, #251526, #160d19); box-shadow: 0 0 24px #000 inset; }
.app-title h1 { font-family: monospace; letter-spacing: 2px; color: #ffd37a; text-shadow: 3px 3px #5a2415; }
.token-table { border: 5px solid #6f3f1f; border-radius: 28px; background: radial-gradient(circle, #28563a 0%, #173321 58%, #120b17 100%); padding: 24px; min-height: 420px; box-shadow: 0 0 40px #000 inset, 0 0 18px #d68b38; }
.board { text-align: center; margin: 10px auto 24px; padding: 18px; border: 2px dashed #d9a35a; border-radius: 18px; max-width: 560px; background: rgba(0,0,0,.25); }
.pot { color: #ffe29a; font-size: 22px; font-weight: 700; }
.street { color: #b7f7c1; font-family: monospace; margin-bottom: 8px; }
.community { min-height: 62px; }
.card { display: inline-flex; align-items: center; justify-content: center; width: 46px; height: 62px; margin: 4px; background: #fff1d4; color: #1b1520; border: 3px solid #3b2a24; border-radius: 6px; font-weight: 800; font-family: monospace; box-shadow: 3px 3px 0 #000; }
.red-card { color: #a72828; }
.hidden-card { background: repeating-linear-gradient(45deg, #33214d, #33214d 5px, #20122f 5px, #20122f 10px); color: #ffd37a; }
.seats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 14px; }
.seat { background: rgba(18, 11, 23, .82); border: 2px solid #6f3f1f; border-radius: 14px; padding: 10px; text-align: center; }
.active-seat { border-color: #ffd37a; box-shadow: 0 0 18px #ffd37a; animation: pulse 1.2s infinite alternate; }
.folded-seat { opacity: .48; filter: grayscale(.6); }
.avatar { width: 52px; height: 52px; margin: 0 auto 8px; border-radius: 8px; background: linear-gradient(135deg, #ffb25f, #7d3cff); color: #160d19; display: flex; align-items: center; justify-content: center; font-family: monospace; font-weight: 900; box-shadow: 3px 3px 0 #000; }
.seat-name { color: #ffd37a; font-weight: 800; }
.seat-badge { display: inline-block; margin-left: 4px; padding: 1px 5px; border: 1px solid #ffd37a; border-radius: 999px; color: #120b17; background: #ffd37a; font-size: 11px; }
.seat-stack { color: #b7f7c1; font-size: 13px; }
.empty-table { min-height: 300px; border: 4px dashed #6f3f1f; display: flex; align-items: center; justify-content: center; color: #ffd37a; font-family: monospace; }
button { font-family: monospace !important; }
@keyframes pulse { from { transform: translateY(0); } to { transform: translateY(-2px); } }
"""
