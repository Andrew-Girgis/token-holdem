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

Pre-download the enabled model snapshots into the Modal Volume. This fans out one Modal setup call per enabled model:

```bash
uv run modal run modal_inference.py::setup_cache
```

Warm the deployed demo workers before recording or judging. This starts each enabled model worker in parallel:

```bash
uv run modal run modal_inference.py::warmup_demo
```

Run a smoke test without the Gradio UI:

```bash
uv run modal run modal_inference.py::smoke --model-name Gemma
```

Print one smoke command per enabled model:

```bash
uv run python scripts/modal_smoke_enabled_models.py
```

Run those smoke checks:

```bash
uv run python scripts/modal_smoke_enabled_models.py --run
```

## Run Gradio With Modal

```bash
USE_MODAL_INFERENCE=true uv run python app.py
```

The default `TOKEN_HOLDEM_MODAL_MODEL_NAMES` behavior enables the runtime-feasible roster, including Cohere Command R7B through Transformers.

## Runtime Coverage

- GGUF seats (`Nemotron Nano`) route to `GgufModelWorker`, a parameterized Modal class that loads one GGUF with `llama.cpp` during `@modal.enter`.
- Gemma routes to `MultimodalModelWorker`, a parameterized Modal class that loads one multimodal Transformers model during `@modal.enter`.
- Standard Transformers seats (`Qwen`, `Cohere Command R7B`, `Mistral`, `Llama Scout`) route to `CausalModelWorker`, a parameterized Modal class that loads one causal-LM model during `@modal.enter`.
- The Modal Volume `token-holdem-hf-cache` is mounted at `/cache/huggingface`. `HF_HOME`, `TRANSFORMERS_CACHE`, `HF_HUB_CACHE`, and `HUGGINGFACE_HUB_CACHE` point at that mount, so Hugging Face downloads survive container scale-down.
- `setup_cache` uses one parallel `snapshot_download` call per enabled model to populate the mounted Volume before the demo. GGUF repos are restricted to the configured quantized file instead of pulling every quantization.
- `warmup_demo` calls each parameterized worker's `warmup` method in parallel, which runs the same `@modal.enter` model load path used by live decisions. Warm containers keep the loaded model/tokenizer or model/processor objects in process memory until Modal scales them down.
- `OpenAI Open Model 20B` routes to `HeavyCausalModelWorker`, which defaults to a larger `A100-80GB` GPU and pins `kernels==0.12.0` for MXFP4 quantized loading. Newer `kernels` releases changed `LayerRepository` construction and broke Transformers imports during warmup.
- `Qwen` and `Mistral` use public safetensors checkpoints through the Transformers path; their earlier GGUF routes were slower in live Modal validation.
- Modal workers generate and parse the poker action JSON only. Public table talk uses deterministic tavern templates after a valid action to avoid prompt leakage and remove a second model generation from each turn.
- `Llama Scout` uses `TinyLlama/TinyLlama-1.1B-Chat-v1.0`; the previously tested Meta Llama 3.2 checkpoint is gated and failed Modal cache setup without token access.
- North Mini was tested as `unsloth/North-Mini-Code-1.0-GGUF` with `North-Mini-Code-1.0-UD-Q4_K_M.gguf`, but a live Modal smoke test failed during `llama_cpp.Llama(...)` model load under the current runtime. North Mini FP8 loaded but failed on FP8 matmul support in the current Torch path. The active Cohere seat uses `CohereLabs/c4ai-command-r7b-12-2024` through Transformers.

## Environment Variables

- `USE_MODAL_INFERENCE`: set to `true`, `1`, `yes`, or `on` to use `ModalRuntime`.
- `TOKEN_HOLDEM_MODAL_APP_NAME`: deployed Modal app name. Default: `token-holdem-inference`.
- `TOKEN_HOLDEM_MODAL_MODEL_NAMES`: comma-separated model/player names, `default`, or explicit `all`. Default enables all runtime-feasible seats.
- `TOKEN_HOLDEM_MODAL_HF_SECRET_NAME`: Modal secret name that exposes `HF_TOKEN`. Default: `token-holdem-hf-token`.
- `TOKEN_HOLDEM_MODAL_TIMEOUT_SECONDS`: local wait timeout and Modal worker timeout. Default: `300`.
- `TOKEN_HOLDEM_MODAL_DEMO_MODE`: keep demo defaults warm for longer. Default: `true`.
- `TOKEN_HOLDEM_MODAL_SCALEDOWN_SECONDS`: idle seconds to keep warm Modal workers alive. Default: `1800` in demo mode, `600` otherwise.
- `TOKEN_HOLDEM_MODAL_MIN_CONTAINERS`: optional always-warm worker count. Default: `0`; leave unset for cost-conscious demos.
- `TOKEN_HOLDEM_MODAL_GPU`: Modal GPU type for remote workers. Default: `L40S`; set empty to request no GPU.
- `TOKEN_HOLDEM_MODAL_HEAVY_GPU`: Modal GPU type for `HeavyCausalModelWorker`, currently the OpenAI 20B seat. Default: `A100-80GB`.
- `TOKEN_HOLDEM_MODEL_CACHE_DIR`: mounted Hugging Face cache root. Default: `/cache/huggingface`.
- `TOKEN_HOLDEM_GGUF_CONTEXT`: llama.cpp context length for Modal GGUF seats. Default: `4096`.
- `TOKEN_HOLDEM_GGUF_GPU_LAYERS`: llama.cpp GPU layer count. Default: `-1`.
- `TOKEN_HOLDEM_GGUF_DECISION_TOKENS`: max tokens for GGUF decision JSON. Default: `96`.
- `TOKEN_HOLDEM_GGUF_TALK_TOKENS`: max tokens for GGUF table talk. Default: `24`.
- `TOKEN_HOLDEM_ALLOW_MODEL_DOWNLOADS`: local-only flag for `LocalRuntime`.
- `TOKEN_HOLDEM_ALLOW_DETERMINISTIC_BOTS`: explicit development/test fallback mode.

## Runtime Boundary

The boundary is `InferenceRuntime.decide(profile, state_summary)`.

The local Gradio process owns game creation, legal actions, betting repair, pot movement, showdown, leaderboard updates, event callbacks, and rendering.

Modal receives current game state, model/player name, persona, model id, legal action metadata, and the decision prompt.

Modal returns action, bet amount, explanation, commentary, raw model output, and an error field. The local adapter validates the response before the poker engine applies anything.

Disabled models and Modal failures are surfaced as model-unavailable errors in the UI and structured logs. The app does not apply deterministic bot actions for model seats unless `TOKEN_HOLDEM_ALLOW_DETERMINISTIC_BOTS=1` is explicitly used outside Modal mode.

Modal container logs include structured JSON timing rows for container start, snapshot download/cache-hit state, tokenizer or processor load, model load to GPU, first token time, total generation time, and cache commits. Worker `@modal.enter` model-loading errors are not converted into successful decisions; they fail the worker load and surface through Modal/local diagnostics.
