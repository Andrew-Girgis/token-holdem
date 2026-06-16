---
title: Token Hold'em
emoji: 🃏
colorFrom: red
colorTo: purple
sdk: docker
app_port: 7860
short_description: Modal-powered LLM poker arena
startup_duration_timeout: 30m
pinned: false
tags:
  - gradio
  - docker
  - modal
  - openai
  - nvidia
  - nemotron
  - poker
  - game
  - agents
  - build-small-hackathon
  - thousand-token-wood
  - track:wood
  - sponsor:openai
  - sponsor:nvidia
  - sponsor:modal
  - openai-codex
  - best-use-of-codex
  - best-use-of-modal
  - off-brand
  - achievement:offbrand
  - tiny-titan
  - achievement:tiny-titan
  - badge-tiny-titan
  - best-demo
  - achievement:best-demo
  - achievement:sharing
  - best-agent
  - agentic
  - bonus-quest-champion
  - judges-wildcard
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

Modal is the runtime boundary for LLM poker decisions. The local Gradio process sends a serializable game-state summary, the acting model name, model id, persona, legal actions, and the decision prompt to a warm Modal worker class in `modal_inference.py`.

The deployed app defines one parameterized worker per runtime family:

- `GgufModelWorker` for GGUF/llama.cpp seats.
- `MultimodalModelWorker` for Gemma.
- `CausalModelWorker` for standard causal-LM Transformers seats.

Each worker is parameterized by `model_id` and loads that one assigned model during `@modal.enter`, so a warm container handles later turns for the same model without packing every roster model into one GPU container.

The Modal Hugging Face cache Volume is mounted at `/cache/huggingface`, and `HF_HOME`, `TRANSFORMERS_CACHE`, `HF_HUB_CACHE`, and `HUGGINGFACE_HUB_CACHE` point at that mount. A separate setup step pre-downloads enabled model snapshots into the Volume in parallel, then the demo warmup step loads each enabled worker in parallel so model/tokenizer objects stay hot inside warm containers until scale-down.

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

Pre-download enabled model snapshots into the Modal Volume in parallel:

```bash
uv run modal run modal_inference.py::setup_cache
```

Warm all enabled workers in parallel before a demo:

```bash
uv run modal run modal_inference.py::warmup_demo
```

Smoke-test one seat:

```bash
uv run modal run modal_inference.py::smoke --model-name Gemma
```

Print smoke commands for every enabled Modal seat:

```bash
uv run python scripts/modal_smoke_enabled_models.py
```

Run those smoke checks:

```bash
uv run python scripts/modal_smoke_enabled_models.py --run
```

## Environment

- `USE_MODAL_INFERENCE=true`: use Modal for model decisions.
- `TOKEN_HOLDEM_MODAL_APP_NAME`: Modal app name. Default: `token-holdem-inference`.
- `TOKEN_HOLDEM_MODAL_MODEL_NAMES`: comma-separated player/model names, `default`, or explicit `all`. Default enables the full runtime-feasible roster, including Cohere Command R7B.
- `TOKEN_HOLDEM_MODAL_HF_SECRET_NAME`: Modal secret exposing `HF_TOKEN`. Default: `token-holdem-hf-token`.
- `TOKEN_HOLDEM_MODAL_TIMEOUT_SECONDS`: local wait timeout and Modal worker timeout. Default: `300`.
- `TOKEN_HOLDEM_MODAL_DEMO_MODE`: use longer warm-worker defaults for demos. Default: `true`.
- `TOKEN_HOLDEM_MODAL_SCALEDOWN_SECONDS`: idle seconds to keep warm Modal workers before scale-down. Default: `1800` in demo mode, `600` otherwise.
- `TOKEN_HOLDEM_MODAL_MIN_CONTAINERS`: optional always-warm worker count. Default: `0`; leave unset for cost-conscious demos.
- `TOKEN_HOLDEM_MODAL_GPU`: Modal GPU type. Default: `L40S`.
- `TOKEN_HOLDEM_MODAL_HEAVY_GPU`: GPU type for the heavy causal worker used by OpenAI Open Model 20B. Default: `A100-80GB`.
- `TOKEN_HOLDEM_MODEL_CACHE_DIR`: Modal-mounted Hugging Face cache root. Default: `/cache/huggingface`.
- `TOKEN_HOLDEM_GGUF_CONTEXT`: llama.cpp context for GGUF Modal seats. Default: `4096`.
- `TOKEN_HOLDEM_GGUF_GPU_LAYERS`: llama.cpp GPU layer count. Default: `-1`.
- `TOKEN_HOLDEM_GGUF_DECISION_TOKENS`: max tokens for GGUF decision JSON. Default: `96`.
- `TOKEN_HOLDEM_GGUF_TALK_TOKENS`: max tokens for GGUF table talk. Default: `24`.
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
| Qwen | `Qwen/Qwen3-0.6B` | 0.75B safetensors | Active through Modal Transformers |
| Gemma | `google/gemma-4-12B-it` | 11.96B safetensors | Active through Modal Transformers |
| Cohere Command R7B | `CohereLabs/c4ai-command-r7b-12-2024` | 8.03B BF16 safetensors | Active through Modal Transformers if the HF token has access |
| Mistral | `mistralai/Mistral-7B-Instruct-v0.2` | 7.24B safetensors | Active through Modal Transformers |
| OpenAI Open Model 20B | `openai/gpt-oss-20b` | 21.51B mixed precision | Active through Modal Transformers |
| Llama Scout | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | 1.1B safetensors | Active through Modal Transformers |

The default enabled Modal seats are Nemotron Nano, Qwen, Gemma, Cohere Command R7B, Mistral, OpenAI Open Model 20B, and Llama Scout. Qwen and Mistral use public safetensors checkpoints through GPU Transformers workers because their earlier GGUF routes were slower during Modal validation. Llama Scout uses TinyLlama because the previously tested Meta Llama 3.2 checkpoint is gated and failed Modal cache setup without token access. North Mini was first switched from the 30B safetensors model to Unsloth `North-Mini-Code-1.0-UD-Q4_K_M.gguf` through the same GGUF/llama.cpp runtime as the other GGUF seats, but a live Modal smoke test failed during `llama_cpp.Llama(...)` model load. North Mini FP8 loaded but failed on FP8 matmul support in the current Torch path. The active Cohere seat now uses the official Command R7B Transformers checkpoint. Disabled model seats fail visibly with a model-unavailable message; they are not replaced by bots.

The Diagnostics tab shows recent runtime evidence for each seat: model called, Modal/local source, action returned, and any unavailable/disabled reason.
Modal models generate the poker action JSON. Public table talk is rendered from deterministic tavern templates after a valid action so prompt leakage cannot reach the table and each AI turn needs one model generation instead of two.

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
- OpenAI Best Use of Codex: eligible once the connected GitHub repo or Space contains Codex-attributed commits. Codex-attributed commit: https://github.com/Andrew-Girgis/token-holdem/commit/97b78fd9317a3c8cd50cf9a0a6942b964bcef363
- NVIDIA Nemotron Hardware Prize: eligible because the roster uses `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` as an active Modal GGUF seat. Note for judges: Nemotron Nano is one of the table agents.
- Modal Best Use of Modal: eligible because model decisions run through Modal at app runtime, including GGUF seats via llama.cpp and Transformers seats via Hub-loaded models.
- Off Brand bonus badge: eligible because the app uses a custom full-page tavern/poker-table UI instead of stock Gradio layout.
- Tiny Titan bonus badge: candidate claim through the Qwen 0.6B, Llama 1B, and Nemotron Nano 4B-or-smaller seats. The full roster also includes larger under-32B models, so the demo should emphasize tiny-seat impact.
- Best Demo bonus badge: demo video URL and social post URL are listed below for judges.
- Best Agent bonus badge: candidate claim through autonomous poker agents that read state, choose legal actions, and produce persona-grounded commentary.
- Bonus Quest Champion: candidate if the final Space README includes the Modal, Nemotron, custom UI, tiny-model, demo, and agent notes above.
- Judges' Wildcard: all submissions are considered.

## Judge Demo Checklist

1. Confirm the Space README includes the demo video and social post links.
2. Start in `Play Mode`, click `Quick Seat`, and play at least one human action.
3. Open `Diagnostics`, click `Refresh Recent Logs`, and verify Modal model-call rows.
4. Run `AI Arena` for one hand.
5. Open `Leaderboard` and `Hall of Fame` to see recorded outcomes.

Demo video: https://youtu.be/hXPOF0UwQYA

Social post: https://x.com/AndrewGirgis/status/2066668850662273466?s=20

## Known Limitations

- First Modal calls may cold-start if `setup_cache` and `warmup_demo` have not been run recently. The setup command downloads model snapshots into the Modal Volume; warm worker containers keep one loaded model per `model_id` until scale-down.
- Cohere North Mini Q4_K_M GGUF failed to load under the current `llama-cpp-python` runtime. North Mini FP8 loaded but failed on FP8 matmul support in the current Torch path. The game keeps a Cohere seat through the official Command R7B Transformers checkpoint, which requires the Modal HF secret to have accepted gated access.
- Large models can exceed the default timeout or GPU memory depending on Modal hardware; failures are visible in Diagnostics instead of hidden behind fallback actions.
- Local non-Modal play requires cached local model weights, local downloads, or the explicit development bot flag.

## Architecture

- `app.py`: Gradio app, callbacks, diagnostics, and mode wiring.
- `modal_inference.py`: Modal GPU/llama.cpp/Transformers warm worker classes and compatibility smoke function.
- `token_holdem/engine.py`: deterministic poker state machine.
- `token_holdem/agents.py`: roster and explicit development fallback personalities.
- `token_holdem/model_runtime.py`: runtime selection, Modal adapter, validation, status reporting, and no-silent-fallback policy.
- `token_holdem/render.py`: HTML/CSS poker table rendering.
- `token_holdem/leaderboard.py`: SQLite stats and Hall of Fame.
- `assets/token-holdem/manifest.json`: local asset manifest.
