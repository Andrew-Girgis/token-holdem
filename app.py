from __future__ import annotations

import itertools
import time
import uuid
import warnings
from dataclasses import dataclass, field

warnings.filterwarnings(
    "ignore",
    message="'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated.*",
)

import gradio as gr

from token_holdem.agents import ROSTER, fallback_decide
from token_holdem.cards import cards_label
from token_holdem.engine import GameState, make_players
from token_holdem.leaderboard import Leaderboard
from token_holdem.logging_utils import get_logger, log_event
from token_holdem.logging_utils import LOG_FILE
from token_holdem.model_runtime import TransformersRuntime
from token_holdem.render import CSS, hall_markdown, leaderboard_markdown, log_markdown, table_html


HAND_COUNTER = itertools.count(1)


@dataclass
class AppSession:
    game: GameState | None = None
    chats: list[str] = field(default_factory=list)
    stopped: bool = False
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    hand_no: int = 0
    orbit_no: int = 1


leaderboard = Leaderboard()
model_runtime = TransformersRuntime()
logger = get_logger("token_holdem.app")


def _play_outputs(session: AppSession | None, status: str = ""):
    game = session.game if session else None
    return (
        session,
        table_html(game),
        log_markdown(game, session.chats if session else None),
        _leaderboard_md(),
        _hall_md(),
        status or _play_status(session),
        hand_review_markdown(session),
        *_action_button_updates(session),
        gr.update(interactive=bool(session and session.stopped)),
    )


def _play_status(session: AppSession | None) -> str:
    if session is None or session.game is None:
        return "Quick Seat starts a cash-game session."
    if session.stopped:
        return "You are busted. Rebuy to keep playing this cash game."
    game = session.game
    if game.result:
        return f"Hand complete: {game.result.summary} Click Next Hand to continue with current stacks."
    current = game.current_player()
    if current.is_human:
        legal = game.legal_actions(current.id)
        return f"Your turn. To call: {legal['to_call']}. Stack: {current.stack}."
    return f"{current.name} is thinking..."


def _action_button_updates(session: AppSession | None):
    hidden = [
        gr.update(interactive=False, visible=False, value="Fold"),
        gr.update(interactive=False, visible=False, value="Check"),
        gr.update(interactive=False, visible=False, value="Call"),
        gr.update(interactive=False, visible=False, value="Min Raise"),
        gr.update(interactive=False, visible=False, value="Half-Pot"),
        gr.update(interactive=False, visible=False, value="Pot"),
        gr.update(interactive=False, visible=False, value="All-In"),
    ]
    disabled = [
        gr.update(interactive=False, visible=True, value="Fold"),
        gr.update(interactive=False, visible=True, value="Check"),
        gr.update(interactive=False, visible=True, value="Call"),
        gr.update(interactive=False, visible=True, value="Min Raise"),
        gr.update(interactive=False, visible=True, value="Half-Pot"),
        gr.update(interactive=False, visible=True, value="Pot"),
        gr.update(interactive=False, visible=True, value="All-In"),
    ]
    if session is None or session.game is None or session.game.result or session.stopped:
        return hidden
    game = session.game
    current = game.current_player()
    if not current.is_human:
        return disabled
    legal = game.legal_actions(current.id)
    actions = set(legal["actions"])
    presets = legal["raise_presets"]
    return [
        gr.update(interactive="fold" in actions, visible=True, value="Fold"),
        gr.update(interactive="check" in actions, visible=True, value="Check"),
        gr.update(interactive="call" in actions, visible=True, value=f"Call {legal['to_call']}"),
        gr.update(interactive="raise" in actions, visible=True, value=f"Min {presets.get('min', 0)}"),
        gr.update(interactive="raise" in actions, visible=True, value=f"Half-Pot {presets.get('half_pot', 0)}"),
        gr.update(interactive="raise" in actions, visible=True, value=f"Pot {presets.get('pot', 0)}"),
        gr.update(interactive="all_in" in actions, visible=True, value=f"All-In {presets.get('all_in', current.stack)}"),
    ]


def hand_review_markdown(session: AppSession | None) -> str:
    if session is None or session.game is None:
        return "**Hand Review:** No active hand."
    game = session.game
    button = game.players[game.dealer_index].name
    small_blind = game.players[game.small_blind_index].name if game.small_blind_index is not None else "-"
    big_blind = game.players[game.big_blind_index].name if game.big_blind_index is not None else "-"
    current = "Complete" if game.result else game.current_player().name
    legal = {} if game.result else game.legal_actions(game.current_player().id)
    showdown = ""
    if game.result and game.result.showdown:
        showdown_lines = []
        for player in game.players:
            if player.id in game.result.showdown:
                marker = " winner" if player.id in game.result.winners else ""
                showdown_lines.append(f"  - {player.name}: {game.result.showdown[player.id]}{marker}")
        showdown = "\n- Showdown:\n" + "\n".join(showdown_lines)
    return (
        "**Hand Review**\n\n"
        f"- Session: `{game.session_id or '-'}`\n"
        f"- Hand: `{game.hand_id or '-'}`\n"
        f"- Orbit: `{game.orbit_id or '-'}`\n"
        f"- Button: **{button}**\n"
        f"- Small blind: **{small_blind}**\n"
        f"- Big blind: **{big_blind}**\n"
        f"- Street: **{game.street.value}**\n"
        f"- Current actor: **{current}**\n"
        f"- Legal actions: `{legal}`"
        f"{showdown}"
    )


def _ensure_roster() -> None:
    for idx, profile in enumerate(ROSTER):
        leaderboard.ensure_player(f"ai_{idx}", profile.name, "model", profile.model_id, profile.persona)


def _start_game(human_name: str, seed: int | None, mode: str) -> AppSession:
    _ensure_roster()
    human_name = (human_name or "Human Wanderer").strip()[:32]
    if mode == "play":
        leaderboard.ensure_player("human", human_name, "human")
        profiles = ROSTER[:7]
        players = make_players([profile.name for profile in profiles], human_name=human_name)
    else:
        profiles = ROSTER[:7]
        players = make_players([profile.name for profile in profiles])
    hand_no = 1
    session = AppSession(hand_no=hand_no, orbit_no=1)
    game = GameState(
        players=players,
        seed=(seed or int(time.time())) + next(HAND_COUNTER),
        session_id=session.session_id,
        hand_id=f"{session.session_id}-h{hand_no:03d}",
        orbit_id=f"{session.session_id}-o{session.orbit_no:02d}",
    )
    game.start_hand()
    session.game = game
    log_event(logger, "session_started", mode=mode, session_id=session.session_id, hand_id=game.hand_id, orbit_id=game.orbit_id, hand_no=hand_no, seed=game.seed, players=[player.name for player in players])
    return session


def _start_next_cash_hand(session: AppSession, seed: int | None, human_name: str) -> AppSession:
    if session.game is None:
        return _start_game(human_name, seed, "play")
    game = session.game
    for player in game.players:
        if not player.is_human and player.stack <= 0:
            player.stack = 1_000
            log_event(logger, "ai_auto_rebuy", player=player.name, amount=1_000)
    human = next((player for player in game.players if player.is_human), None)
    if human and human.stack <= 0:
        session.stopped = True
        session.chats.append(f"{human.name}: busted and needs a rebuy to keep playing.")
        log_event(logger, "human_busted_rebuy_required", player=human.name)
        return session
    next_button = game.next_active_index(game.dealer_index)
    session.hand_no += 1
    session.orbit_no = ((session.hand_no - 1) // len(game.players)) + 1
    next_game = GameState(
        players=game.players,
        dealer_index=next_button,
        seed=(seed or int(time.time())) + next(HAND_COUNTER),
        session_id=session.session_id,
        hand_id=f"{session.session_id}-h{session.hand_no:03d}",
        orbit_id=f"{session.session_id}-o{session.orbit_no:02d}",
    )
    next_game.start_hand()
    session.game = next_game
    session.stopped = False
    log_event(
        logger,
        "cash_hand_started",
        session_id=session.session_id,
        hand_id=next_game.hand_id,
        orbit_id=next_game.orbit_id,
        hand_no=session.hand_no,
        seed=next_game.seed,
        button=next_game.players[next_game.dealer_index].name,
        small_blind=next_game.players[next_game.small_blind_index].name if next_game.small_blind_index is not None else None,
        big_blind=next_game.players[next_game.big_blind_index].name if next_game.big_blind_index is not None else None,
        stacks={player.name: player.stack for player in next_game.players},
    )
    return session


def start_play(human_name: str, seed: int | None):
    try:
        log_event(logger, "callback_start", callback="start_play", human_name=human_name, seed=seed)
        session = _start_game(human_name, seed, "play")
        _advance_ai_until_human(session, next(HAND_COUNTER))
        return _play_outputs(session)
    except Exception:
        logger.exception("callback_failed", extra={"event": {"callback": "start_play"}})
        raise


def start_play_with_runtime(human_name: str, seed: int | None):
    try:
        log_event(logger, "callback_start", callback="start_play_with_runtime", human_name=human_name, seed=seed, use_models=True)
        session = _start_game(human_name, seed, "play")
        yielded = False
        for output in _advance_ai_until_human_stream(session, next(HAND_COUNTER), use_models=True):
            yielded = True
            yield output
        if not yielded:
            yield _play_outputs(session)
    except Exception:
        logger.exception("callback_failed", extra={"event": {"callback": "start_play_with_runtime"}})
        raise


def human_action(session: AppSession | None, action: str):
    try:
        log_event(logger, "callback_start", callback="human_action", action=action, use_models=True, has_session=session is not None)
        if session is None or session.game is None or session.game.result:
            yield _play_outputs(session)
            return
        game = session.game
        legal = game.legal_actions()
        amount = 0
        if action == "min_raise":
            action = "raise"
            amount = legal["raise_presets"].get("min", 0)
        elif action == "half_pot":
            action = "raise"
            amount = legal["raise_presets"].get("half_pot", 0)
        elif action == "pot":
            action = "raise"
            amount = legal["raise_presets"].get("pot", 0)
        game.apply_action(action, amount)
        yield _play_outputs(session, status="Action accepted. The tavern waits for the next move...")
        for output in _advance_ai_until_human_stream(session, next(HAND_COUNTER), use_models=True):
            yield output
        if game.result:
            _record_result(game, "play")
        yield _play_outputs(session)
    except Exception:
        logger.exception("callback_failed", extra={"event": {"callback": "human_action", "action": action}})
        raise


def next_play_hand(session: AppSession | None, human_name: str, seed: int | None):
    try:
        log_event(logger, "callback_start", callback="next_play_hand", human_name=human_name, seed=seed, use_models=True)
        if session is None:
            for output in start_play_with_runtime(human_name, seed):
                yield output
            return
        session = _start_next_cash_hand(session, seed, human_name)
        if not session.stopped:
            yielded = False
            for output in _advance_ai_until_human_stream(session, next(HAND_COUNTER), use_models=True):
                yielded = True
                yield output
            if not yielded:
                yield _play_outputs(session)
        else:
            yield _play_outputs(session)
    except Exception:
        logger.exception("callback_failed", extra={"event": {"callback": "next_play_hand"}})
        raise


def rebuy_user(session: AppSession | None, amount: int = 1_000):
    try:
        log_event(logger, "callback_start", callback="rebuy_user", amount=amount, has_session=session is not None)
        if session and session.game:
            for player in session.game.players:
                if player.is_human:
                    player.stack = amount
                    session.stopped = False
                    session.chats.append(f"{player.name} rebuys for {amount} chips.")
                    log_event(logger, "human_rebuy", player=player.name, amount=amount)
                    break
        return _play_outputs(session)
    except Exception:
        logger.exception("callback_failed", extra={"event": {"callback": "rebuy_user"}})
        raise


def action_handler(action: str):
    def handle(session: AppSession | None):
        yield from human_action(session, action)

    return handle


def run_arena(seed: int | None, hands: int):
    try:
        log_event(logger, "callback_start", callback="run_arena", seed=seed, hands=hands, use_models=True)
        session = _start_game("", seed, "arena")
        for _ in range(max(1, min(int(hands or 1), 10))):
            if session.game is None or session.game.result:
                session = _start_game("", seed, "arena")
            hand_no = next(HAND_COUNTER)
            while session.game and not session.game.result:
                _take_ai_turn(session, hand_no, use_models=True)
                yield table_html(session.game, reveal_all=True), log_markdown(session.game, session.chats), _leaderboard_md(), _hall_md()
                time.sleep(0.25)
            if session.game and session.game.result:
                _record_result(session.game, "arena")
                session.chats.append(_chronicle(session.game))
                yield table_html(session.game, reveal_all=True), log_markdown(session.game, session.chats), _leaderboard_md(), _hall_md()
                time.sleep(0.5)
    except Exception:
        logger.exception("callback_failed", extra={"event": {"callback": "run_arena", "seed": seed, "hands": hands, "use_models": True}})
        raise


def _advance_ai_until_human(session: AppSession, hand_no: int, use_models: bool = False) -> None:
    while session.game and not session.game.result and not session.game.current_player().is_human:
        _take_ai_turn(session, hand_no, use_models=use_models)


def _advance_ai_until_human_stream(session: AppSession, hand_no: int, use_models: bool = False):
    while session.game and not session.game.result and not session.game.current_player().is_human:
        player = session.game.current_player()
        yield _play_outputs(session, status=f"{player.name} is thinking with {'local inference' if use_models else 'fallback persona'}...")
        _take_ai_turn(session, hand_no, use_models=use_models)
        yield _play_outputs(session, status=f"{player.name} acted. {_play_status(session)}")


def _take_ai_turn(session: AppSession, hand_no: int, use_models: bool = False) -> None:
    game = session.game
    if game is None:
        return
    player = game.current_player()
    profile = next((profile for profile in ROSTER if profile.name == player.name), ROSTER[0])
    summary = {
        "hand_no": hand_no,
        "street": game.street.value,
        "hole_cards": player.hole_cards,
        "community_cards": game.community_cards,
        "stack": player.stack,
        "pot": game.pot(),
        "legal": game.legal_actions(player.id),
        "history": game.action_log,
        "recent_chats": session.chats[-12:],
        "seed": game.seed,
        "session_id": game.session_id,
        "hand_id": game.hand_id,
        "orbit_id": game.orbit_id,
    }
    if use_models:
        runtime_result = model_runtime.decide(profile, summary)
        decision = runtime_result.decision
        session.chats.append(f"{player.name}: {decision['table_talk']}")
        log_event(logger, "ai_decision", session_id=game.session_id, hand_id=game.hand_id, orbit_id=game.orbit_id, player=player.name, source=runtime_result.source, status=runtime_result.status, action=decision.get("action"), amount=decision.get("amount"), street=game.street.value)
    else:
        decision = fallback_decide(profile, summary, seed=game.seed)
        session.chats.append(f"{player.name}: {decision['table_talk']}")
        log_event(logger, "ai_decision", session_id=game.session_id, hand_id=game.hand_id, orbit_id=game.orbit_id, player=player.name, source="fallback", status="disabled", action=decision.get("action"), amount=decision.get("amount"), street=game.street.value)
    game.apply_action(decision["action"], int(decision.get("amount") or 0))


def _record_result(game: GameState, mode: str) -> None:
    if not game.result:
        return
    if getattr(game, "_recorded", False):
        log_event(logger, "hand_record_skipped_duplicate", mode=mode, summary=game.result.summary)
        return
    names = {player.id: player.name for player in game.players}
    leaderboard.record_hand(
        mode,
        game.result.pot,
        cards_label(game.result.board),
        game.result.winners,
        game.result.deltas,
        names,
        game.result.summary,
        game.session_id,
        game.hand_id,
        game.orbit_id,
    )
    setattr(game, "_recorded", True)
    log_event(logger, "hand_recorded", mode=mode, session_id=game.session_id, hand_id=game.hand_id, orbit_id=game.orbit_id, pot=game.result.pot, winners=game.result.winners, deltas=game.result.deltas)


def _chronicle(game: GameState) -> str:
    if not game.result:
        return ""
    winner = game.player(game.result.winners[0]).name
    return f"Chronicle: {winner} raises a tiny mug to the rafters after dragging {game.result.pot} chips through the candle smoke."


def _leaderboard_md() -> str:
    return leaderboard_markdown(leaderboard.rows())


def _hall_md() -> str:
    return hall_markdown(leaderboard.hall_of_fame())


def recent_logs(limit: int = 80) -> str:
    if not LOG_FILE.exists():
        return "No app logs yet. Trigger a hand or Arena run first."
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-limit:]
    return "```json\n" + "\n".join(lines) + "\n```"


def build_app() -> gr.Blocks:
    _ensure_roster()
    with gr.Blocks(title="Token Hold'em") as demo:
        gr.HTML('<div class="app-title"><h1>Token Hold\'em</h1><p>A tiny pixel tavern where small models gamble with big personalities.</p></div>')
        play_state = gr.State(None)
        with gr.Tab("Play Mode"):
            with gr.Row():
                human_name = gr.Textbox(label="Your tavern name", value="Human Wanderer")
                play_seed = gr.Number(label="Seed", value=0, precision=0)
                start_btn = gr.Button("Quick Seat", variant="primary")
                next_btn = gr.Button("Next Hand")
                rebuy_btn = gr.Button("Rebuy 1000", interactive=False)
            play_table = gr.HTML(table_html(None))
            with gr.Row():
                fold_btn = gr.Button("Fold", interactive=False)
                check_btn = gr.Button("Check", interactive=False)
                call_btn = gr.Button("Call", interactive=False)
                min_btn = gr.Button("Min Raise", interactive=False)
                half_btn = gr.Button("Half-Pot", interactive=False)
                pot_btn = gr.Button("Pot", interactive=False)
                all_in_btn = gr.Button("All-In", interactive=False)
            play_status = gr.Markdown("Quick Seat starts a cash-game session.")
            play_log = gr.Markdown("No hand yet.")
            hand_review = gr.Markdown("**Hand Review:** No active hand.")
        with gr.Tab("AI Arena"):
            with gr.Row():
                arena_seed = gr.Number(label="Seed", value=0, precision=0)
                arena_hands = gr.Slider(label="Hands to auto-play", minimum=1, maximum=10, value=3, step=1)
                arena_btn = gr.Button("Start Arena", variant="primary")
            arena_table = gr.HTML(table_html(None))
            arena_log = gr.Markdown("The tavern is quiet.")
        with gr.Tab("Leaderboard"):
            leaderboard_out = gr.Markdown(_leaderboard_md())
        with gr.Tab("Hall of Fame"):
            hall_out = gr.Markdown(_hall_md())
        with gr.Tab("About"):
            gr.Markdown("Token Hold'em is a Thousand Token Wood hackathon app. The poker engine is deterministic. Local inference can be enabled for every model seat using small local substitute models while preserving each seat's persona prompt.")
        with gr.Tab("Diagnostics"):
            gr.Markdown("Structured app logs are written to `logs/token_holdem.jsonl`. Framework warnings from Gradio/Starlette may still appear in the terminal separately.")
            refresh_logs = gr.Button("Refresh Recent Logs")
            logs_out = gr.Markdown(recent_logs())

        play_outputs = [play_state, play_table, play_log, leaderboard_out, hall_out, play_status, hand_review, fold_btn, check_btn, call_btn, min_btn, half_btn, pot_btn, all_in_btn, rebuy_btn]
        start_btn.click(start_play_with_runtime, inputs=[human_name, play_seed], outputs=play_outputs)
        next_btn.click(next_play_hand, inputs=[play_state, human_name, play_seed], outputs=play_outputs)
        rebuy_btn.click(rebuy_user, inputs=[play_state], outputs=play_outputs)
        for button, action in [
            (fold_btn, "fold"),
            (check_btn, "check"),
            (call_btn, "call"),
            (min_btn, "min_raise"),
            (half_btn, "half_pot"),
            (pot_btn, "pot"),
            (all_in_btn, "all_in"),
        ]:
            button.click(action_handler(action), inputs=[play_state], outputs=play_outputs)
        arena_btn.click(run_arena, inputs=[arena_seed, arena_hands], outputs=[arena_table, arena_log, leaderboard_out, hall_out])
        refresh_logs.click(recent_logs, outputs=[logs_out])
    return demo


demo = build_app()


if __name__ == "__main__":
    demo.launch(css=CSS)
