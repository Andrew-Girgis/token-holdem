from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import modal


APP_NAME = os.getenv("TOKEN_HOLDEM_MODAL_APP_NAME", "token-holdem-inference")
DEFAULT_GPU = os.getenv("TOKEN_HOLDEM_MODAL_GPU", "L40S") or None
HF_SECRET_NAME = os.getenv("TOKEN_HOLDEM_MODAL_HF_SECRET_NAME", "token-holdem-hf-token")
MODEL_CACHE_DIR = "/cache/huggingface"
hf_cache = modal.Volume.from_name("token-holdem-hf-cache", create_if_missing=True)

GGUF_MODEL_FILES = {
    "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF": "NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf",
    "lm-kit/qwen-3-0.6b-instruct-gguf": "Qwen3-0.6B-Q4_K_M.gguf",
    "TheBloke/Mistral-7B-Instruct-v0.2-GGUF": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
}
MULTIMODAL_PROCESSOR_MODELS = {"google/gemma-4-12B-it"}

image = (
    modal.Image.debian_slim(python_version="3.13")
    .uv_sync()
    .add_local_python_source("token_holdem")
)

app = modal.App(APP_NAME, image=image, volumes={MODEL_CACHE_DIR: hf_cache})


@lru_cache(maxsize=2)
def _load_model(model_id: str) -> tuple[Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        trust_remote_code=True,
        cache_dir=MODEL_CACHE_DIR,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype="auto",
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        cache_dir=MODEL_CACHE_DIR,
    )
    model.eval()
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer


@lru_cache(maxsize=1)
def _load_multimodal_model(model_id: str) -> tuple[Any, Any]:
    from transformers import AutoModelForMultimodalLM, AutoProcessor

    processor = AutoProcessor.from_pretrained(
        model_id,
        trust_remote_code=True,
        cache_dir=MODEL_CACHE_DIR,
    )
    model = AutoModelForMultimodalLM.from_pretrained(
        model_id,
        dtype="auto",
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        cache_dir=MODEL_CACHE_DIR,
    )
    model.eval()
    return model, processor


@lru_cache(maxsize=3)
def _load_gguf_model(model_id: str) -> Any:
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    filename = GGUF_MODEL_FILES.get(model_id)
    if not filename:
        raise ValueError(f"No GGUF filename configured for {model_id}")
    model_path = hf_hub_download(
        repo_id=model_id,
        filename=filename,
        cache_dir=MODEL_CACHE_DIR,
    )
    return Llama(
        model_path=model_path,
        n_ctx=int(os.getenv("TOKEN_HOLDEM_GGUF_CONTEXT", "4096")),
        n_gpu_layers=int(os.getenv("TOKEN_HOLDEM_GGUF_GPU_LAYERS", "-1")),
        verbose=False,
    )


def _format_chat_prompt(tokenizer: Any, prompt: str) -> str:
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
    return f"{prompt}\n\nAssistant:"


def _format_multimodal_prompt(processor: Any, prompt: str) -> str:
    if getattr(processor, "apply_chat_template", None):
        return processor.apply_chat_template(
            [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            tokenize=False,
            add_generation_prompt=True,
        )
    tokenizer = getattr(processor, "tokenizer", None)
    if tokenizer is not None and getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
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


def _generate_text(model: Any, tokenizer: Any, prompt: str, max_new_tokens: int, temperature: float) -> str:
    import torch

    formatted_prompt = _format_chat_prompt(tokenizer, prompt)
    inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)


def _generate_multimodal_text(model: Any, processor: Any, prompt: str, max_new_tokens: int, temperature: float) -> str:
    import torch

    formatted_prompt = _format_multimodal_prompt(processor, prompt)
    inputs = _move_inputs_to_device(processor(text=formatted_prompt, return_tensors="pt"), model.device)
    tokenizer = getattr(processor, "tokenizer", None)
    eos_token_id = getattr(tokenizer, "eos_token_id", None)
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=0.9,
            pad_token_id=eos_token_id,
        )
    return _decode_processor_output(processor, output[0][inputs["input_ids"].shape[-1] :])


def _generate_gguf_text(model: Any, prompt: str, max_new_tokens: int, temperature: float) -> str:
    output = model(
        prompt,
        max_tokens=max_new_tokens,
        temperature=temperature,
        top_p=0.9,
        stop=["\n\nUser:", "\n\nVisible state:"],
    )
    return str(output["choices"][0].get("text", "")).strip()


def _requires_multimodal_processor(model_id: str) -> bool:
    return model_id in MULTIMODAL_PROCESSOR_MODELS


def _run_agent_decision_impl(
    game_state: dict[str, Any],
    model_name: str,
    persona: str,
    model_id: str,
    legal_actions: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    from token_holdem.agents import AgentProfile
    from token_holdem.model_runtime import (
        apply_poker_sanity_guard,
        build_table_talk_prompt,
        finalize_table_talk,
        first_valid_decision,
    )

    try:
        from token_holdem.model_runtime import requires_gguf_runtime

        is_gguf = requires_gguf_runtime(model_id)
        is_multimodal = _requires_multimodal_processor(model_id)
        if is_gguf:
            model = _load_gguf_model(model_id)
            decision_text = _generate_gguf_text(model, prompt, max_new_tokens=192, temperature=0.7)
        elif is_multimodal:
            model, processor = _load_multimodal_model(model_id)
            decision_text = _generate_multimodal_text(model, processor, prompt, max_new_tokens=192, temperature=0.7)
        else:
            model, tokenizer = _load_model(model_id)
            decision_text = _generate_text(model, tokenizer, prompt, max_new_tokens=192, temperature=0.7)
        decision = first_valid_decision(decision_text, legal_actions)
        if decision is None:
            return {
                "action": None,
                "bet_amount": None,
                "explanation": "",
                "commentary": "",
                "raw_model_output": decision_text,
                "error": "model did not return valid decision JSON",
            }
        decision = apply_poker_sanity_guard(decision, game_state)
        profile = AgentProfile(model_name, model_id, persona, 0.5, 0.1, ())
        talk_prompt = build_table_talk_prompt(profile, decision["action"], game_state)
        if is_gguf:
            talk_text = _generate_gguf_text(model, talk_prompt, max_new_tokens=48, temperature=0.9)
        elif is_multimodal:
            talk_text = _generate_multimodal_text(model, processor, talk_prompt, max_new_tokens=48, temperature=0.9)
        else:
            talk_text = _generate_text(model, tokenizer, talk_prompt, max_new_tokens=48, temperature=0.9)
        commentary = finalize_table_talk(profile, decision["action"], talk_text, game_state)
        return {
            "action": decision["action"],
            "bet_amount": int(decision.get("amount") or 0),
            "explanation": decision.get("reasoning_hint", ""),
            "commentary": commentary,
            "raw_model_output": f"decision={decision_text[:800]}\ntable_talk={talk_text[:400]}",
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


@app.function(gpu=DEFAULT_GPU, timeout=900, scaledown_window=300, secrets=[modal.Secret.from_name(HF_SECRET_NAME)])
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
    result = run_agent_decision.remote(
        state,
        profile.name,
        profile.persona,
        profile.model_id,
        state["legal"],
        build_prompt(profile, state),
    )
    print(result)
