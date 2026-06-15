# Token Hold'em

Token Hold'em is a whimsical Gradio poker tavern for the Hugging Face Build Small Hackathon, Thousand Token Wood track. Small model identities sit around a Texas Hold'em table, bluff, banter, win chips, lose chips, and build persistent reputations.

The poker engine is deterministic. Models and fallback agents only choose actions and generate table talk; they never calculate winners, legal actions, pots, or chip movement.

## Current Status

Implemented:

- Play Mode with a named human player against AI seats.
- True cash-game Play Mode: Quick Seat creates a table session, stacks persist across hands, the button rotates, and the user can rebuy after busting.
- AI Arena with six model identities and auto-played hands.
- Deterministic Hold'em flow: deck, blinds, betting, legal action repair, showdown, and chip settlement.
- `treys` hand evaluation.
- SQLite leaderboard and Hall of Fame records.
- Custom dark pixel-tavern Gradio UI.
- Fallback personality agents for all six seats.
- Local Transformers inference for every model seat using small local substitute models and each seat's own persona prompt.

Current local model behavior:

- Every model identity currently maps to the accessible local substitute `Qwen/Qwen3-0.6B`.
- The model identity/persona still differs per seat, but the underlying runtime model is the same small local substitute for now.
- If local inference fails, the seat falls back to its deterministic persona bot and the fallback reason is logged.
- The next runtime step is replacing substitutes with exact per-family small/GGUF models where feasible.

Play Mode behavior:

- `Quick Seat` starts a cash-game session.
- `Next Hand` continues with current stacks and rotates the button.
- AI seats auto-rebuy if busted so the tavern stays populated.
- If the human busts, the table pauses and `Rebuy 1000` becomes available.
- Illegal user actions are disabled; button labels show live call and raise amounts.
- During AI turns, the UI streams intermediate status updates such as `Qwen is thinking...`.

## Run Locally

```bash
uv sync
uv run python app.py
```

Open the printed local URL, usually `http://127.0.0.1:7860/`.

## Tests

```bash
uv run pytest
```

The root app tests are scoped to `tests/`. The `ml-intern/` checkout is a local reference/tooling repo and is intentionally excluded from root app tests.

## Diagnostics

Structured app logs are written as JSON Lines to:

```text
logs/token_holdem.jsonl
```

The Gradio app also has a `Diagnostics` tab with a `Refresh Recent Logs` button.

Useful event names include:

- `callback_start`
- `callback_failed`
- `session_started`
- `hand_started`
- `action_applied`
- `ai_decision`
- `model_runtime_success`
- `model_runtime_failed`
- `model_runtime_unsupported`
- `hand_completed`
- `leaderboard_record_hand`

The logs are ignored by git and rotate automatically.

## Persistence

The app uses local SQLite at `token_holdem.sqlite3`. This file is ignored by git and recreated automatically.

On Hugging Face Spaces, local SQLite persists while the Space runtime is alive, but may reset on rebuild/redeploy unless persistent storage is configured.

## Architecture

- `app.py`: Gradio app and UI event wiring.
- `token_holdem/engine.py`: deterministic poker state machine.
- `token_holdem/evaluator.py`: `treys` adapter.
- `token_holdem/agents.py`: roster and fallback personalities.
- `token_holdem/model_runtime.py`: optional local Transformers inference, JSON parsing, validation, and fallback.
- `token_holdem/leaderboard.py`: SQLite stats and Hall of Fame.
- `token_holdem/render.py`: HTML/CSS rendering helpers.

## Next Runtime Work

- Add GGUF/llama.cpp support for larger named model identities.
- Add configurable model IDs through environment variables or UI settings.
- Generate and commit pixel sprite assets.
- Add stronger pause/resume controls for Arena simulation.
- Implement full side-pot support.
