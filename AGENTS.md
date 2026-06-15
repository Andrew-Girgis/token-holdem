# Agent Notes

## Repo Shape

- Build the new app from the repo root unless the user explicitly asks to work on `ml-intern/`.
- `ml-intern/` is a local tool/reference checkout, not the target app. Use it for agent tooling, examples, and docs, but do not treat its FastAPI/React app as this repo's product.
- `ml-intern/AGENTS.md` applies only when editing `ml-intern/` itself.
- Repo-local skills live in `.agents/skills/`. Hugging Face and Gradio source docs for app-building agents live in `ml-intern/docs/agent-context/`.

## Setup And Checks

- Root package is currently minimal: Python `>=3.13`, no dependencies, and `main.py` is the only root code entrypoint.
- If using `ml-intern/` as a tool, set it up separately with `cd ml-intern && uv sync --locked --extra dev`.
- Checks for `ml-intern/` are not checks for the root app; only run them when changing `ml-intern/` files.
- For `ml-intern/` changes, CI runs Python 3.12 with `uv sync --locked --extra dev`, then `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`.

## Local App

- No root Gradio app exists yet. If creating one, add explicit run/check commands here after choosing the app entrypoint.
- Use the docs in `ml-intern/docs/agent-context/` before re-fetching Gradio/Hugging Face/llama.cpp pages.

## Runtime Notes

- The `hf` CLI is available; prefer it for Hugging Face Hub operations.
- Repo-local Hugging Face skills are installed under `.agents/skills/`; restart/reload the agent session if newly added skills are not visible.
- `ml-intern` local model support uses OpenAI-compatible endpoints through LiteLLM with prefixes such as `ollama/`, `vllm/`, `lm_studio/`, and `llamacpp/`.

## Deployment Gotchas

- Do not use the `ml-intern/` HF Space deploy flow for the root app unless the user explicitly asks to deploy `ml-intern`.
- If this root app becomes a Hugging Face Space, document its own Space SDK, app file, secrets, variables, and deploy command here.
