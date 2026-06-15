# Agent Notes

## Repo Shape

- Build the new app from the repo root unless the user explicitly asks to work on `ml-intern/`.
- `ml-intern/` is a local tool/reference checkout, not the target app. Use it for agent tooling, examples, and docs, but do not treat its FastAPI/React app as this repo's product.
- `ml-intern/AGENTS.md` applies only when editing `ml-intern/` itself.
- Repo-local skills live in `.agents/skills/`. Hugging Face and Gradio source docs for app-building agents live in `ml-intern/docs/agent-context/`.

## Setup And Checks

- Root app is Token Hold'em, a Gradio Texas Hold'em poker tavern implemented from the repo root.
- Root package requires Python `>=3.13` and uses `gradio`, `accelerate`, `torch`, `transformers`, `treys`, and `pytest` from `pyproject.toml`.
- The app entrypoint is `app.py`; `token_holdem/render.py` owns HTML/CSS table rendering and `token_holdem/engine.py` owns deterministic game rules.
- If using `ml-intern/` as a tool, set it up separately with `cd ml-intern && uv sync --locked --extra dev`.
- Root checks are `uv sync` and `uv run pytest`.
- Checks for `ml-intern/` are not checks for the root app; only run them when changing `ml-intern/` files.
- For `ml-intern/` changes, CI runs Python 3.12 with `uv sync --locked --extra dev`, then `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`.

## Local App

- Run the root Gradio app with `uv run python app.py`.
- Open the printed Gradio URL, usually `http://127.0.0.1:7860/`.
- Run root tests with `uv run pytest`.
- Use the docs in `ml-intern/docs/agent-context/` before re-fetching Gradio/Hugging Face/llama.cpp pages.
- The current table layout renders exactly 8 stable seats: seat 0 is the human bottom-center, seats 1-7 are LLM seats around the table, community cards live in the fixed center zone, and action buttons remain outside the table art in Gradio controls.

## Runtime Notes

- The `hf` CLI is available; prefer it for Hugging Face Hub operations.
- Repo-local Hugging Face skills are installed under `.agents/skills/`; restart/reload the agent session if newly added skills are not visible.
- `ml-intern` local model support uses OpenAI-compatible endpoints through LiteLLM with prefixes such as `ollama/`, `vllm/`, `lm_studio/`, and `llamacpp/`.

## Reference Docs

- `docs/modal-llms.md` is the local Modal reference for Modal inference work. Consult it for `modal.App`, `modal.Image`, uv project setup, GPU configuration, Volumes/model weights, Secrets/env vars, deployed Function invocation, timeouts/retries, and debugging Modal apps.
- Treat `docs/modal-llms.md` as reference material only, not as app requirements.

## Deployment Gotchas

- Do not use the `ml-intern/` HF Space deploy flow for the root app unless the user explicitly asks to deploy `ml-intern`.
- If this root app becomes a Hugging Face Space, document its own Space SDK, app file, secrets, variables, and deploy command here.
