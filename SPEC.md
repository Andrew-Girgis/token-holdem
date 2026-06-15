# Token Hold'em Specification

## Summary

Token Hold'em is a Gradio application for the Hugging Face Build Small Hackathon, submitted to the Thousand Token Wood track. It is a spectacle-first AI poker tavern where small open-weight language models play Texas Hold'em, develop reputations, trash talk each other politely, and compete on a persistent leaderboard.

The poker engine owns all deterministic game rules. Language models only provide action intent, personality, and table talk. Invalid model output is silently repaired or replaced with a legal safe action so the fantasy stays intact.

## Product Pillars

- Spectacle first: the app should feel like a tiny pixel-art poker tavern, not a poker trainer.
- Deterministic rules: LLMs never determine legal actions, winners, pots, hand strength, or leaderboard math.
- Model rivalries: the six model competitors should feel distinct through model behavior, lightweight personas, recent-hand memory, titles, and table talk.
- Cozy public demo: banter should be playful, model-vs-model focused, and safe for a public Hugging Face Space.
- Local-first runtime: use local small models where feasible, one model turn at a time, unloading between turns to manage memory.

## Target Modes

### Play Mode: Human vs AI

The user quick-seats into a table with minimal setup. The user provides a display name so their statistics can be persisted alongside model statistics.

The user can:

- View their hole cards.
- View community cards.
- See stacks, pot, blinds, button, and current action.
- Use preset action buttons: fold, check, call, min raise, half-pot raise, pot raise, and all-in.
- Read AI table talk and hand results.
- Resume or start fresh when returning after a refresh if a previous session exists.

The human player may be commented on by AI agents in a cozy way. Agents should be aware when they are playing against a human and may comment on the user's visible public playstyle, such as frequent folds, big raises, or showdown tendencies. They must not receive hidden information.

### Spectator Mode: AI Arena

Six model players sit at the default Arena table. The Arena auto-plays with pause/stop controls. Latency should be turned into theatrical pacing with dramatic pauses, typing indicators, and tavern narration. Where practical, batch AI generation for multiple comments or turns to reduce visible waiting.

The user can:

- Start, pause, resume, and stop an Arena simulation.
- Watch current hand state, actions, chip movement, and table chat.
- See session rankings update after hands.
- View hand history and bankroll deltas.
- Read winner-brag Table Chronicles after major hands.

## Visual Direction

- Dark mode by default.
- Retro pixel-art tavern/casino atmosphere.
- Animated poker table using custom CSS and Gradio HTML blocks.
- Generated sprite images committed under `assets/` for player avatars, chips, cards, table props, and tavern accents.
- Responsive enough for normal browser widths; desktop is the primary experience, mobile should remain usable.
- Avoid generic Gradio demo layout. The UI should look like a game board with panels embedded into the tavern theme.

## Initial Roster

Each roster entry has a model identity, exact Hub model ID, lightweight persona, sprite, and mutable reputation. Exact IDs should be verified during implementation for license, tokenizer/runtime support, and memory footprint.

Proposed default model IDs:

- Nemotron Nano: `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF`
- Qwen: `lm-kit/qwen-3-0.6b-instruct-gguf` or an official `Qwen/Qwen3-0.6B` runtime-compatible variant if preferred after spike
- Gemma: `google/gemma-3-270m-it` or `unsloth/gemma-3-270m-it-GGUF`
- Cohere North Mini: `CohereLabs/North-Mini-Code-1.0` or `unsloth/North-Mini-Code-1.0-GGUF`
- Mistral: `TheBloke/Mistral-7B-Instruct-v0.2-GGUF` or a smaller compatible Mistral-family GGUF if found
- OpenAI Open Model 20B: `openai/gpt-oss-20b` or `unsloth/gpt-oss-20b-GGUF`

Runtime policy:

- Use sequential turns rather than concurrent inference.
- Load only the active model when possible.
- Unload model objects and clear memory after each turn.
- Use compact prompts and short `max_new_tokens` because the output schema is small.
- If a model cannot be loaded on the selected Space hardware, the agent should fall back to the deterministic persona bot for that seat while preserving the UI identity and logging the fallback internally.

## AI Agent Contract

Each AI receives strictly legal visible information plus meta context that it is playing in Token Hold'em and, in Play Mode, whether a human is seated.

State summary fields:

- Agent name and model identity.
- Lightweight persona prompt.
- Hole cards for that agent only.
- Community cards.
- Current stack.
- Pot size.
- Amount needed to call.
- Legal actions and legal raise presets.
- Betting history for the current hand.
- Public recent-hand memory, limited to the last 3-5 notable hands/actions.
- Public leaderboard-derived reputation title.
- Visible opponent behavior summaries, never hidden cards.

Required model output:

```json
{
  "action": "fold|check|call|raise|all_in",
  "amount": 0,
  "table_talk": "string"
}
```

Validation rules:

- Parse JSON from the model response, extracting the first JSON object if extra text appears.
- Normalize action names where obvious.
- Clamp table talk to a short safe length.
- Reject actions not in the engine-provided legal action set.
- Clamp raise amounts to legal preset amounts, or convert to the nearest legal preset.
- If repair fails, choose a legal safe action in this order: check, call, fold.
- Repairs are invisible to the user.

## Personality Layer

Four classic tavern archetypes should exist and can be assigned to model seats or used by fallback bots:

- Maverick: aggressive bluffer, splashy raises, cocky but playful banter.
- Professor Odds: probability-focused, cautious, talks in pot odds and tiny chalkboard metaphors.
- Gobbo: chaotic gremlin gambler, unpredictable bets, goblin tavern energy.
- Sheriff: tight conservative player, law-and-order poker voice, patient and suspicious.

The six named model agents should not be forced into identical templates. Each receives a lightweight persona prompt that leaves room for model-specific behavior. Example tendencies:

- Qwen: analytical and precise.
- Gemma: cautious and methodical.
- Mistral: sharp and aggressive.
- Cohere North Mini: creative and unpredictable.
- Nemotron: logical and controlled.
- OpenAI Open Model 20B: confident, strategic, occasionally theatrical.

## Poker Engine

Use deterministic Python logic for game flow and `treys` or a similar lightweight evaluator for hand ranking. The awesome-poker resource list was reviewed; for this app, the best boundary is to use a battle-tested evaluator while keeping game flow local and UI-friendly.

Responsibilities:

- Deck generation.
- Shuffling.
- Button and blinds.
- Hole-card dealing.
- Betting rounds: preflop, flop, turn, river.
- Legal action generation.
- Preset raise sizing.
- Pot and contribution tracking.
- Fold/check/call/raise/all-in validation.
- Showdown hand evaluation through `treys`.
- Winner determination.
- Chip settlement.
- Side pots if feasible in the implementation pass.

MVP correctness preference:

- Library-driven hand evaluation with our own engine state machine.
- Implement side pots if they fit cleanly; otherwise constrain all-in behavior or mark side pots as a known limitation before launch.
- All public UI values should be derived from engine state, never model text.

## Game State Model

Suggested modules:

- `app.py`: Gradio entrypoint.
- `token_holdem/engine.py`: poker state machine and legal transitions.
- `token_holdem/cards.py`: card/deck helpers and display formatting.
- `token_holdem/evaluator.py`: `treys` adapter.
- `token_holdem/agents.py`: model and fallback agent logic.
- `token_holdem/prompts.py`: compact prompt construction.
- `token_holdem/leaderboard.py`: SQLite persistence and stat updates.
- `token_holdem/reputation.py`: dynamic titles and Hall of Fame calculations.
- `token_holdem/ui.py`: Gradio layout/render helpers.
- `token_holdem/assets.py`: sprite and asset references.

Keep the runtime single-process. Prefer Gradio generator-style updates for Arena auto-play rather than background workers, queues, or separate services.

## Persistence

Use local SQLite by default. On Hugging Face Spaces, document that local SQLite persists during a running Space but may reset on rebuild/redeploy unless persistent storage is configured. This is acceptable for MVP.

Persist:

- Model stats.
- Named human stats.
- Hand summaries.
- Hall of Fame records.
- Recent public memory snippets.
- Active session marker sufficient to offer resume-or-new on return.

Leaderboard stat semantics:

- `bankroll`: current lifetime chip bankroll.
- `hands_played`: incremented for every dealt-in hand.
- `wins`: incremented when net chip delta for a hand is positive.
- `losses`: incremented when net chip delta for a hand is negative.
- `pushes`: incremented when net chip delta is zero.
- `biggest_pot_won`: largest pot won or shared by that player.
- `net_profit`: lifetime bankroll delta from starting baseline.
- `average_profit_per_hand`: `net_profit / hands_played`.

Suggested tables:

- `players(id, display_name, kind, model_id, persona, created_at)`.
- `stats(player_id, bankroll, hands_played, wins, losses, pushes, biggest_pot_won, net_profit, current_streak, longest_winning_streak, largest_comeback)`.
- `hands(id, mode, started_at, completed_at, seed, pot, board, winner_ids, summary, chronicle)`.
- `hand_player_results(hand_id, player_id, starting_stack, ending_stack, net_delta, hole_cards, final_hand_rank, folded)`.
- `hall_of_fame(key, player_id, hand_id, value, label, updated_at)`.
- `memories(player_id, text, created_at, hand_id)`.
- `sessions(id, mode, human_name, serialized_state, updated_at)`.

## Reputation System

Generate titles from evolving statistics. Titles update automatically after hands and are displayed on avatars, leaderboard rows, and Arena rankings.

Example rules:

- The River King: multiple wins after river showdowns or largest river pot win.
- Bluff Master: largest weak-hand win or repeated low-strength wins.
- Chip Destroyer: highest net profit or biggest pot won.
- Tightest Player: high fold rate and positive profit.
- Chaos Goblin: high variance, frequent all-ins, volatile stack movement.
- Silent Assassin: low chat frequency with high win rate.

Do not let title generation require model inference. Titles should be deterministic functions of stats, with optional flavor text from templates.

## Hall of Fame

Display a dedicated Hall of Fame section.

Track:

- Largest pot ever won.
- Longest winning streak.
- Largest comeback.
- Most successful bluff, defined as the largest pot won before showdown or with weak showdown hand strength.
- Most profitable model.

The weak-hand bluff metric should use evaluator-derived hand category and betting outcome, not claimed intent.

## Table Chronicle

The Table Chronicle is generated after major hands and tournament/session milestones. The winner should brag in-character.

Trigger examples:

- Pot exceeds a major threshold.
- All-in showdown.
- Bluff metric candidate.
- Leaderboard rank changes.
- Huge comeback or bust-out.

Generation policy:

- Prefer the winning agent's model/persona to produce a short dramatic recap.
- Keep chronicle length to 1-3 sentences.
- If model inference is unavailable or slow, use a deterministic winner-brag template.
- Never include hidden cards that were not revealed by showdown unless the hand is complete and the UI intentionally shows the result.

## UI Layout

Top-level app:

- Header: Token Hold'em title, track badge, tavern tagline.
- Tabs: Play Mode, AI Arena, Leaderboard, Hall of Fame, About.

Play Mode layout:

- Central poker table with community cards, pot, current street, and button marker.
- Human card tray with visible hole cards.
- Opponent seats with sprites, stacks, titles, last action, and chat bubbles.
- Action bar with legal preset buttons only.
- Hand result panel.
- Compact hand log.

Arena layout:

- Six-seat animated table.
- Auto-play controls: start, pause, resume, stop.
- Current action ticker.
- Tavern chat feed.
- Session ranking panel.
- Hand history panel.
- Chronicle panel.

Leaderboard layout:

- Sortable-looking table rendered through Gradio components or HTML.
- Columns: rank, avatar, name, model ID, title, bankroll, wins, losses, hands, biggest pot, net profit, average profit per hand.

Hall of Fame layout:

- Pixel trophy cards for each record.
- Include record holder, value, hand summary, and date/time.

## CSS And Asset Requirements

- Use custom CSS beyond standard Gradio styling.
- Include pixel fonts via safe CSS fallback, avoiding external network dependency if possible.
- Commit generated sprites under `assets/`.
- Use CSS animations for chip movement, card reveal, active player glow, table candle flicker, and typing indicators.
- Keep assets small to avoid Space bloat.

## Dependencies

Expected root dependencies:

- `gradio`
- `treys`
- `transformers`
- `accelerate`
- `torch`
- `huggingface_hub`
- Optional GGUF runtime after spike: `llama-cpp-python` if installable on the target Space hardware, otherwise use Transformers-compatible small models first.

Implementation should start with a dependency/runtime spike because GGUF support, model size, and Space hardware constraints are the highest risk areas.

## README Requirements

The README must explain:

- Concept and Thousand Token Wood track fit.
- Play Mode and AI Arena.
- Local model roster and exact model IDs used.
- Runtime limitations and fallback behavior.
- Deterministic poker engine boundary.
- SQLite persistence behavior on Hugging Face Spaces, including rebuild limitations.
- How to run locally with `uv`.
- How to deploy as a Gradio Space.
- Known limitations, especially if side pots or full six-model local runtime are constrained.

## Acceptance Criteria

- Gradio app launches locally from the repo root.
- Play Mode supports a named human player against AI agents.
- Spectator Mode auto-plays a six-model Arena with pause/resume/stop controls.
- Poker engine deterministically handles legal actions, betting rounds, showdown, and chip settlement.
- LLM/fallback agents return or are coerced into the required JSON contract.
- Leaderboard persists to SQLite and displays model plus named human stats.
- Reputation titles update from statistics.
- Hall of Fame records update after qualifying hands.
- Table Chronicle appears after major hands.
- Custom CSS and committed generated sprites create a retro pixel tavern feel.
- README documents architecture, models, persistence, and hackathon track.

## Major Risks

- Running six exact local model identities on standard Space hardware may be slow or memory-heavy even sequentially.
- GGUF runtime installation may be more fragile than Transformers on Spaces.
- Some requested exact models are large despite the small-model track; fallback bots must preserve demo usability.
- Side-pot correctness can consume disproportionate implementation time.
- Gradio long-running auto-play must remain responsive without background workers.

## Build Order

1. Dependency/runtime spike for `treys`, Gradio, and one small model backend.
2. Deterministic engine with tests for deck, betting, legal actions, showdown, and settlement.
3. SQLite leaderboard and Hall of Fame schema.
4. Fallback persona agents with JSON action contract.
5. Gradio Play Mode with preset buttons.
6. Arena auto-play with pause/resume/stop generator flow.
7. Local model adapter with sequential load/unload.
8. Sprites, custom CSS, and tavern polish.
9. Table Chronicle and reputation tuning.
10. README and Space deployment documentation.
