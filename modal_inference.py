import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from typing import Any

import modal


MODEL_CACHE_DIR = os.getenv("TOKEN_HOLDEM_MODEL_CACHE_DIR", "/cache/huggingface")
HF_CACHE_ENV = {
    "HF_HOME": MODEL_CACHE_DIR,
    "TRANSFORMERS_CACHE": MODEL_CACHE_DIR,
    "HF_HUB_CACHE": MODEL_CACHE_DIR,
    "HUGGINGFACE_HUB_CACHE": MODEL_CACHE_DIR,
}
for name, value in HF_CACHE_ENV.items():
    os.environ.setdefault(name, value)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _modal_log(message: str, **fields: Any) -> None:
    payload = {
        "message": message,
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=True, default=str), flush=True)


APP_NAME = os.getenv("TOKEN_HOLDEM_MODAL_APP_NAME", "token-holdem-inference")
DEFAULT_GPU = os.getenv("TOKEN_HOLDEM_MODAL_GPU", "L40S") or None
HEAVY_GPU = os.getenv("TOKEN_HOLDEM_MODAL_HEAVY_GPU", "A100-80GB") or DEFAULT_GPU
HF_SECRET_NAME = os.getenv("TOKEN_HOLDEM_MODAL_HF_SECRET_NAME", "token-holdem-hf-token")
MODAL_TIMEOUT_SECONDS = int(os.getenv("TOKEN_HOLDEM_MODAL_TIMEOUT_SECONDS", "300"))
DEMO_MODE = _env_flag("TOKEN_HOLDEM_MODAL_DEMO_MODE", True)
DEFAULT_SCALEDOWN_WINDOW_SECONDS = 1800 if DEMO_MODE else 600
SCALEDOWN_WINDOW_SECONDS = int(os.getenv("TOKEN_HOLDEM_MODAL_SCALEDOWN_SECONDS", str(DEFAULT_SCALEDOWN_WINDOW_SECONDS)))
MIN_CONTAINERS = int(os.getenv("TOKEN_HOLDEM_MODAL_MIN_CONTAINERS", "0")) or None
GGUF_DECISION_MAX_TOKENS = int(os.getenv("TOKEN_HOLDEM_GGUF_DECISION_TOKENS", "96"))
GGUF_TALK_MAX_TOKENS = int(os.getenv("TOKEN_HOLDEM_GGUF_TALK_TOKENS", "24"))
hf_cache = modal.Volume.from_name("token-holdem-hf-cache", create_if_missing=True)

GGUF_MODEL_FILES = {
    "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF": "NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf",
    "lm-kit/qwen-3-0.6b-instruct-gguf": "Qwen3-0.6B-Q4_K_M.gguf",
    "unsloth/North-Mini-Code-1.0-GGUF": "North-Mini-Code-1.0-UD-Q4_K_M.gguf",
    "bartowski/c4ai-command-r7b-12-2024-GGUF": "c4ai-command-r7b-12-2024-Q4_K_M.gguf",
    "TheBloke/Mistral-7B-Instruct-v0.2-GGUF": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
}
MULTIMODAL_PROCESSOR_MODELS = {"google/gemma-4-12B-it"}

image = (
    modal.Image.debian_slim(python_version="3.13")
    .env(HF_CACHE_ENV)
    .uv_sync()
    .add_local_python_source("token_holdem")
)

app = modal.App(APP_NAME, image=image, volumes={MODEL_CACHE_DIR: hf_cache})

worker_options = {
    "gpu": DEFAULT_GPU,
    "timeout": MODAL_TIMEOUT_SECONDS,
    "scaledown_window": SCALEDOWN_WINDOW_SECONDS,
    "secrets": [modal.Secret.from_name(HF_SECRET_NAME)],
    "min_containers": MIN_CONTAINERS,
}

heavy_worker_options = {**worker_options, "gpu": HEAVY_GPU}

cache_setup_options = {
    "timeout": max(MODAL_TIMEOUT_SECONDS, 1800),
    "scaledown_window": 60,
    "secrets": [modal.Secret.from_name(HF_SECRET_NAME)],
}

_modal_log(
    "modal_container_start",
    app_name=APP_NAME,
    cache_dir=MODEL_CACHE_DIR,
    demo_mode=DEMO_MODE,
    scaledown_window_seconds=SCALEDOWN_WINDOW_SECONDS,
    default_gpu=DEFAULT_GPU,
    heavy_gpu=HEAVY_GPU,
)


def _commit_model_cache() -> None:
    start = time.perf_counter()
    hf_cache.commit()
    _modal_log("modal_cache_commit", elapsed_seconds=round(time.perf_counter() - start, 3), cache_dir=MODEL_CACHE_DIR)


def _snapshot_cache_exists(model_id: str, filename: str | None = None) -> bool:
    repo_dir = Path(MODEL_CACHE_DIR) / f"models--{model_id.replace('/', '--')}"
    snapshots_dir = repo_dir / "snapshots"
    if not snapshots_dir.exists():
        return False
    snapshots = [path for path in snapshots_dir.iterdir() if path.is_dir()]
    if filename:
        return any((snapshot / filename).exists() for snapshot in snapshots)
    return any(any(snapshot.iterdir()) for snapshot in snapshots)


def _download_model_snapshot(model_id: str) -> dict[str, Any]:
    from huggingface_hub import snapshot_download
    from token_holdem.model_runtime import requires_gguf_runtime

    filename = GGUF_MODEL_FILES.get(model_id) if requires_gguf_runtime(model_id) else None
    if requires_gguf_runtime(model_id) and not filename:
        raise ValueError(f"No GGUF filename configured for {model_id}")

    cache_hit_before = _snapshot_cache_exists(model_id, filename)
    start = time.perf_counter()
    _modal_log(
        "modal_model_snapshot_download_start",
        model_id=model_id,
        cache_dir=MODEL_CACHE_DIR,
        cache_hit_before=cache_hit_before,
        allow_patterns=[filename] if filename else None,
    )
    try:
        snapshot_path = snapshot_download(
            repo_id=model_id,
            cache_dir=MODEL_CACHE_DIR,
            allow_patterns=[filename] if filename else None,
        )
    except Exception as exc:
        _modal_log(
            "modal_model_snapshot_download_error",
            model_id=model_id,
            error_type=exc.__class__.__name__,
            error=str(exc),
            elapsed_seconds=round(time.perf_counter() - start, 3),
        )
        raise
    _commit_model_cache()
    elapsed = time.perf_counter() - start
    _modal_log(
        "modal_model_snapshot_download_complete",
        model_id=model_id,
        cache_state="hit" if cache_hit_before else "downloaded",
        snapshot_path=snapshot_path,
        elapsed_seconds=round(elapsed, 3),
    )
    return {
        "model_id": model_id,
        "cache_hit_before": cache_hit_before,
        "snapshot_path": snapshot_path,
        "elapsed_seconds": elapsed,
    }


def _profiles_for_modal_config(configured: str | None = None) -> list[Any]:
    from token_holdem.agents import ROSTER
    from token_holdem.model_runtime import configured_modal_model_names

    enabled = configured_modal_model_names(configured)
    return [profile for profile in ROSTER if profile.name in enabled]


@lru_cache(maxsize=None)
def _load_model(model_id: str) -> tuple[Any, Any]:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    load_start = time.perf_counter()
    cache_hit_before = _snapshot_cache_exists(model_id)
    _modal_log("modal_model_cache_status", model_id=model_id, cache_hit_before=cache_hit_before, cache_dir=MODEL_CACHE_DIR)
    try:
        tokenizer_start = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            trust_remote_code=True,
            cache_dir=MODEL_CACHE_DIR,
        )
        _modal_log(
            "modal_tokenizer_load_complete",
            model_id=model_id,
            elapsed_seconds=round(time.perf_counter() - tokenizer_start, 3),
        )
        model_start = time.perf_counter()
        model_kwargs: dict[str, Any] = {
            "dtype": "auto",
            "device_map": "auto",
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
            "cache_dir": MODEL_CACHE_DIR,
        }
        if model_id == "openai/gpt-oss-20b":
            model_kwargs["device_map"] = {"": "cuda:0"}
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            **model_kwargs,
        )
        model.eval()
        _modal_log(
            "modal_model_load_to_gpu_complete",
            model_id=model_id,
            elapsed_seconds=round(time.perf_counter() - model_start, 3),
            device=str(getattr(model, "device", "device_map")),
        )
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        _commit_model_cache()
        _modal_log(
            "modal_model_load_complete",
            model_id=model_id,
            cache_state="hit" if cache_hit_before else "downloaded",
            elapsed_seconds=round(time.perf_counter() - load_start, 3),
        )
        return model, tokenizer
    except Exception as exc:
        _modal_log(
            "modal_model_load_error",
            model_id=model_id,
            error_type=exc.__class__.__name__,
            error=str(exc),
            elapsed_seconds=round(time.perf_counter() - load_start, 3),
        )
        raise


@lru_cache(maxsize=None)
def _load_multimodal_model(model_id: str) -> tuple[Any, Any]:
    from transformers import AutoModelForMultimodalLM, AutoProcessor

    load_start = time.perf_counter()
    cache_hit_before = _snapshot_cache_exists(model_id)
    _modal_log("modal_model_cache_status", model_id=model_id, cache_hit_before=cache_hit_before, cache_dir=MODEL_CACHE_DIR)
    try:
        processor_start = time.perf_counter()
        processor = AutoProcessor.from_pretrained(
            model_id,
            trust_remote_code=True,
            cache_dir=MODEL_CACHE_DIR,
        )
        _modal_log(
            "modal_tokenizer_load_complete",
            model_id=model_id,
            elapsed_seconds=round(time.perf_counter() - processor_start, 3),
        )
        model_start = time.perf_counter()
        model = AutoModelForMultimodalLM.from_pretrained(
            model_id,
            dtype="auto",
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            cache_dir=MODEL_CACHE_DIR,
        )
        model.eval()
        _modal_log(
            "modal_model_load_to_gpu_complete",
            model_id=model_id,
            elapsed_seconds=round(time.perf_counter() - model_start, 3),
            device=str(getattr(model, "device", "device_map")),
        )
        _commit_model_cache()
        _modal_log(
            "modal_model_load_complete",
            model_id=model_id,
            cache_state="hit" if cache_hit_before else "downloaded",
            elapsed_seconds=round(time.perf_counter() - load_start, 3),
        )
        return model, processor
    except Exception as exc:
        _modal_log(
            "modal_model_load_error",
            model_id=model_id,
            error_type=exc.__class__.__name__,
            error=str(exc),
            elapsed_seconds=round(time.perf_counter() - load_start, 3),
        )
        raise


@lru_cache(maxsize=None)
def _load_gguf_model(model_id: str) -> Any:
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    load_start = time.perf_counter()
    filename = GGUF_MODEL_FILES.get(model_id)
    if not filename:
        raise ValueError(f"No GGUF filename configured for {model_id}")
    cache_hit_before = _snapshot_cache_exists(model_id, filename)
    _modal_log(
        "modal_model_cache_status",
        model_id=model_id,
        gguf_filename=filename,
        cache_hit_before=cache_hit_before,
        cache_dir=MODEL_CACHE_DIR,
    )
    try:
        download_start = time.perf_counter()
        model_path = hf_hub_download(
            repo_id=model_id,
            filename=filename,
            cache_dir=MODEL_CACHE_DIR,
        )
        _modal_log(
            "modal_model_download_complete",
            model_id=model_id,
            cache_state="hit" if cache_hit_before else "downloaded",
            elapsed_seconds=round(time.perf_counter() - download_start, 3),
            model_path=model_path,
        )
        _commit_model_cache()
        model_start = time.perf_counter()
        model = Llama(
            model_path=model_path,
            n_ctx=int(os.getenv("TOKEN_HOLDEM_GGUF_CONTEXT", "4096")),
            n_gpu_layers=int(os.getenv("TOKEN_HOLDEM_GGUF_GPU_LAYERS", "-1")),
            verbose=False,
        )
        _modal_log(
            "modal_model_load_to_gpu_complete",
            model_id=model_id,
            elapsed_seconds=round(time.perf_counter() - model_start, 3),
        )
        _modal_log(
            "modal_model_load_complete",
            model_id=model_id,
            cache_state="hit" if cache_hit_before else "downloaded",
            elapsed_seconds=round(time.perf_counter() - load_start, 3),
        )
        return model
    except Exception as exc:
        _modal_log(
            "modal_model_load_error",
            model_id=model_id,
            error_type=exc.__class__.__name__,
            error=str(exc),
            elapsed_seconds=round(time.perf_counter() - load_start, 3),
        )
        raise


def _format_chat_prompt(tokenizer: Any, prompt: str) -> str:
    if getattr(tokenizer, "chat_template", None):
        messages = [{"role": "user", "content": prompt}]
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
    return f"{prompt}\n\nAssistant:"


def _format_multimodal_prompt(processor: Any, prompt: str) -> str:
    if getattr(processor, "apply_chat_template", None):
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        try:
            return processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            return processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
    tokenizer = getattr(processor, "tokenizer", None)
    if tokenizer is not None and getattr(tokenizer, "chat_template", None):
        messages = [{"role": "user", "content": prompt}]
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
    return f"{prompt}\n\nAssistant:"


def _move_inputs_to_device(inputs: Any, device: Any) -> Any:
    if hasattr(inputs, "to"):
        return inputs.to(device)
    return {key: value.to(device) if hasattr(value, "to") else value for key, value in inputs.items()}


def _decode_processor_output(processor: Any, output: Any) -> str:
    tokenizer = getattr(processor, "tokenizer", None)
    decoder = tokenizer if tokenizer is not None else processor
    return decoder.decode(output, skip_special_tokens=True)


class _FirstTokenTimer:
    def __init__(self, started_at: float):
        self.started_at = started_at
        self.first_token_seconds: float | None = None
        self._saw_prompt = False

    def put(self, value: Any) -> None:
        if not self._saw_prompt:
            self._saw_prompt = True
            return
        if self.first_token_seconds is None:
            self.first_token_seconds = time.perf_counter() - self.started_at

    def end(self) -> None:
        pass


def _log_generation_complete(runtime_family: str, started_at: float, first_token_seconds: float | None) -> None:
    elapsed = time.perf_counter() - started_at
    _modal_log(
        "modal_generation_complete",
        runtime_family=runtime_family,
        first_token_seconds=round(first_token_seconds if first_token_seconds is not None else elapsed, 3),
        total_generation_seconds=round(elapsed, 3),
    )


def _generate_text(
    model: Any,
    tokenizer: Any,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
    *,
    json_prefix: bool = False,
    deterministic: bool = False,
) -> str:
    import torch

    formatted_prompt = _format_chat_prompt(tokenizer, prompt)
    if json_prefix:
        formatted_prompt += "{"
    inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)
    generation_start = time.perf_counter()
    first_token_timer = _FirstTokenTimer(generation_start)
    generation_kwargs: dict[str, Any] = {
        **inputs,
        "max_new_tokens": max_new_tokens,
        "do_sample": not deterministic,
        "pad_token_id": tokenizer.eos_token_id,
        "streamer": first_token_timer,
    }
    if not deterministic:
        generation_kwargs.update({"temperature": temperature, "top_p": 0.9})
    with torch.inference_mode():
        output = model.generate(**generation_kwargs)
    _log_generation_complete("causal", generation_start, first_token_timer.first_token_seconds)
    decoded = tokenizer.decode(output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
    return "{" + decoded if json_prefix else decoded


def _generate_multimodal_text(
    model: Any,
    processor: Any,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
    *,
    json_prefix: bool = False,
    deterministic: bool = False,
) -> str:
    import torch

    formatted_prompt = _format_multimodal_prompt(processor, prompt)
    if json_prefix:
        formatted_prompt += "{"
    inputs = _move_inputs_to_device(processor(text=formatted_prompt, return_tensors="pt"), model.device)
    tokenizer = getattr(processor, "tokenizer", None)
    eos_token_id = getattr(tokenizer, "eos_token_id", None)
    generation_start = time.perf_counter()
    first_token_timer = _FirstTokenTimer(generation_start)
    generation_kwargs: dict[str, Any] = {
        **inputs,
        "max_new_tokens": max_new_tokens,
        "do_sample": not deterministic,
        "pad_token_id": eos_token_id,
        "streamer": first_token_timer,
    }
    if not deterministic:
        generation_kwargs.update({"temperature": temperature, "top_p": 0.9})
    with torch.inference_mode():
        output = model.generate(**generation_kwargs)
    _log_generation_complete("multimodal", generation_start, first_token_timer.first_token_seconds)
    decoded = _decode_processor_output(processor, output[0][inputs["input_ids"].shape[-1] :])
    return "{" + decoded if json_prefix else decoded


def _generate_gguf_text(
    model: Any,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
    *,
    json_prefix: bool = False,
    deterministic: bool = False,
) -> str:
    generation_start = time.perf_counter()
    first_token_seconds: float | None = None
    chunks: list[str] = []
    formatted_prompt = f"{prompt}\n{{" if json_prefix else prompt
    output = model(
        formatted_prompt,
        max_tokens=max_new_tokens,
        temperature=0.0 if deterministic else temperature,
        top_p=0.9,
        stop=["\n\nUser:", "\n\nVisible state:", "\ntable_talk=", "table_talk=", "\n```"],
        stream=True,
    )
    for chunk in output:
        text = str(chunk["choices"][0].get("text", ""))
        if text and first_token_seconds is None:
            first_token_seconds = time.perf_counter() - generation_start
        chunks.append(text)
    _log_generation_complete("gguf", generation_start, first_token_seconds)
    decoded = "".join(chunks).strip()
    return "{" + decoded if json_prefix else decoded


def _requires_multimodal_processor(model_id: str) -> bool:
    return model_id in MULTIMODAL_PROCESSOR_MODELS


def _generate_loaded_text(
    model: Any,
    tokenizer_or_processor: Any,
    runtime_family: str,
    prompt: str,
    *,
    max_new_tokens: int,
    temperature: float,
    json_prefix: bool = False,
    deterministic: bool = False,
) -> str:
    if runtime_family == "gguf":
        return _generate_gguf_text(
            model,
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            json_prefix=json_prefix,
            deterministic=deterministic,
        )
    if runtime_family == "multimodal":
        return _generate_multimodal_text(
            model,
            tokenizer_or_processor,
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            json_prefix=json_prefix,
            deterministic=deterministic,
        )
    return _generate_text(
        model,
        tokenizer_or_processor,
        prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        json_prefix=json_prefix,
        deterministic=deterministic,
    )


def _build_decision_repair_prompt(original_prompt: str, invalid_output: str, legal_actions: dict[str, Any]) -> str:
    return f"""{original_prompt}

Your previous answer was invalid because it was not a single legal JSON object.
Previous answer:
{invalid_output[:900]}

Return exactly one compact JSON object now.
Allowed actions: {legal_actions['actions']}
Raise presets: {legal_actions['raise_presets']}
Use this schema only:
{{"action":"call","amount":0,"reasoning_hint":"brief reason"}}
No thinking. No markdown. No surrounding text.
"""


def _run_agent_decision_impl(
    game_state: dict[str, Any],
    model_name: str,
    persona: str,
    model_id: str,
    legal_actions: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    try:
        from token_holdem.model_runtime import requires_gguf_runtime

        is_gguf = requires_gguf_runtime(model_id)
        is_multimodal = _requires_multimodal_processor(model_id)
        if is_gguf:
            model = _load_gguf_model(model_id)
            tokenizer_or_processor = None
            runtime_family = "gguf"
        elif is_multimodal:
            model, tokenizer_or_processor = _load_multimodal_model(model_id)
            runtime_family = "multimodal"
        else:
            model, tokenizer_or_processor = _load_model(model_id)
            runtime_family = "causal"
        return _run_loaded_agent_decision_impl(
            game_state,
            model_name,
            persona,
            model_id,
            legal_actions,
            prompt,
            model,
            tokenizer_or_processor,
            runtime_family,
        )
    except Exception as exc:  # noqa: BLE001 - the local adapter converts this into a visible unavailable state.
        return {
            "action": None,
            "bet_amount": None,
            "explanation": "",
            "commentary": "",
            "raw_model_output": "",
            "error": f"{exc.__class__.__name__}: {exc}",
        }


@app.cls(**worker_options)
class CausalModelWorker:
    model_id: str = modal.parameter()
    model: Any = modal.parameter(init=False)
    tokenizer: Any = modal.parameter(init=False)

    @modal.enter()
    def load_model(self) -> None:
        self.model, self.tokenizer = _load_model(self.model_id)

    @modal.method()
    def warmup(self, model_name: str = "") -> dict[str, Any]:
        return {
            "model_name": model_name,
            "model_id": self.model_id,
            "runtime_family": "causal",
            "loaded": self.model is not None and self.tokenizer is not None,
            "cache_dir": MODEL_CACHE_DIR,
        }

    @modal.method()
    def decide(
        self,
        game_state: dict[str, Any],
        model_name: str,
        persona: str,
        legal_actions: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        return _run_loaded_agent_decision_impl(
            game_state,
            model_name,
            persona,
            self.model_id,
            legal_actions,
            prompt,
            self.model,
            self.tokenizer,
            "causal",
        )


@app.cls(**heavy_worker_options)
class HeavyCausalModelWorker:
    model_id: str = modal.parameter()
    model: Any = modal.parameter(init=False)
    tokenizer: Any = modal.parameter(init=False)

    @modal.enter()
    def load_model(self) -> None:
        self.model, self.tokenizer = _load_model(self.model_id)

    @modal.method()
    def warmup(self, model_name: str = "") -> dict[str, Any]:
        return {
            "model_name": model_name,
            "model_id": self.model_id,
            "runtime_family": "heavy_causal",
            "loaded": self.model is not None and self.tokenizer is not None,
            "cache_dir": MODEL_CACHE_DIR,
            "gpu": HEAVY_GPU,
        }

    @modal.method()
    def decide(
        self,
        game_state: dict[str, Any],
        model_name: str,
        persona: str,
        legal_actions: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        return _run_loaded_agent_decision_impl(
            game_state,
            model_name,
            persona,
            self.model_id,
            legal_actions,
            prompt,
            self.model,
            self.tokenizer,
            "causal",
        )


@app.cls(**worker_options)
class MultimodalModelWorker:
    model_id: str = modal.parameter()
    model: Any = modal.parameter(init=False)
    processor: Any = modal.parameter(init=False)

    @modal.enter()
    def load_model(self) -> None:
        self.model, self.processor = _load_multimodal_model(self.model_id)

    @modal.method()
    def warmup(self, model_name: str = "") -> dict[str, Any]:
        return {
            "model_name": model_name,
            "model_id": self.model_id,
            "runtime_family": "multimodal",
            "loaded": self.model is not None and self.processor is not None,
            "cache_dir": MODEL_CACHE_DIR,
        }

    @modal.method()
    def decide(
        self,
        game_state: dict[str, Any],
        model_name: str,
        persona: str,
        legal_actions: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        return _run_loaded_agent_decision_impl(
            game_state,
            model_name,
            persona,
            self.model_id,
            legal_actions,
            prompt,
            self.model,
            self.processor,
            "multimodal",
        )


@app.cls(**worker_options)
class GgufModelWorker:
    model_id: str = modal.parameter()
    model: Any = modal.parameter(init=False)

    @modal.enter()
    def load_model(self) -> None:
        self.model = _load_gguf_model(self.model_id)

    @modal.method()
    def warmup(self, model_name: str = "") -> dict[str, Any]:
        return {
            "model_name": model_name,
            "model_id": self.model_id,
            "runtime_family": "gguf",
            "loaded": self.model is not None,
            "cache_dir": MODEL_CACHE_DIR,
        }

    @modal.method()
    def decide(
        self,
        game_state: dict[str, Any],
        model_name: str,
        persona: str,
        legal_actions: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        return _run_loaded_agent_decision_impl(
            game_state,
            model_name,
            persona,
            self.model_id,
            legal_actions,
            prompt,
            self.model,
            None,
            "gguf",
        )


MODAL_WORKER_CLASSES = {
    "CausalModelWorker": CausalModelWorker,
    "HeavyCausalModelWorker": HeavyCausalModelWorker,
    "MultimodalModelWorker": MultimodalModelWorker,
    "GgufModelWorker": GgufModelWorker,
}


def _run_loaded_agent_decision_impl(
    game_state: dict[str, Any],
    model_name: str,
    persona: str,
    model_id: str,
    legal_actions: dict[str, Any],
    prompt: str,
    model: Any,
    tokenizer_or_processor: Any,
    runtime_family: str,
) -> dict[str, Any]:
    from token_holdem.agents import fallback_decide
    from token_holdem.agents import profile_by_name
    from token_holdem.model_runtime import (
        apply_poker_sanity_guard,
        first_valid_decision,
        template_table_talk,
    )

    try:
        try:
            profile = profile_by_name(model_name)
        except StopIteration:
            from token_holdem.agents import AgentProfile

            profile = AgentProfile(model_name, model_id, persona, 0.5, 0.1, ("The candlelight keeps me thinking.",))
        decision_tokens = GGUF_DECISION_MAX_TOKENS if runtime_family == "gguf" else 192
        decision_text = _generate_loaded_text(
            model,
            tokenizer_or_processor,
            runtime_family,
            prompt,
            max_new_tokens=decision_tokens,
            temperature=0.0,
            json_prefix=True,
            deterministic=True,
        )
        decision = first_valid_decision(decision_text, legal_actions)
        repair_text = ""
        if decision is None:
            repair_text = _generate_loaded_text(
                model,
                tokenizer_or_processor,
                runtime_family,
                _build_decision_repair_prompt(prompt, decision_text, legal_actions),
                max_new_tokens=GGUF_DECISION_MAX_TOKENS if runtime_family == "gguf" else 96,
                temperature=0.0,
                json_prefix=True,
                deterministic=True,
            )
            decision = first_valid_decision(repair_text, legal_actions)
        if decision is None:
            decision = apply_poker_sanity_guard(fallback_decide(profile, game_state, seed=game_state.get("seed")), game_state)
            commentary = template_table_talk(profile, decision["action"], game_state)
            return {
                "action": decision["action"],
                "bet_amount": int(decision.get("amount") or 0),
                "explanation": "model decision JSON invalid after repair attempt; used persona fallback action",
                "commentary": commentary,
                "raw_model_output": f"decision={decision_text[:800]}\nrepair={repair_text[:500]}",
                "error": None,
            }
        decision = apply_poker_sanity_guard(decision, game_state)
        commentary = template_table_talk(profile, decision["action"], game_state)
        raw_model_output = f"decision={decision_text[:800]}"
        if repair_text:
            raw_model_output += f"\nrepair={repair_text[:500]}"
        return {
            "action": decision["action"],
            "bet_amount": int(decision.get("amount") or 0),
            "explanation": decision.get("reasoning_hint", ""),
            "commentary": commentary,
            "raw_model_output": raw_model_output,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - the local adapter converts this into a visible unavailable state.
        return {
            "action": None,
            "bet_amount": None,
            "explanation": "",
            "commentary": "",
            "raw_model_output": "",
            "error": f"{exc.__class__.__name__}: {exc}",
        }


@app.function(**cache_setup_options)
def predownload_model_snapshot(model_name: str, model_id: str) -> dict[str, Any]:
    return {"model_name": model_name, **_download_model_snapshot(model_id)}


def _collect_spawned_calls(spawned_calls: list[tuple[str, float, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, len(spawned_calls))) as executor:
        futures = {
            executor.submit(call.get, timeout=max(MODAL_TIMEOUT_SECONDS, 1800)): (model_name, start)
            for model_name, start, call in spawned_calls
        }
        for future in as_completed(futures):
            model_name, start = futures[future]
            result = future.result()
            result["elapsed_seconds"] = round(time.perf_counter() - start, 3)
            results.append(result)
            _modal_log("modal_parallel_call_complete", **{"model_name": model_name, **result})
    return sorted(results, key=lambda result: result.get("model_name", ""))


@app.function(**worker_options)
def run_agent_decision(
    game_state: dict[str, Any],
    model_name: str,
    persona: str,
    model_id: str,
    legal_actions: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    return _run_agent_decision_impl(
        game_state,
        model_name,
        persona,
        model_id,
        legal_actions,
        prompt,
    )


@app.local_entrypoint()
def setup_cache(model_names: str = "default") -> None:
    configured = None if model_names == "default" else model_names
    spawned_calls = []
    for profile in _profiles_for_modal_config(configured):
        _modal_log("modal_cache_setup_spawn", model_name=profile.name, model_id=profile.model_id)
        spawned_calls.append((profile.name, time.perf_counter(), predownload_model_snapshot.spawn(profile.name, profile.model_id)))
    results = _collect_spawned_calls(spawned_calls)
    print(json.dumps(results, indent=2, default=str))


@app.local_entrypoint()
def warmup_demo(model_names: str = "default") -> None:
    from token_holdem.model_runtime import modal_worker_class_name

    configured = None if model_names == "default" else model_names
    results = []
    spawned_calls = []
    for profile in _profiles_for_modal_config(configured):
        Worker = MODAL_WORKER_CLASSES[modal_worker_class_name(profile.model_id)]
        _modal_log("modal_demo_warmup_start", model_name=profile.name, model_id=profile.model_id)
        spawned_calls.append((profile.name, time.perf_counter(), Worker(model_id=profile.model_id).warmup.spawn(profile.name)))
    results = _collect_spawned_calls(spawned_calls)
    for result in results:
        _modal_log("modal_demo_warmup_complete", **result)
    print(json.dumps(results, indent=2, default=str))


@app.local_entrypoint()
def smoke(model_name: str = "Gemma") -> None:
    from token_holdem.agents import profile_by_name
    from token_holdem.model_runtime import build_prompt

    profile = profile_by_name(model_name)
    state = {
        "hand_no": 1,
        "street": "preflop",
        "hole_cards": ["As", "Kd"],
        "community_cards": [],
        "stack": 1000,
        "pot": 30,
        "legal": {
            "actions": ["fold", "call", "raise", "all_in"],
            "to_call": 20,
            "raise_presets": {"min": 40, "half_pot": 80, "pot": 140, "all_in": 1000},
        },
        "history": [],
        "recent_chats": [],
        "seed": 123,
        "session_id": "modal-smoke",
        "hand_id": "modal-smoke-h001",
        "orbit_id": "modal-smoke-o01",
    }
    from token_holdem.model_runtime import modal_worker_class_name

    Worker = MODAL_WORKER_CLASSES[modal_worker_class_name(profile.model_id)]
    result = Worker(model_id=profile.model_id).decide.remote(
        state,
        profile.name,
        profile.persona,
        state["legal"],
        build_prompt(profile, state),
    )
    print(result)
