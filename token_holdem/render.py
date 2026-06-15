from __future__ import annotations

from html import escape

from token_holdem.cards import RED_SUITS, SUIT_SYMBOLS, cards_label
from token_holdem.engine import GameState, PlayerState
from token_holdem.leaderboard import LeaderboardRow


SEAT_COORDS: dict[int, tuple[int, int]] = {
    0: (50, 82),
    1: (23, 78),
    2: (8, 54),
    3: (18, 24),
    4: (50, 12),
    5: (82, 24),
    6: (92, 54),
    7: (77, 78),
}

DEALER_BUTTON_COORDS: dict[int, tuple[int, int]] = {
    0: (50, 70),
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

AVATAR_PERSONAS: dict[str, dict[str, str]] = {
    "Nemotron Nano": {
        "display": "Nemotron",
        "role": "Tinkerer automaton",
        "initials": "NE",
        "accent": "#d9a35f",
        "talk": "Counting tells by candlelight.",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-nemotron-automaton-halfbody-768.png",
    },
    "Qwen": {
        "display": "Qwen",
        "role": "Scholar oracle",
        "initials": "QW",
        "accent": "#74b8b2",
        "talk": "Pot odds first, pride second.",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-qwen-oracle-halfbody-768.png",
    },
    "Gemma": {
        "display": "Gemma",
        "role": "Hearth strategist",
        "initials": "GE",
        "accent": "#b7cf7a",
        "talk": "Small folds keep stacks warm.",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-gemma-hearth-halfbody-768.png",
    },
    "Cohere North Mini": {
        "display": "North",
        "role": "Cartographer monk",
        "initials": "NO",
        "accent": "#c982bc",
        "talk": "A side quest enters the pot.",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-north-cartographer-halfbody-768.png",
    },
    "Mistral": {
        "display": "Mistral",
        "role": "Storm duelist",
        "initials": "MI",
        "accent": "#8dc5ff",
        "talk": "Fast wind, faster raise.",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-mistral-duelist-halfbody-768.png",
    },
    "OpenAI Open Model 20B": {
        "display": "Open Model",
        "role": "Dealer savant",
        "initials": "OM",
        "accent": "#f2c45d",
        "talk": "Expected value takes the stage.",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-open-model-savant-halfbody-768.png",
    },
    "Llama Scout": {
        "display": "Llama Scout",
        "role": "Pattern scout",
        "initials": "LS",
        "accent": "#d49464",
        "talk": "The felt remembers every bet.",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-llama-scout-halfbody-768.png",
    },
    "Professor Odds": {
        "display": "Professor Odds",
        "role": "Probability professor",
        "initials": "PO",
        "accent": "#d9a35f",
        "talk": "The math is in my favor.",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-professor-odds-neutral-512.png",
    },
    "Maverick": {
        "display": "Maverick",
        "role": "Frontier gambler",
        "initials": "MV",
        "accent": "#d49464",
        "talk": "Smells like weakness.",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-maverick-frontier-neutral-512.png",
    },
    "Sheriff": {
        "display": "Sheriff",
        "role": "Lawkeeper",
        "initials": "SH",
        "accent": "#c4934e",
        "talk": "Keep the table honest.",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-sheriff-lawkeeper-neutral-512.png",
    },
    "Gobbo": {
        "display": "Gobbo",
        "role": "Chip trickster",
        "initials": "GB",
        "accent": "#82bf63",
        "talk": "Shiny chips... mine?",
        "avatar": "/gradio_api/file=assets/token-holdem/avatar-gobbo-trickster-neutral-512.png",
    },
}

HUMAN_PERSONA = {
    "display": "You",
    "role": "Tavern challenger",
    "initials": "YU",
    "accent": "#ffd37a",
    "talk": "Your cards, your candle.",
    "avatar": "/gradio_api/file=assets/token-holdem/avatar-human-wanderer-halfbody-768.png",
}


def table_html(game: GameState | None, reveal_all: bool = False, chats: list[str] | None = None) -> str:
    if game is None:
        return """
        <div class="token-table-shell tavern-scene">
          <div class="token-table token-table-empty">
            <div class="tavern-backdrop tavern-background" aria-hidden="true">
              <span class="wall-stone wall-stone-a"></span>
              <span class="wall-stone wall-stone-b"></span>
              <span class="bar-shelf"></span>
              <span class="bartender-shadow"></span>
              <span class="candle candle-left"></span>
              <span class="candle candle-right"></span>
            </div>
            <div class="tavern-ambient-lights" aria-hidden="true"><span></span><span></span><span></span></div>
            <div class="table-felt poker-table-surface" aria-hidden="true"></div>
            <div class="table-chip-pile table-chip-pile-empty" aria-hidden="true"><span></span><span></span><span></span></div>
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
    talk_by_name = _table_talk_by_name(chats)
    seats = []
    human_seat = ""
    speech_bubbles = []
    for slot, player in enumerate(_seat_slots(game)):
        x, y = SEAT_COORDS[slot]
        slot_class = " human-seat" if slot == 0 else " llm-seat"
        if player is None:
            seat_html = _empty_seat_html(slot, x, y, slot_class)
            if slot == 0:
                human_seat = seat_html
            else:
                seats.append(seat_html)
            continue
        hidden = not reveal_all and not player.is_human and not game.result
        result_winner = bool(game.result and player.id in game.result.winners)
        active = " active-seat" if player.id == current_id else ""
        winner_class = " winner-seat" if result_winner else ""
        folded = " folded-seat" if player.folded else ""
        all_in = " all-in-seat" if player.all_in else ""
        cards = _hole_cards_html(player, hidden=hidden)
        status = _player_status(player, active=player.id == current_id, result_winner=result_winner)
        bet = f'<span class="seat-bet">Bet {player.bet}</span>' if player.bet else '<span class="seat-bet muted">Bet 0</span>'
        persona = _persona_for(player)
        talk = talk_by_name.get(player.name, persona["talk"])
        avatar_html = _avatar_img_html(persona)
        if talk and player.name in talk_by_name:
            speech_bubbles.append(
                f'<div class="speech-bubble seat-{slot}-bubble" style="--bubble-x: {x}%; --bubble-y: {max(8, y - 12)}%; --avatar-accent: {persona["accent"]};"><strong>{escape(player.name)}</strong><span>{escape(talk)}</span></div>'
            )
        talk_html = f'<div class="seat-talk">{escape(talk)}</div>' if talk else ""
        seat_html = f"""
            <section class="seat seat-{slot}{slot_class}{active}{winner_class}{folded}{all_in}" style="--seat-x: {x}%; --seat-y: {y}%; --avatar-accent: {persona['accent']};" aria-label="Seat {slot}: {escape(player.name)}">
              <div class="avatar-layer" title="{escape(persona['display'])}" aria-hidden="true">
                <div class="avatar-slot">{avatar_html}<span>{escape(persona['initials'])}</span></div>
              </div>
              <div class="seat-plaque">
                <div class="seat-copy">
                  <div class="seat-name">{escape(player.name)}</div>
                </div>
                <div class="seat-meta"><span class="seat-stack">Stack {player.stack}</span>{bet}<span class="seat-status">{status}</span></div>
              </div>
              <div class="speech-bubble-layer">{talk_html}</div>
              <div class="seat-cards">{cards}</div>
            </section>
            """
        if slot == 0:
            human_seat = seat_html
        else:
            seats.append(seat_html)
    winner = f'<div class="result-banner">{escape(game.result.summary)}</div>' if game.result else ""
    return f"""
    <div class="token-table-shell tavern-scene">
      <div class="table-status-bar">
        <span>Hand {escape(game.hand_id or "-")}</span>
        <span>Orbit {escape(game.orbit_id or "-")}</span>
        <span>Blinds {game.small_blind}/{game.big_blind}</span>
      </div>
      <div class="token-table" role="img" aria-label="Token Hold'em 8-seat table">
        <div class="tavern-backdrop tavern-background" aria-hidden="true">
          <span class="wall-stone wall-stone-a"></span>
          <span class="wall-stone wall-stone-b"></span>
          <span class="bar-shelf"></span>
          <span class="bartender-shadow"></span>
          <span class="candle candle-left"></span>
          <span class="candle candle-right"></span>
          <span class="floor-planks"></span>
        </div>
        <div class="tavern-ambient-lights" aria-hidden="true"><span></span><span></span><span></span></div>
        <div class="table-felt poker-table-surface" aria-hidden="true"></div>
        <div class="table-chip-pile" aria-hidden="true"><span></span><span></span><span></span><b>{game.pot()}</b></div>
        <div class="dealer-button" style="--dealer-x: {dealer_x}%; --dealer-y: {dealer_y}%;" aria-label="Dealer button at seat {button_slot}">D</div>
        <section class="center-hud" aria-label="Current hand state">
          <div class="hud-kicker">Current actor</div>
          <div class="current-actor">{escape(current_actor)}</div>
          <div class="pot">Pot {game.pot()}</div>
          <div class="street">{escape(game.street.value.title())} · Bet {game.current_bet}</div>
          <div class="community card-row" aria-label="Community cards">{_community_cards_html(game.community_cards)}</div>
          {winner}
        </section>
        <div class="seat-layer">
          {human_seat}
          <div class="seat-ring">{''.join(seats)}</div>
        </div>
        <div class="speech-bubble-layer table-speech-layer">{''.join(speech_bubbles[-3:])}</div>
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


def _persona_for(player: PlayerState) -> dict[str, str]:
    if player.is_human:
        persona = HUMAN_PERSONA.copy()
        initials = "".join(part[0] for part in player.name.split()[:2]).upper() or "YU"
        persona["initials"] = initials[:2]
        return persona
    return AVATAR_PERSONAS.get(
        player.name,
        {
            "display": "Tavern Regular",
            "role": "Unknown model",
            "initials": player.name[:2].upper(),
            "accent": "#d9a35f",
            "talk": "Waiting for a readable tell.",
            "avatar": "/gradio_api/file=assets/token-holdem/avatar-sheriff-lawkeeper-neutral-512.png",
        },
    )


def _avatar_img_html(persona: dict[str, str]) -> str:
    avatar = persona.get("avatar", "")
    if not avatar:
        return ""
    return f'<img src="{escape(avatar)}" alt="" loading="lazy">'


def _table_talk_by_name(chats: list[str] | None) -> dict[str, str]:
    if not chats:
        return {}
    talks: dict[str, str] = {}
    for chat in chats[-16:]:
        if ": " not in chat:
            continue
        name, line = chat.split(": ", 1)
        talks[name] = line[:96]
    return talks


def _last_action_by_name(game: GameState) -> dict[str, str]:
    actions: dict[str, str] = {}
    names = sorted((player.name for player in game.players), key=len, reverse=True)
    for line in game.action_log:
        for name in names:
            if line.startswith(f"{name} "):
                actions[name] = line[len(name) + 1 :][:42]
                break
    return actions


def _player_status(player: PlayerState, *, active: bool, result_winner: bool) -> str:
    if result_winner:
        return "Winner"
    if player.folded:
        return "Folded"
    if active:
        return "Acting"
    if player.all_in or player.bet:
        return "Ready"
    return "Watching"


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
        return '<div class="tavern-log empty-log">No hand yet. The table is waiting by the hearth.</div>'
    lines = ['<div class="tavern-log">', f'<div class="log-board">Board: <code>{escape(cards_label(game.community_cards))}</code></div>', '<ul>']
    lines.extend(f"<li>{escape(line)}</li>" for line in game.action_log[-18:])
    lines.append("</ul>")
    if chats:
        lines.append('<div class="log-talk-title">Table Talk</div><ul class="log-talk">')
        lines.extend(f"<li>{escape(chat)}</li>" for chat in chats[-10:])
        lines.append("</ul>")
    lines.append("</div>")
    return "\n".join(lines)


def leaderboard_markdown(rows: list[LeaderboardRow]) -> str:
    if not rows:
        return '<div class="tavern-ledger empty-ledger">No hands recorded yet. The ledger is clean parchment.</div>'
    body = ['<div class="tavern-ledger"><table><thead><tr><th>Rank</th><th>Player</th><th>Title</th><th>Bankroll</th><th>W-L-P</th><th>Hands</th><th>Biggest Pot</th><th>Net</th><th>Avg/Hand</th></tr></thead><tbody>']
    for idx, row in enumerate(rows, 1):
        body.append(
            "<tr>"
            f"<td>{idx}</td><td>{escape(row.name)}</td><td>{escape(row.title)}</td><td>{row.bankroll}</td>"
            f"<td>{row.wins}-{row.losses}-{row.pushes}</td><td>{row.hands_played}</td><td>{row.biggest_pot_won}</td>"
            f"<td>{row.net_profit}</td><td>{row.average_profit:.1f}</td>"
            "</tr>"
        )
    body.append("</tbody></table></div>")
    return "\n".join(body)


def hall_markdown(records) -> str:
    if not records:
        return '<div class="hall-wall empty-hall">No legends carved into the tavern wall yet.</div>'
    items = ['<div class="hall-wall">']
    for record in records:
        title = escape(record["key"].replace("_", " ").title())
        label = escape(record["label"])
        items.append(f'<article class="hall-plaque"><span>{title}</span><strong>{label}</strong></article>')
    items.append("</div>")
    return "\n".join(items)


CSS = """
:root {
  color-scheme: dark;
  --ink: #f8e8c8;
  --ember: #ffd37a;
  --amber: #dca861;
  --brass: #c4934e;
  --walnut: #5b331c;
  --dark-walnut: #211018;
  --stone: #50494a;
  --felt: #2f724f;
  --felt-dark: #15351f;
  --burgundy: #5a2230;
  --danger: #bd3f35;
  --confirm: #65b96f;
  --raise: #d88736;
  --all-in: #8965d6;
  --z-bg: 0;
  --z-stage: 10;
  --z-table: 20;
  --z-avatars: 30;
  --z-speech: 40;
  --z-hud: 50;
  --z-actions: 60;
  --z-modal: 100;
}
.gradio-container {
  color: var(--ink) !important;
  background:
    linear-gradient(180deg, rgba(10, 7, 9, .58), rgba(10, 7, 9, .62)),
    url("/gradio_api/file=assets/token-holdem/tavern-bg-main-1672x941.png") center top / cover fixed,
    radial-gradient(circle at 18% 8%, rgba(255, 189, 94, .13), transparent 18rem),
    radial-gradient(circle at 88% 18%, rgba(255, 211, 122, .09), transparent 16rem),
    repeating-linear-gradient(0deg, rgba(255,255,255,.025) 0 2px, transparent 2px 34px),
    repeating-linear-gradient(90deg, rgba(255,255,255,.018) 0 2px, transparent 2px 54px),
    linear-gradient(180deg, #181217 0%, #100d12 38%, #17100f 100%) !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace !important;
  min-height: 100dvh;
}
.gradio-container > .main, .gradio-container .wrap, .gradio-container .contain { max-width: none !important; }
.gradio-container [role="tablist"],
.gradio-container [role="tabpanel"],
.gradio-container .tabs,
.gradio-container .tab-nav,
.gradio-container .tabitem {
  border-color: transparent !important;
  box-shadow: none !important;
}
.gradio-container [role="tabpanel"] {
  background: transparent !important;
}
.app-title {
  width: min(100%, 1440px);
  margin: 0 auto 8px;
  text-align: center;
  padding: 10px 18px;
  border: 2px solid var(--brass);
  border-radius: 8px;
  background:
    linear-gradient(90deg, rgba(255,211,122,.06), transparent 14%, transparent 86%, rgba(255,211,122,.06)),
    repeating-linear-gradient(0deg, rgba(255,255,255,.035) 0 2px, transparent 2px 11px),
    linear-gradient(180deg, #3a1d18, #1b1114);
  box-shadow: 0 0 0 3px rgba(40,20,14,.85), 0 12px 28px rgba(0,0,0,.48), 0 0 24px rgba(255,171,74,.12) inset;
}
.app-title h1 { margin: 0; color: var(--ember); font-size: clamp(28px, 4vw, 46px); letter-spacing: 0; text-shadow: 3px 3px #5a2415; }
.app-title p { margin: 4px 0 0; color: #f5dec0; font-weight: 800; }
.tavern-app-shell {
  position: relative;
  isolation: isolate;
  min-height: calc(100dvh - 132px);
  width: min(100%, 1540px);
  margin: 0 auto;
  padding: clamp(10px, 1.4vw, 18px);
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.tavern-app-shell > .styler,
.tavern-app-shell > .gr-group > .styler {
  position: relative;
  z-index: 2;
  min-height: calc(100dvh - 170px);
  display: grid !important;
  grid-template-columns: minmax(220px, 250px) minmax(720px, 1fr) minmax(230px, 260px);
  grid-template-rows: minmax(0, 1fr) auto auto;
  grid-template-areas:
    "left stage right"
    "actions actions actions"
    "status status status";
  gap: clamp(10px, 1.2vw, 16px);
  align-items: stretch;
}
.tavern-scene-chrome {
  position: absolute !important;
  inset: 0;
  z-index: 0;
  padding: 0 !important;
  margin: 0 !important;
  pointer-events: none;
}
.tavern-scene-chrome .tavern-background,
.tavern-scene-chrome .tavern-ambient-lights {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: var(--z-bg);
}
.tavern-scene-chrome .tavern-background {
  background:
    linear-gradient(180deg, rgba(12,8,8,.08), rgba(12,8,8,.16)),
    url("/gradio_api/file=assets/token-holdem/tavern-bg-main-1672x941.png") center center / cover no-repeat,
    linear-gradient(180deg, rgba(93,86,82,.35), rgba(24,14,16,.72) 47%, rgba(23,12,8,.92)),
    repeating-linear-gradient(0deg, rgba(255,255,255,.035) 0 2px, transparent 2px 44px),
    repeating-linear-gradient(90deg, rgba(0,0,0,.16) 0 3px, transparent 3px 86px);
}
.tavern-stonework { position: absolute; inset: 0 0 42%; opacity: .82; }
.tavern-bar-backdrop {
  position: absolute;
  left: 21%;
  right: 21%;
  top: 7%;
  height: clamp(70px, 10vw, 118px);
  border: 4px solid rgba(47,25,16,.86);
  border-left-width: 24px;
  border-right-width: 24px;
  background:
    radial-gradient(circle at 46% 66%, rgba(255,191,92,.28) 0 20px, transparent 21px),
    radial-gradient(circle at 14% 52%, rgba(116,145,94,.48) 0 12px, transparent 13px),
    radial-gradient(circle at 82% 54%, rgba(140,76,86,.5) 0 12px, transparent 13px),
    linear-gradient(180deg, #59351f, #23120f);
  box-shadow: 0 10px 0 rgba(17,9,7,.84), 0 32px 60px rgba(0,0,0,.35);
  opacity: .12;
}
.tavern-floor {
  position: absolute;
  left: -8%;
  right: -8%;
  bottom: -9%;
  height: 43%;
  background: repeating-linear-gradient(90deg, rgba(104,58,30,.16) 0 48px, rgba(55,29,20,.20) 48px 54px);
  transform: perspective(680px) rotateX(58deg);
  transform-origin: bottom;
}
.tavern-scene-chrome .tavern-ambient-lights {
  z-index: 1;
  background:
    radial-gradient(circle at 14% 23%, rgba(255,190,90,.24), transparent 13rem),
    radial-gradient(circle at 86% 22%, rgba(255,202,118,.20), transparent 14rem),
    radial-gradient(circle at 50% 47%, rgba(255,226,154,.13), transparent 23rem),
    radial-gradient(ellipse at 50% 100%, rgba(10,5,6,.72), transparent 48%);
  animation: ambient-glow 3.8s ease-in-out infinite alternate;
}
.tavern-left-rail, .tavern-right-rail, .poker-stage, .action-bar, .bottom-status-panel {
  position: relative;
  z-index: var(--z-hud);
  min-width: 0;
}
.tavern-left-rail { grid-area: left; }
.tavern-right-rail { grid-area: right; }
.poker-stage {
  grid-area: stage;
  z-index: var(--z-stage);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}
.action-bar { grid-area: actions; z-index: var(--z-actions); }
.bottom-status-panel { grid-area: status; }
.rail-plaque {
  padding: 14px;
  border: 2px solid rgba(196,147,78,.75);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(68,38,23,.92), rgba(25,15,17,.94));
  box-shadow: 0 10px 24px rgba(0,0,0,.32), 0 0 0 2px rgba(255,211,122,.05) inset;
}
.rail-plaque h2 { margin: 3px 0 5px; color: var(--ember); font-size: 22px; letter-spacing: 0; }
.rail-plaque p { margin: 0; color: #f5dec0; font-size: 12px; line-height: 1.35; }
.rail-kicker { color: #b7f7c1; font-weight: 900; font-size: 10px; text-transform: uppercase; }
.tavern-panel, .action-panel {
  max-width: 1120px;
  margin: 10px auto;
  padding: 12px;
  border: 1px solid rgba(196,147,78,.72);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(42,24,32,.94), rgba(23,16,22,.94));
  box-shadow: 0 8px 22px rgba(0,0,0,.32), 0 0 0 2px rgba(255,211,122,.04) inset;
}
.tavern-app-shell .tavern-panel,
.tavern-app-shell .setup-panel,
.tavern-app-shell .log-panel,
.tavern-app-shell .review-panel,
.tavern-app-shell .status-scroll,
.tavern-app-shell .action-bar {
  max-width: none;
  width: 100%;
  margin: 0 !important;
}
.tavern-app-shell .setup-panel { display: grid; gap: 8px; }
.tavern-app-shell .setup-panel .block,
.tavern-app-shell .setup-panel .form,
.tavern-app-shell .setup-panel .wrap,
.tavern-app-shell .setup-panel .styler,
.tavern-app-shell .action-bar .block,
.tavern-app-shell .action-bar .form,
.tavern-app-shell .action-bar .wrap,
.tavern-app-shell .action-bar .styler,
.tavern-app-shell .action-row,
.tavern-app-shell .action-row .styler {
  border-color: rgba(196,147,78,.35) !important;
  background: transparent !important;
  box-shadow: none !important;
}
.tavern-app-shell label,
.tavern-app-shell .setup-panel span,
.tavern-app-shell .setup-panel .label-wrap {
  color: #f5dec0 !important;
  font-family: ui-monospace, monospace !important;
  font-weight: 800 !important;
}
.tavern-app-shell input,
.tavern-app-shell textarea {
  border: 1px solid rgba(255,211,122,.42) !important;
  border-radius: 6px !important;
  background: rgba(11, 8, 11, .82) !important;
  color: #fff1c4 !important;
  font-family: ui-monospace, monospace !important;
  box-shadow: inset 0 0 0 1px rgba(255,211,122,.06) !important;
}
.tavern-app-shell input:focus,
.tavern-app-shell textarea:focus {
  border-color: var(--ember) !important;
  outline: 2px solid rgba(255,211,122,.28) !important;
  outline-offset: 1px !important;
}
.status-scroll {
  max-width: 1120px;
  margin: 10px auto !important;
  padding: 10px 12px;
  border: 1px solid rgba(255,211,122,.65);
  border-radius: 8px;
  color: #fff1c4;
  background: rgba(55,35,27,.86);
  font-weight: 900;
}
.token-table-shell { width: min(100%, 1120px); margin: 10px auto 18px; }
.poker-stage .token-table-shell { width: 100%; margin: 0; }
.table-status-bar { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin: 0 auto 6px; color: #f3d7a2; font: 800 11px ui-monospace, monospace; opacity: .92; }
.table-status-bar span { min-height: 26px; display: inline-flex; align-items: center; padding: 2px 9px; border: 1px solid rgba(196,147,78,.48); border-radius: 6px; background: rgba(18,12,16,.70); box-shadow: 0 2px 0 rgba(0,0,0,.46); }
.token-table {
  position: relative;
  overflow: visible;
  aspect-ratio: 16 / 10;
  min-height: clamp(560px, 59dvh, 720px);
  border: 0;
  border-radius: 26px;
  background: transparent;
  box-shadow: none;
}
.tavern-scene { position: relative; }
.tavern-backdrop { position: absolute; inset: 0; z-index: 0; overflow: hidden; background: transparent; }
.tavern-backdrop::before {
  content: "";
  position: absolute;
  inset: 0 0 36%;
  background:
    repeating-linear-gradient(0deg, rgba(255,255,255,.035) 0 2px, transparent 2px 42px),
    repeating-linear-gradient(90deg, rgba(0,0,0,.14) 0 3px, transparent 3px 86px);
  opacity: .08;
}
.tavern-backdrop::after {
  content: "";
  position: absolute;
  left: 11%;
  right: 11%;
  top: 13%;
  height: 58px;
  border: 3px solid #3a2118;
  border-left-width: 18px;
  border-right-width: 18px;
  background:
    radial-gradient(circle at 14% 55%, #96623a 0 7px, transparent 8px),
    radial-gradient(circle at 24% 55%, #62805e 0 8px, transparent 9px),
    radial-gradient(circle at 70% 55%, #8f4e5b 0 7px, transparent 8px),
    linear-gradient(180deg, #4b2a18, #261410);
  box-shadow: 0 7px 0 #1a0f0d, 0 22px 34px rgba(0,0,0,.34);
  opacity: .08;
}
.wall-stone { position: absolute; width: 120px; height: 38px; border: 2px solid rgba(0,0,0,.08); background: rgba(118,108,102,.04); }
.wall-stone-a { top: 7%; left: 6%; }
.wall-stone-b { top: 23%; right: 8%; width: 160px; }
.bartender-shadow { position: absolute; left: 50%; top: 17%; width: 52px; height: 72px; transform: translateX(-50%); border-radius: 18px 18px 8px 8px; background: linear-gradient(180deg, rgba(226,165,92,.20), rgba(42,24,20,.32)); box-shadow: 0 0 24px rgba(255,189,94,.10); opacity: .2; }
.floor-planks { position: absolute; left: -4%; right: -4%; bottom: 0; height: 36%; background: repeating-linear-gradient(90deg, rgba(92,51,28,.12) 0 42px, rgba(56,31,23,.14) 42px 47px); transform: perspective(500px) rotateX(58deg); transform-origin: bottom; opacity: .2; }
.candle { position: absolute; top: 25%; width: 13px; height: 40px; border-radius: 4px 4px 2px 2px; background: linear-gradient(180deg, #fff1c4, #b8763d); box-shadow: 0 0 22px 9px rgba(255,183,74,.22); }
.candle::before { content: ""; position: absolute; left: 3px; top: -13px; width: 7px; height: 15px; border-radius: 50% 50% 45% 45%; background: #ffd37a; box-shadow: 0 0 18px 8px rgba(255,171,74,.45); animation: candle-flicker 1.9s ease-in-out infinite alternate; }
.candle-left { left: 5%; }
.candle-right { right: 5%; animation-delay: .6s; }
.table-felt {
  position: absolute;
  inset: 13% 4% 7%;
  z-index: var(--z-table);
  border: clamp(22px, 3.1vw, 36px) solid var(--walnut);
  border-radius: 50%;
  background:
    linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px),
    linear-gradient(0deg, rgba(0,0,0,.085) 1px, transparent 1px),
    repeating-linear-gradient(45deg, rgba(255,255,255,.035) 0 3px, transparent 3px 9px),
    repeating-linear-gradient(-45deg, rgba(0,0,0,.055) 0 4px, transparent 4px 12px),
    radial-gradient(ellipse at 50% 45%, rgba(255,255,255,.10), transparent 28%),
    radial-gradient(ellipse at center, #2c6a49 0%, #24563a 48%, #14351f 76%);
  background-size: 10px 10px, 10px 10px, auto, auto, auto, auto;
  image-rendering: pixelated;
  box-shadow:
    0 0 0 4px #2a130c,
    0 0 0 9px #a46e39,
    0 0 0 14px #2f1710,
    0 0 42px rgba(0,0,0,.78) inset,
    0 26px 46px rgba(0,0,0,.62);
}
.table-felt::before {
  content: "";
  position: absolute;
  inset: -26px;
  border-radius: 50%;
  background:
    repeating-linear-gradient(90deg, rgba(255,211,122,.10) 0 7px, rgba(42,19,10,.16) 7px 14px),
    linear-gradient(180deg, rgba(117,65,32,.80), rgba(45,22,13,.92));
  z-index: -1;
}
.table-felt::after { content: ""; position: absolute; inset: 14%; border: 2px dashed rgba(255,211,122,.20); border-radius: 50%; box-shadow: 0 0 0 1px rgba(0,0,0,.12); }
.table-chip-pile {
  position: absolute;
  left: 50%;
  top: 39%;
  z-index: calc(var(--z-table) + 8);
  transform: translate(-50%, -50%);
  width: 92px;
  height: 42px;
  pointer-events: none;
}
.table-chip-pile span {
  position: absolute;
  bottom: 7px;
  width: 22px;
  height: 26px;
  border-radius: 6px 6px 4px 4px;
  background: repeating-linear-gradient(0deg, #bd4a2e 0 4px, #ffd37a 4px 6px, #58301f 6px 8px);
  box-shadow: 2px 3px 0 rgba(0,0,0,.54), 0 0 0 2px rgba(255,241,196,.08) inset;
}
.table-chip-pile span:nth-child(1) { left: 18px; height: 32px; background: repeating-linear-gradient(0deg, #bd4a2e 0 4px, #ffd37a 4px 6px, #58301f 6px 8px); }
.table-chip-pile span:nth-child(2) { left: 38px; height: 38px; background: repeating-linear-gradient(0deg, #4f9565 0 4px, #fff1c4 4px 6px, #1f432d 6px 8px); }
.table-chip-pile span:nth-child(3) { left: 58px; height: 30px; background: repeating-linear-gradient(0deg, #6e5a9d 0 4px, #fff1c4 4px 6px, #2c2346 6px 8px); }
.table-chip-pile b {
  position: absolute;
  left: 50%;
  bottom: -15px;
  transform: translateX(-50%);
  padding: 2px 8px;
  border: 1px solid rgba(255,211,122,.5);
  border-radius: 5px;
  color: #ffe29a;
  background: rgba(19,12,13,.82);
  font: 900 11px ui-monospace, monospace;
}
.table-chip-pile-empty { opacity: .45; top: 42%; }
.token-table-empty { display: grid; place-items: center; }
.center-hud {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: calc(var(--z-table) + 12);
  width: min(48%, 500px);
  min-width: 360px;
  padding: 10px 12px 12px;
  text-align: center;
  border: 2px solid var(--brass);
  border-radius: 8px;
  background: rgba(20, 14, 16, .66);
  box-shadow: 0 10px 20px rgba(0,0,0,.42), 0 0 0 3px rgba(255,211,122,.05) inset;
}
.hud-kicker { color: #d1b37c; font: 700 11px ui-monospace, monospace; text-transform: uppercase; }
.current-actor { margin-top: 2px; color: #fff1c4; font: 900 18px ui-monospace, monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pot { color: #ffe29a; font: 900 24px ui-monospace, monospace; text-shadow: 0 0 12px rgba(255,211,122,.3); }
.street { color: #b7f7c1; font: 800 13px ui-monospace, monospace; margin-bottom: 8px; }
.result-banner { margin-top: 8px; padding: 7px 9px; border-radius: 6px; color: #120b17; background: linear-gradient(180deg, #ffe29a, #dca861); font: 900 12px ui-monospace, monospace; box-shadow: 0 3px 0 #5b331c; }
.card-row { position: relative; z-index: calc(var(--z-table) + 14); display: flex; justify-content: center; align-items: center; gap: clamp(5px, .8vw, 10px); min-height: clamp(58px, 8vw, 78px); }
.card, .mini-card { display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto; background: linear-gradient(180deg, #fff9e8, #ead7b4); color: #1b1520; border: 3px solid #3b2a24; border-radius: 4px; font-weight: 900; font-family: ui-monospace, monospace; box-shadow: 4px 4px 0 #000, 0 0 0 2px rgba(255,255,255,.18) inset; image-rendering: pixelated; }
.card { width: clamp(44px, 5.2vw, 58px); height: clamp(62px, 7.3vw, 78px); font-size: clamp(16px, 2vw, 20px); }
.mini-card { width: 28px; height: 38px; font-size: 12px; }
.red-card { color: #a72828; }
.hidden-card { background:
  radial-gradient(circle at 50% 50%, rgba(255,211,122,.22), transparent 13px),
  repeating-linear-gradient(45deg, #5b331c 0 4px, #20122f 4px 8px, #33214d 8px 12px);
  color: var(--ember);
}
.card-slot { background: rgba(255,241,212,.13); border-style: dashed; box-shadow: none; color: transparent; }
.seat-layer { position: absolute; inset: 0; z-index: var(--z-avatars); pointer-events: none; }
.seat-ring { position: absolute; inset: 0; z-index: var(--z-avatars); pointer-events: none; }
.seat {
  position: absolute;
  z-index: var(--z-avatars);
  left: var(--seat-x);
  top: var(--seat-y);
  transform: translate(-50%, -50%);
  width: clamp(150px, 14vw, 206px);
  min-height: 202px;
  display: block;
  padding: 0;
  text-align: center;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease, opacity 180ms ease, filter 180ms ease;
  pointer-events: auto;
}
.seat-2, .seat-6 { width: clamp(138px, 12.2vw, 178px); }
.human-seat { width: clamp(210px, 20vw, 286px); min-height: 240px; border-color: rgba(255,211,122,.8); }
.seat-layer > .human-seat { z-index: calc(var(--z-avatars) + 2); }
.avatar-layer { position: relative; z-index: 2; min-width: 0; height: clamp(132px, 13vw, 184px); pointer-events: none; }
.human-seat .avatar-layer { height: clamp(160px, 16vw, 222px); }
.avatar-slot {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: visible;
  border-radius: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: #130e12;
  font: 900 13px ui-monospace, monospace;
  text-shadow: 0 1px rgba(255,255,255,.28);
}
.avatar-slot img {
  width: 118%;
  height: 118%;
  object-fit: contain;
  display: block;
  image-rendering: auto;
  filter: drop-shadow(0 12px 9px rgba(0,0,0,.62)) drop-shadow(0 0 12px color-mix(in srgb, var(--avatar-accent, #dca861), transparent 72%));
}
.avatar-slot img + span { display: none; }
.seat-plaque, .hud-layer, .seat-copy, .seat-meta { min-width: 0; }
.seat-plaque {
  position: relative;
  z-index: 3;
  margin: -20px auto 0;
  width: min(100%, 178px);
  padding: 7px 8px 8px;
  border: 2px solid rgba(196,147,78,.78);
  border-radius: 6px;
  background: linear-gradient(180deg, rgba(51,31,24,.94), rgba(18,12,16,.96));
  box-shadow: 0 4px 0 rgba(0,0,0,.72), 0 0 0 2px rgba(255,211,122,.05) inset;
}
.human-seat .seat-plaque { width: min(100%, 210px); }
.seat-label { min-height: 18px; display: flex; flex-wrap: wrap; align-items: center; gap: 3px; overflow: hidden; }
.seat-index { display: none; }
.persona-role { display: none; }
.seat-name { color: var(--ember); font: 900 13px ui-monospace, monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.seat-persona { color: #f5dec0; font: 800 10px ui-monospace, monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.llm-seat .seat-persona { display: none; }
.seat-stack { color: #b7f7c1; font: 900 11px ui-monospace, monospace; white-space: nowrap; }
.seat-meta { display: grid; grid-template-columns: 1fr; gap: 3px; align-items: center; margin-top: 4px; }
.seat-bet, .seat-status, .seat-badge, .seat-last-action { display: inline-flex; align-items: center; min-height: 18px; padding: 1px 5px; border-radius: 5px; font: 900 10px ui-monospace, monospace; }
.seat-bet { justify-content: center; color: #f5dec0; background: #37231b; }
.seat-status { color: #121014; background: #b7f7c1; }
.seat-status { justify-content: center; }
.seat-badge { color: #120b17; background: var(--ember); border: 1px solid var(--ember); }
.seat-last-action { display: none; }
.seat > .speech-bubble-layer { grid-column: 1 / 3; }
.seat-talk { display: none; }
.seat-cards { display: flex; justify-content: center; gap: 5px; min-height: 34px; margin-top: 6px; }
.active-seat .seat-plaque { border-color: var(--ember); box-shadow: 0 0 0 3px rgba(255,211,122,.20), 0 0 22px rgba(255,211,122,.42), 0 4px 0 rgba(0,0,0,.72); }
.active-seat .seat-status { background: var(--ember); }
.active-seat .avatar-slot { animation: active-seat-glow 1.8s ease-in-out infinite alternate; }
.winner-seat .seat-plaque { border-color: var(--ember); box-shadow: 0 0 0 3px rgba(255,211,122,.24), 0 0 30px rgba(255,211,122,.56), 0 4px 0 rgba(0,0,0,.72); }
.winner-seat .seat-status { background: var(--ember); }
.folded-seat { opacity: .58; filter: grayscale(.55) saturate(.65); }
.all-in-seat .seat-plaque { border-color: #b7f7c1; }
.empty-seat { opacity: .62; }
.muted { opacity: .74; }
.dealer-button { position: absolute; left: var(--dealer-x); top: var(--dealer-y); transform: translate(-50%, -50%); z-index: calc(var(--z-table) + 5); width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 50%; border: 3px solid #4b2a18; color: #1b1520; background: radial-gradient(circle at 36% 28%, #fff1c4, #ffe29a 44%, #c4934e 78%); font: 900 16px ui-monospace, monospace; box-shadow: 2px 3px 0 #000, 0 0 12px rgba(255,211,122,.42); transition: left 220ms ease, top 220ms ease; animation: dealer-pulse 1.8s ease-in-out infinite; }
.table-speech-layer { position: absolute; inset: 0; z-index: var(--z-speech); pointer-events: none; }
.speech-bubble {
  position: absolute;
  left: var(--bubble-x);
  top: var(--bubble-y);
  transform: translate(-50%, -100%);
  width: clamp(150px, 16vw, 210px);
  max-height: 76px;
  overflow: hidden;
  padding: 8px 10px;
  border: 2px solid var(--avatar-accent, var(--brass));
  border-radius: 8px;
  color: #fff1c4;
  background: rgba(22, 14, 17, .96);
  box-shadow: 0 10px 20px rgba(0,0,0,.42), 0 0 18px color-mix(in srgb, var(--avatar-accent, #dca861), transparent 70%);
  animation: speech-float 420ms ease-out both;
}
.speech-bubble strong { display: block; color: var(--ember); font-size: 10px; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.speech-bubble span { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; color: #f5dec0; font-size: 11px; line-height: 1.25; overflow: hidden; }
.tavern-log { max-height: 360px; overflow: auto; color: #f5dec0; }
.tavern-log ul { margin: 8px 0 0 18px; padding: 0; }
.tavern-log li { margin: 3px 0; }
.log-board, .log-talk-title { color: var(--ember); font-weight: 900; }
.log-talk { border-top: 1px solid rgba(196,147,78,.36); padding-top: 8px !important; }
.tavern-ledger { overflow-x: auto; }
.tavern-ledger table { width: 100%; min-width: 820px; border-collapse: collapse; color: #f8e8c8; }
.tavern-ledger th, .tavern-ledger td { padding: 8px 10px; border-bottom: 1px solid rgba(196,147,78,.25); text-align: right; white-space: nowrap; }
.tavern-ledger th:nth-child(2), .tavern-ledger td:nth-child(2), .tavern-ledger th:nth-child(3), .tavern-ledger td:nth-child(3) { text-align: left; }
.tavern-ledger th { color: var(--ember); background: rgba(91,51,28,.45); }
.runtime-report { overflow-x: auto; color: #f8e8c8; }
.runtime-report h3 { margin: 0 0 10px; color: var(--ember); }
.runtime-report table { width: 100%; min-width: 920px; border-collapse: collapse; }
.runtime-report th, .runtime-report td { padding: 7px 9px; border-bottom: 1px solid rgba(196,147,78,.24); text-align: left; vertical-align: top; }
.runtime-report th { color: var(--ember); background: rgba(91,51,28,.45); }
.runtime-report code { color: #b7f7c1; white-space: nowrap; }
.hall-wall { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.hall-plaque { padding: 12px; border: 1px solid var(--brass); border-radius: 8px; background: linear-gradient(180deg, rgba(91,51,28,.75), rgba(42,24,32,.75)); box-shadow: 0 3px 0 #110b0f; }
.hall-plaque span { display: block; color: #d1b37c; font-size: 12px; text-transform: uppercase; }
.hall-plaque strong { display: block; margin-top: 4px; color: #fff1c4; }
button { min-height: 44px; font-family: ui-monospace, monospace !important; border-radius: 8px !important; }
button:hover:not(:disabled) { filter: brightness(1.08); transform: translateY(-1px); }
button:active:not(:disabled) { transform: translateY(1px); }
button:focus-visible { outline: 3px solid var(--ember) !important; outline-offset: 2px !important; }
.setup-panel button {
  border: 1px solid rgba(255,211,122,.48) !important;
  background: linear-gradient(180deg, rgba(91,51,28,.95), rgba(42,24,32,.96)) !important;
  color: #fff1c4 !important;
  font-weight: 900 !important;
  opacity: 1 !important;
}
.setup-panel button:disabled {
  color: rgba(255,241,196,.55) !important;
  border-color: rgba(196,147,78,.28) !important;
  background: linear-gradient(180deg, rgba(55,35,27,.76), rgba(28,20,24,.82)) !important;
}
.setup-panel button.primary,
.setup-panel button[class*="primary"] {
  background: linear-gradient(180deg, #ff8b31, #b94a1d) !important;
  border-color: #ffd37a !important;
  color: #fff7d7 !important;
}
.action-panel { position: sticky; bottom: 8px; z-index: 20; }
.action-bar {
  padding: 10px;
  border: 2px solid rgba(196,147,78,.72);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(46,28,22,.96), rgba(17,11,14,.98));
  box-shadow: 0 10px 22px rgba(0,0,0,.36), 0 0 0 2px rgba(255,211,122,.05) inset;
}
.action-status {
  margin-bottom: 8px !important;
  text-align: center;
  font-size: 16px;
  color: #ffe29a !important;
  text-transform: none;
  letter-spacing: 0;
}
.action-status p { margin: 0; color: #ffe29a !important; }
.action-bar-caption { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 8px; margin-bottom: 8px; color: #d1b37c; font: 800 11px ui-monospace, monospace; text-transform: uppercase; }
.action-bar-caption strong { color: var(--ember); font-size: 13px; }
.action-row { display: grid !important; grid-template-columns: repeat(7, minmax(92px, 1fr)); gap: 8px; }
.action-row > *,
.action-row > .form,
.action-row > .block {
  min-width: 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
.poker-action button, button.poker-action { min-width: 0; font-weight: 900 !important; opacity: 1 !important; }
.fold-action button, button.fold-action { background: linear-gradient(180deg, #d75b4d, var(--danger)) !important; color: #fff3e4 !important; border-color: #ffc0a8 !important; }
.check-action button, button.check-action { background: linear-gradient(180deg, #55473e, #31272b) !important; color: #f5dec0 !important; border-color: #9a8060 !important; }
.call-action button, button.call-action { background: linear-gradient(180deg, #83d68b, var(--confirm)) !important; color: #10140f !important; border-color: #d7ffd6 !important; }
.raise-action button, button.raise-action { background: linear-gradient(180deg, #f0a84c, var(--raise)) !important; color: #171008 !important; border-color: #ffe2a0 !important; }
.all-in-action button, button.all-in-action { background: linear-gradient(180deg, #b59cff, var(--all-in)) !important; color: #fff7d7 !important; border-color: #ffe29a !important; }
@keyframes candle-flicker {
  from { transform: translateY(0) scaleX(1); opacity: .78; }
  to { transform: translateY(-1px) scaleX(.82); opacity: 1; }
}
@keyframes ambient-glow {
  from { opacity: .78; }
  to { opacity: 1; }
}
@keyframes speech-float {
  from { opacity: 0; transform: translate(-50%, -86%) scale(.96); }
  to { opacity: 1; transform: translate(-50%, -100%) scale(1); }
}
@keyframes dealer-pulse {
  0%, 100% { box-shadow: 2px 3px 0 #000, 0 0 10px rgba(255,211,122,.34); }
  50% { box-shadow: 2px 3px 0 #000, 0 0 20px rgba(255,211,122,.7); }
}
@keyframes active-seat-glow {
  from { filter: brightness(1); }
  to { filter: brightness(1.18); }
}
@media (prefers-reduced-motion: reduce) {
  .seat, .dealer-button, button, .candle::before, .speech-bubble, .avatar-slot, .tavern-ambient-lights { transition: none; animation: none; }
}
@media (max-width: 1240px) {
  .tavern-app-shell > .styler,
  .tavern-app-shell > .gr-group > .styler {
    grid-template-columns: minmax(190px, 23vw) minmax(460px, 1fr);
    grid-template-areas:
      "left stage"
      "right stage"
      "actions actions"
      "status status";
  }
  .tavern-right-rail .tavern-log { max-height: 220px; }
}
@media (max-width: 980px) {
  .tavern-app-shell > .styler,
  .tavern-app-shell > .gr-group > .styler {
    min-height: auto;
    grid-template-columns: 1fr;
    grid-template-areas:
      "left"
      "stage"
      "right"
      "actions"
      "status";
  }
  .tavern-left-rail .setup-panel { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .rail-plaque { display: none; }
  .token-table { min-height: 660px; aspect-ratio: auto; }
  .table-felt { inset: 3% 4% 21%; border-width: 12px; }
  .center-hud { top: 38%; width: min(76%, 460px); min-width: 280px; }
  .seat { width: 136px; min-height: 128px; padding: 6px; grid-template-columns: 36px minmax(0, 1fr); }
  .seat-talk { display: none; }
  .human-seat { width: min(78%, 320px); top: 82% !important; }
  .avatar-slot { width: 36px; height: 36px; }
  .mini-card { width: 24px; height: 34px; }
  .action-row { grid-template-columns: repeat(4, minmax(112px, 1fr)); }
}
@media (max-width: 680px) {
  .app-title { padding: 12px; }
  .tavern-app-shell { padding: 7px; border-left: 0; border-right: 0; }
  .tavern-app-shell > .styler,
  .tavern-app-shell > .gr-group > .styler { gap: 8px; }
  .tavern-left-rail .setup-panel { grid-template-columns: 1fr; }
  .token-table-shell { margin-top: 6px; }
  .table-status-bar { justify-content: flex-start; overflow-x: auto; padding-bottom: 3px; }
  .token-table { min-height: 800px; border-width: 4px; }
  .table-felt { inset: 6% 3% 32%; border-width: 10px; }
  .center-hud { top: 27%; width: calc(100% - 28px); min-width: 0; padding: 10px; }
  .seat-ring { position: absolute; left: 10px; right: 10px; top: 43%; bottom: 172px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; overflow: auto; align-content: start; }
  .seat { position: relative; left: auto; top: auto; transform: none; width: auto; min-height: 108px; }
  .human-seat { position: absolute; left: 50%; right: auto; top: auto !important; bottom: 10px; transform: translateX(-50%); width: calc(100% - 28px); min-height: 134px; }
  .seat-0 { order: 8; }
  .dealer-button { width: 30px; height: 30px; font-size: 14px; }
  .table-speech-layer { display: none; }
  .current-actor { font-size: 15px; }
  .pot { font-size: 19px; }
  .seat-name { font-size: 12px; }
  .persona-role { max-width: 76px; }
  .action-row { grid-template-columns: repeat(2, minmax(126px, 1fr)); }
  .tavern-panel, .action-panel { padding: 9px; }
}
"""
