from __future__ import annotations

from html import escape

from token_holdem.cards import RED_SUITS, SUIT_SYMBOLS, cards_label
from token_holdem.engine import GameState, PlayerState
from token_holdem.leaderboard import LeaderboardRow


SEAT_COORDS: dict[int, tuple[int, int]] = {
    0: (50, 88),
    1: (23, 78),
    2: (8, 54),
    3: (18, 24),
    4: (50, 12),
    5: (82, 24),
    6: (92, 54),
    7: (77, 78),
}

DEALER_BUTTON_COORDS: dict[int, tuple[int, int]] = {
    0: (50, 74),
    1: (30, 69),
    2: (20, 54),
    3: (28, 32),
    4: (50, 24),
    5: (72, 32),
    6: (80, 54),
    7: (70, 69),
}

SEAT_COUNT = 8
BOARD_CARD_SLOTS = 5


def table_html(game: GameState | None, reveal_all: bool = False) -> str:
    if game is None:
        return """
        <div class="token-table-shell">
          <div class="token-table token-table-empty">
            <div class="table-felt" aria-hidden="true"></div>
            <div class="center-hud">
              <div class="hud-kicker">Waiting for players</div>
              <div class="pot">Pot 0</div>
              <div class="street">Quick Seat to begin</div>
              <div class="community card-row" aria-label="Community cards">
                <span class="card card-slot"></span><span class="card card-slot"></span><span class="card card-slot"></span><span class="card card-slot"></span><span class="card card-slot"></span>
              </div>
            </div>
          </div>
        </div>
        """

    current_id = game.current_player().id if not game.result else ""
    current_actor = "Complete" if game.result else game.current_player().name
    button_slot = _slot_for_player_index(game, game.dealer_index)
    dealer_x, dealer_y = DEALER_BUTTON_COORDS[button_slot]
    seats = []
    for slot, player in enumerate(_seat_slots(game)):
        x, y = SEAT_COORDS[slot]
        slot_class = " human-seat" if slot == 0 else " llm-seat"
        if player is None:
            seats.append(_empty_seat_html(slot, x, y, slot_class))
            continue
        hidden = not reveal_all and not player.is_human and not game.result
        active = " active-seat" if player.id == current_id else ""
        folded = " folded-seat" if player.folded else ""
        all_in = " all-in-seat" if player.all_in else ""
        idx = game.players.index(player)
        badges = []
        if idx == game.dealer_index:
            badges.append("BTN")
        if idx == game.small_blind_index:
            badges.append("SB")
        if idx == game.big_blind_index:
            badges.append("BB")
        if player.all_in:
            badges.append("ALL-IN")
        badge_html = "".join(f'<span class="seat-badge">{badge}</span>' for badge in badges)
        cards = _hole_cards_html(player, hidden=hidden)
        status = _player_status(player, active=player.id == current_id, result_winner=bool(game.result and player.id in game.result.winners))
        bet = f'<span class="seat-bet">Bet {player.bet}</span>' if player.bet else '<span class="seat-bet muted">No bet</span>'
        seats.append(
            f"""
            <section class="seat seat-{slot}{slot_class}{active}{folded}{all_in}" style="--seat-x: {x}%; --seat-y: {y}%;" aria-label="Seat {slot}: {escape(player.name)}">
              <div class="avatar-slot" aria-hidden="true"><span>{escape(player.name[:2]).upper()}</span></div>
              <div class="seat-copy">
                <div class="seat-label"><span class="seat-index">Seat {slot}</span>{badge_html}</div>
                <div class="seat-name">{escape(player.name)}</div>
                <div class="seat-stack">{player.stack} chips</div>
              </div>
              <div class="seat-meta">{bet}<span class="seat-status">{status}</span></div>
              <div class="seat-cards">{cards}</div>
            </section>
            """
        )
    winner = f'<div class="result-banner">{escape(game.result.summary)}</div>' if game.result else ""
    return f"""
    <div class="token-table-shell">
      <div class="table-status-bar">
        <span>Hand {escape(game.hand_id or "-")}</span>
        <span>Orbit {escape(game.orbit_id or "-")}</span>
        <span>Blinds {game.small_blind}/{game.big_blind}</span>
      </div>
      <div class="token-table" role="img" aria-label="Token Hold'em 8-seat table">
        <div class="table-felt" aria-hidden="true"></div>
        <div class="dealer-button" style="--dealer-x: {dealer_x}%; --dealer-y: {dealer_y}%;" aria-label="Dealer button at seat {button_slot}">D</div>
        <section class="center-hud" aria-label="Current hand state">
          <div class="hud-kicker">Current actor</div>
          <div class="current-actor">{escape(current_actor)}</div>
          <div class="pot">Pot {game.pot()}</div>
          <div class="street">{escape(game.street.value.title())} · Bet {game.current_bet}</div>
          <div class="community card-row" aria-label="Community cards">{_community_cards_html(game.community_cards)}</div>
          {winner}
        </section>
        <div class="seat-ring">{''.join(seats)}</div>
      </div>
    </div>
    """


def _slot_for_player_index(game: GameState, player_index: int) -> int:
    if not game.players:
        return 0
    player = game.players[player_index]
    if player.is_human:
        return 0
    human_present = any(candidate.is_human for candidate in game.players)
    ai_players = [candidate for candidate in game.players if not candidate.is_human]
    ai_slot = ai_players.index(player) + 1
    return min(ai_slot, SEAT_COUNT - 1) if human_present else min(player_index + 1, SEAT_COUNT - 1)


def _seat_slots(game: GameState) -> list[PlayerState | None]:
    slots: list[PlayerState | None] = [None] * SEAT_COUNT
    human = next((player for player in game.players if player.is_human), None)
    ai_players = [player for player in game.players if not player.is_human]
    slots[0] = human
    for slot, player in enumerate(ai_players[: SEAT_COUNT - 1], start=1):
        slots[slot] = player
    return slots


def _empty_seat_html(slot: int, x: int, y: int, slot_class: str) -> str:
    label = "Human seat" if slot == 0 else "LLM seat"
    return f"""
    <section class="seat seat-{slot}{slot_class} empty-seat" style="--seat-x: {x}%; --seat-y: {y}%;" aria-label="Seat {slot}: {label} open">
      <div class="avatar-slot" aria-hidden="true"><span>{slot}</span></div>
      <div class="seat-copy">
        <div class="seat-label"><span class="seat-index">Seat {slot}</span></div>
        <div class="seat-name">{label}</div>
        <div class="seat-stack">Waiting</div>
      </div>
      <div class="seat-meta"><span class="seat-bet muted">No bet</span><span class="seat-status">Open</span></div>
      <div class="seat-cards">{_empty_hole_cards_html()}</div>
    </section>
    """


def _player_status(player: PlayerState, *, active: bool, result_winner: bool) -> str:
    if result_winner:
        return "Winner"
    if player.folded:
        return "Folded"
    if player.all_in:
        return "All-in"
    if active:
        return "Acting"
    return "Ready"


def _hole_cards_html(player: PlayerState, *, hidden: bool) -> str:
    if not player.hole_cards:
        return _empty_hole_cards_html()
    return "".join(_card_html(card, hidden=hidden, small=not player.is_human) for card in player.hole_cards[:2])


def _empty_hole_cards_html() -> str:
    return '<span class="mini-card card-slot"></span><span class="mini-card card-slot"></span>'


def _community_cards_html(cards: list[str]) -> str:
    visible_cards = [_card_html(card) for card in cards[:BOARD_CARD_SLOTS]]
    empty_cards = ['<span class="card card-slot"></span>' for _ in range(BOARD_CARD_SLOTS - len(visible_cards))]
    return "".join([*visible_cards, *empty_cards])


def _card_html(card: str, *, hidden: bool = False, small: bool = False) -> str:
    class_name = "mini-card" if small else "card"
    if hidden:
        return f'<span class="{class_name} hidden-card" aria-label="Hidden card">??</span>'
    suit = card[1]
    color = " red-card" if suit in RED_SUITS else ""
    return f'<span class="{class_name}{color}">{escape(card[0] + SUIT_SYMBOLS[suit])}</span>'


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
.gradio-container { background: #100d12 !important; color: #f8e8c8 !important; }
.app-title { text-align: center; padding: 18px; border: 2px solid #7a4b2a; background: linear-gradient(180deg, #2a1820, #171016); box-shadow: 0 0 24px #000 inset; }
.app-title h1 { font-family: monospace; letter-spacing: 0; color: #ffd37a; text-shadow: 2px 2px #5a2415; }
.token-table-shell { width: min(100%, 1120px); margin: 10px auto 18px; }
.table-status-bar { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin: 0 auto 8px; color: #f3d7a2; font: 700 12px monospace; }
.table-status-bar span { min-height: 28px; display: inline-flex; align-items: center; padding: 3px 9px; border: 1px solid #7a4b2a; border-radius: 6px; background: #21161a; }
.token-table { position: relative; overflow: hidden; aspect-ratio: 16 / 10; min-height: 560px; border: 6px solid #74451f; border-radius: 26px; background: #1c1116; box-shadow: 0 0 38px #000 inset, 0 10px 24px rgba(0,0,0,.45); }
.table-felt { position: absolute; inset: 5%; border: 18px solid #5b331c; border-radius: 50%; background: radial-gradient(ellipse at center, #2f724f 0%, #22593d 48%, #15351f 76%); box-shadow: 0 0 34px rgba(0,0,0,.7) inset, 0 0 0 4px #c38b45 inset; }
.token-table-empty { display: grid; place-items: center; }
.center-hud { position: absolute; left: 50%; top: 48%; transform: translate(-50%, -50%); z-index: 4; width: min(44%, 480px); min-width: 360px; padding: 12px 14px 14px; text-align: center; border: 2px solid #c4934e; border-radius: 8px; background: rgba(20, 16, 18, .84); box-shadow: 0 10px 20px rgba(0,0,0,.42); }
.hud-kicker { color: #d1b37c; font: 700 11px monospace; text-transform: uppercase; }
.current-actor { margin-top: 2px; color: #fff1c4; font: 900 18px monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pot { color: #ffe29a; font: 900 22px monospace; }
.street { color: #b7f7c1; font: 700 13px monospace; margin-bottom: 8px; }
.result-banner { margin-top: 8px; padding: 6px 8px; border-radius: 6px; color: #120b17; background: #ffd37a; font: 800 12px monospace; }
.card-row { display: flex; justify-content: center; align-items: center; gap: clamp(4px, .8vw, 9px); min-height: clamp(54px, 8vw, 74px); }
.card, .mini-card { display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto; background: #fff1d4; color: #1b1520; border: 2px solid #3b2a24; border-radius: 6px; font-weight: 900; font-family: monospace; box-shadow: 3px 3px 0 #000; }
.card { width: clamp(36px, 5vw, 50px); height: clamp(50px, 7vw, 68px); font-size: clamp(14px, 2vw, 18px); }
.mini-card { width: 28px; height: 38px; font-size: 12px; }
.red-card { color: #a72828; }
.hidden-card { background: repeating-linear-gradient(45deg, #33214d, #33214d 5px, #20122f 5px, #20122f 10px); color: #ffd37a; }
.card-slot { background: rgba(255,241,212,.13); border-style: dashed; box-shadow: none; color: transparent; }
.seat-ring { position: absolute; inset: 0; z-index: 5; }
.seat { position: absolute; left: var(--seat-x); top: var(--seat-y); transform: translate(-50%, -50%); width: clamp(138px, 16vw, 184px); min-height: 126px; display: grid; grid-template-columns: 42px minmax(0, 1fr); grid-template-rows: auto auto; gap: 6px 8px; padding: 8px; text-align: left; border: 2px solid #7a4b2a; border-radius: 8px; background: rgba(20, 13, 18, .9); box-shadow: 0 8px 18px rgba(0,0,0,.42); transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease, opacity 180ms ease; }
.human-seat { width: clamp(190px, 24vw, 270px); min-height: 142px; }
.avatar-slot { grid-row: 1 / 3; width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; border-radius: 7px; border: 2px solid #c4934e; background: linear-gradient(135deg, #dca861, #5f6b7a); box-shadow: 2px 2px 0 #000; color: #171016; font: 900 13px monospace; }
.seat-copy, .seat-meta { min-width: 0; }
.seat-label { min-height: 18px; display: flex; flex-wrap: wrap; align-items: center; gap: 3px; }
.seat-index { color: #d1b37c; font: 700 10px monospace; text-transform: uppercase; }
.seat-name { color: #ffd37a; font: 900 13px monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.seat-stack { color: #b7f7c1; font: 800 12px monospace; white-space: nowrap; }
.seat-meta { grid-column: 2; display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.seat-bet, .seat-status, .seat-badge { display: inline-flex; align-items: center; min-height: 18px; padding: 1px 5px; border-radius: 5px; font: 800 10px monospace; }
.seat-bet { color: #f5dec0; background: #37231b; }
.seat-status { color: #121014; background: #b7f7c1; }
.seat-badge { color: #120b17; background: #ffd37a; border: 1px solid #ffd37a; }
.seat-cards { grid-column: 1 / 3; display: flex; justify-content: center; gap: 5px; min-height: 40px; }
.active-seat { border-color: #ffd37a; box-shadow: 0 0 0 3px rgba(255,211,122,.24), 0 0 22px rgba(255,211,122,.55); }
.active-seat .seat-status { background: #ffd37a; }
.folded-seat { opacity: .56; filter: grayscale(.55); }
.all-in-seat { border-color: #b7f7c1; }
.empty-seat { opacity: .62; }
.muted { opacity: .74; }
.dealer-button { position: absolute; left: var(--dealer-x); top: var(--dealer-y); transform: translate(-50%, -50%); z-index: 6; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; border-radius: 50%; border: 3px solid #4b2a18; color: #1b1520; background: #ffe29a; font: 900 16px monospace; box-shadow: 2px 3px 0 #000; transition: left 220ms ease, top 220ms ease; }
button { min-height: 44px; font-family: monospace !important; }
button:hover:not(:disabled) { filter: brightness(1.08); }
button:focus-visible { outline: 3px solid #ffd37a !important; outline-offset: 2px !important; }
@media (prefers-reduced-motion: reduce) {
  .seat, .dealer-button { transition: none; }
}
@media (max-width: 900px) {
  .token-table { min-height: 640px; aspect-ratio: auto; }
  .table-felt { inset: 3% 4% 21%; border-width: 12px; }
  .center-hud { top: 38%; width: min(78%, 460px); min-width: 280px; }
  .seat { width: 132px; min-height: 112px; padding: 6px; grid-template-columns: 34px minmax(0, 1fr); }
  .human-seat { width: min(78%, 320px); top: 82% !important; }
  .avatar-slot { width: 34px; height: 34px; }
  .mini-card { width: 24px; height: 34px; }
}
@media (max-width: 680px) {
  .token-table-shell { margin-top: 6px; }
  .table-status-bar { justify-content: flex-start; overflow-x: auto; padding-bottom: 3px; }
  .token-table { min-height: 780px; border-width: 4px; }
  .table-felt { inset: 6% 3% 32%; border-width: 10px; }
  .center-hud { top: 28%; width: calc(100% - 28px); min-width: 0; padding: 10px; }
  .seat-ring { position: absolute; left: 10px; right: 10px; top: 43%; bottom: 138px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; overflow: auto; align-content: start; }
  .seat { position: relative; left: auto; top: auto; transform: none; width: auto; min-height: 104px; }
  .human-seat { position: absolute; left: 50%; right: auto; top: auto !important; bottom: 10px; transform: translateX(-50%); width: calc(100% - 28px); min-height: 118px; }
  .seat-0 { order: 8; }
  .dealer-button { width: 30px; height: 30px; left: 50% !important; top: 39% !important; }
  .current-actor { font-size: 15px; }
  .pot { font-size: 18px; }
  .seat-name { font-size: 12px; }
}
"""
