# Modal Inference Backend

Token Hold'em keeps Gradio and deterministic poker logic in the local or Hugging Face Space process. Modal owns model decisions when `USE_MODAL_INFERENCE=true`.

Unlike the early prototype, model-enabled play no longer silently falls back to deterministic persona bots. If Modal is unavailable, the model returns invalid JSON, a model is disabled, or a gated model cannot be accessed, the app logs the failure and surfaces a clear unavailable message without applying a fake action.

## Setup

Install project dependencies:

```bash
uv sync
```

Authenticate Modal:

```bash
modal setup
```

Create the Modal Hugging Face secret from the repo `.env` file:

```bash
uv run modal secret create token-holdem-hf-token --from-dotenv .env --force
```

## Deploy Modal

```bash
uv run modal deploy modal_inference.py
```

Run a smoke test without the Gradio UI:

```bash
uv run modal run modal_inference.py::smoke --model-name Gemma
```

## Run Gradio With Modal

```bash
USE_MODAL_INFERENCE=true uv run python app.py
```

`TOKEN_HOLDEM_MODAL_MODEL_NAMES=all` is the default. Use a comma-separated subset only when you intentionally want the other seats to show as disabled/unavailable.

## Runtime Coverage

- GGUF seats (`Nemotron Nano`, `Qwen`, `Mistral`) are sent to Modal and loaded with `llama.cpp`.
- Transformers seats (`Gemma`, `Cohere North Mini`, `OpenAI Open Model 20B`, `Llama Scout`) are sent to Modal and loaded with Transformers.
- `Llama Scout` uses a gated Hub repo, so the Modal `HF_TOKEN` secret must have access.

## Environment Variables

- `USE_MODAL_INFERENCE`: set to `true`, `1`, `yes`, or `on` to use `ModalRuntime`.
- `TOKEN_HOLDEM_MODAL_APP_NAME`: deployed Modal app name. Default: `token-holdem-inference`.
- `TOKEN_HOLDEM_MODAL_MODEL_NAMES`: comma-separated model/player names or `all`. Default: `all`.
- `TOKEN_HOLDEM_MODAL_HF_SECRET_NAME`: Modal secret name that exposes `HF_TOKEN`. Default: `token-holdem-hf-token`.
- `TOKEN_HOLDEM_MODAL_TIMEOUT_SECONDS`: local wait timeout for a Modal call. Default: `300`.
- `TOKEN_HOLDEM_MODAL_GPU`: Modal GPU type for the remote function. Default: `L40S`; set empty to request no GPU.
- `TOKEN_HOLDEM_GGUF_CONTEXT`: llama.cpp context length for Modal GGUF seats. Default: `4096`.
- `TOKEN_HOLDEM_GGUF_GPU_LAYERS`: llama.cpp GPU layer count. Default: `-1`.
- `TOKEN_HOLDEM_ALLOW_MODEL_DOWNLOADS`: local-only flag for `LocalRuntime`.
- `TOKEN_HOLDEM_ALLOW_DETERMINISTIC_BOTS`: explicit development/test fallback mode.

## Runtime Boundary

The boundary is `InferenceRuntime.decide(profile, state_summary)`.

The local Gradio process owns game creation, legal actions, betting repair, pot movement, showdown, leaderboard updates, event callbacks, and rendering.

Modal receives current game state, model/player name, persona, model id, legal action metadata, and the decision prompt.

Modal returns action, bet amount, explanation, commentary, raw model output, and an error field. The local adapter validates the response before the poker engine applies anything.
