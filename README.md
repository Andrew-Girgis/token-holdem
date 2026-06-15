---
title: Token Hold'em
colorFrom: red
colorTo: amber
sdk: gradio
sdk_version: 6.18.0
app_file: app.py
pinned: false
tags:
  - gradio
  - modal
  - poker
  - game
  - agents
  - build-small-hackathon
---

# Token Hold'em

Token Hold'em is a Thousand Token Wood Gradio poker tavern for the Hugging Face Build Small Hackathon. One human can quick-seat into a Texas Hold'em cash game against seven LLM poker agents, or judges can run an AI Arena where the model seats play hands against each other.

The poker engine is deterministic: it owns dealing, blinds, legal actions, betting, showdown, side-pot settlement, chip movement, leaderboard records, and Hall of Fame stats. Models only choose among legal actions and generate short table talk.

## Run Locally

```bash
uv sync
uv run python app.py
```

Open the printed Gradio URL, usually `http://127.0.0.1:7860/`.

For production-style model play through Modal:

```bash
USE_MODAL_INFERENCE=true uv run python app.py
```

For local development only, deterministic bots can be enabled explicitly:

```bash
TOKEN_HOLDEM_ALLOW_DETERMINISTIC_BOTS=1 uv run python app.py
```

That fallback mode is intentionally labeled as development/test behavior. Normal model-enabled play does not silently replace unavailable LLMs with bots.

## Modal Runtime

Modal is the runtime boundary for LLM poker decisions. The local Gradio process sends a serializable game-state summary, the acting model name, model id, persona, legal actions, and the decision prompt to `modal_inference.py::run_agent_decision`.

Modal returns:

- `action`
- `bet_amount`
- `explanation`
- `commentary`
- `raw_model_output`
- `error`

If Modal lookup, timeout, model loading, generation, or response validation fails, the app logs the failure and surfaces a clear model-unavailable message. It does not apply a fake fallback action.

Deploy Modal:

```bash
uv run modal deploy modal_inference.py
```

Smoke-test one seat:

```bash
uv run modal run modal_inference.py::smoke --model-name Gemma
```

## Environment

- `USE_MODAL_INFERENCE=true`: use Modal for model decisions.
- `TOKEN_HOLDEM_MODAL_APP_NAME`: Modal app name. Default: `token-holdem-inference`.
- `TOKEN_HOLDEM_MODAL_MODEL_NAMES`: comma-separated player/model names, or `all`. Default: `all`.
- `TOKEN_HOLDEM_MODAL_HF_SECRET_NAME`: Modal secret exposing `HF_TOKEN`. Default: `token-holdem-hf-token`.
- `TOKEN_HOLDEM_MODAL_TIMEOUT_SECONDS`: local wait timeout for a Modal call. Default: `300`.
- `TOKEN_HOLDEM_MODAL_GPU`: Modal GPU type. Default: `L40S`.
- `TOKEN_HOLDEM_GGUF_CONTEXT`: llama.cpp context for GGUF Modal seats. Default: `4096`.
- `TOKEN_HOLDEM_GGUF_GPU_LAYERS`: llama.cpp GPU layer count. Default: `-1`.
- `TOKEN_HOLDEM_ALLOW_MODEL_DOWNLOADS=1`: allow local Transformers downloads for local-runtime experiments.
- `TOKEN_HOLDEM_ALLOW_DETERMINISTIC_BOTS=1`: explicit development/test fallback mode.

Create the Modal HF secret:

```bash
uv run modal secret create token-holdem-hf-token --from-dotenv .env --force
```

## Model Roster

All configured models are under the 32B hackathon cap. Live Hub metadata was checked during finalization on 2026-06-15.

| Seat | Model | Parameters / format | Runtime status |
| --- | --- | --- | --- |
| Nemotron Nano | `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` | 3.97B GGUF | Active through Modal llama.cpp |
| Qwen | `lm-kit/qwen-3-0.6b-instruct-gguf` | 0.75B GGUF | Active through Modal llama.cpp |
| Gemma | `google/gemma-4-12B-it` | 11.96B safetensors | Active through Modal Transformers |
| Cohere North Mini | `CohereLabs/North-Mini-Code-1.0` | 30.48B safetensors | Active through Modal Transformers |
| Mistral | `TheBloke/Mistral-7B-Instruct-v0.2-GGUF` | 7.24B GGUF | Active through Modal llama.cpp |
| OpenAI Open Model 20B | `openai/gpt-oss-20b` | 21.51B mixed precision | Active through Modal Transformers |
| Llama Scout | `meta-llama/Llama-3.2-1B-Instruct` | 1.24B safetensors | Active through Modal if the HF token has gated access |

The Diagnostics tab shows recent runtime evidence for each seat: model called, Modal/local source, action returned, and any unavailable/disabled reason.

## Game Modes

Human Quick Play:

- Click `Quick Seat`.
- The human occupies the bottom-center seat.
- AI seats act until it is the human turn.
- Legal action buttons update with live call, min-raise, half-pot, pot, and all-in amounts.
- `Next Hand` continues the cash-game session with current stacks and rotating button.
- `Rebuy 1000` appears if the human busts.

AI Arena:

- Open `AI Arena`.
- Choose a seed and number of hands.
- Click `Start Arena`.
- Model seats play without human input.
- Cards are revealed for spectators, and logs/leaderboards update after each hand.

## Tests

```bash
uv run pytest
```

Root tests cover poker flow, app sessions, leaderboard persistence, logging, model-runtime parsing/status behavior, and stable eight-seat rendering. The `ml-intern/` checkout is reference/tooling only and is intentionally excluded from root app checks.

## Submission Tracks And Prize Notes

- Thousand Token Wood: primary track. Token Hold'em is an interactive AI-native poker game with a custom tavern UI and autonomous small-model personalities.
- OpenAI Best Use of Codex: eligible once the connected GitHub repo or Space contains Codex-attributed commits. Placeholder: add PR/commit link here.
- NVIDIA Nemotron Hardware Prize: eligible because the roster uses `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` as an active Modal GGUF seat. Note for judges: Nemotron Nano is one of the table agents.
- Modal Best Use of Modal: eligible because model decisions run through Modal at app runtime, including GGUF seats via llama.cpp and Transformers seats via Hub-loaded models.
- Off Brand bonus badge: eligible because the app uses a custom full-page tavern/poker-table UI instead of stock Gradio layout.
- Tiny Titan bonus badge: candidate claim through the Qwen 0.6B, Llama 1B, and Nemotron Nano 4B-or-smaller seats. The full roster also includes larger under-32B models, so the demo should emphasize tiny-seat impact.
- Best Demo bonus badge: placeholder for demo video URL and social post URL.
- Best Agent bonus badge: candidate claim through autonomous poker agents that read state, choose legal actions, and produce persona-grounded commentary.
- Bonus Quest Champion: candidate if the final Space README includes the Modal, Nemotron, custom UI, tiny-model, demo, and agent notes above.
- Judges' Wildcard: all submissions are considered.

## Judge Demo Checklist

1. Confirm the Space README includes the demo video and social post links.
2. Start in `Play Mode`, click `Quick Seat`, and play at least one human action.
3. Open `Diagnostics`, click `Refresh Recent Logs`, and verify Modal model-call rows.
4. Run `AI Arena` for one hand.
5. Open `Leaderboard` and `Hall of Fame` to see recorded outcomes.

Demo video placeholder: `TODO: add demo video URL`

Social post placeholder: `TODO: add social post URL`

## Known Limitations

- Llama Scout requires the Modal HF secret token to have access to the gated Meta repo.
- First Modal calls may cold-start and download model weights into the Modal Volume.
- Large models can exceed the default timeout or GPU memory depending on Modal hardware; failures are visible in Diagnostics instead of hidden behind fallback actions.
- Local non-Modal play requires cached local model weights, local downloads, or the explicit development bot flag.

## Architecture

- `app.py`: Gradio app, callbacks, diagnostics, and mode wiring.
- `modal_inference.py`: Modal GPU/llama.cpp/Transformers inference function.
- `token_holdem/engine.py`: deterministic poker state machine.
- `token_holdem/agents.py`: roster and explicit development fallback personalities.
- `token_holdem/model_runtime.py`: runtime selection, Modal adapter, validation, status reporting, and no-silent-fallback policy.
- `token_holdem/render.py`: HTML/CSS poker table rendering.
- `token_holdem/leaderboard.py`: SQLite stats and Hall of Fame.
- `assets/token-holdem/manifest.json`: local asset manifest.
